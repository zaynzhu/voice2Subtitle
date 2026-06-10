from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import Job, JobLog, MediaItem, SubtitleSegment
from app.services.audio_extractor import extract_audio
from app.services.media_probe import probe_media
from app.services.subtitle_writer import write_srt
from app.workers.processor import JobCancelled

logger = logging.getLogger(__name__)

PROGRESS_UPDATE_INTERVAL_SEC = 2.0


@dataclass(frozen=True)
class PipelineResult:
    job_id: int
    media_item_id: int
    stage: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_job_log(session: Session, job: Job, level: str, message: str) -> None:
    session.add(JobLog(job_id=job.id, level=level, message=message))


def _check_cancel(cancel_event: threading.Event, stage_name: str) -> None:
    """检查取消信号，如果已设置则抛出 JobCancelled 异常。"""
    if cancel_event.is_set():
        raise JobCancelled(f"任务在 {stage_name} 阶段被用户取消")




def _commit_and_refresh(session: Session, media_item: MediaItem, job: Job) -> None:
    """提交当前事务并刷新对象，确保短事务释放数据库锁。"""
    session.commit()
    session.refresh(media_item)
    session.refresh(job)


def _make_progress_reporter(
    session: Session,
    job: Job,
    stage_start: float,
    stage_end: float,
) -> Callable[[float], None]:
    """创建阶段进度回调，按固定间隔把局部进度映射到总进度。"""
    last_progress = max(job.progress or 0.0, stage_start)
    last_commit_at = time.monotonic() - PROGRESS_UPDATE_INTERVAL_SEC
    disabled = False

    def report(local_progress: float) -> None:
        nonlocal last_progress, last_commit_at, disabled
        if disabled:
            return

        ratio = min(1.0, max(0.0, local_progress))
        next_progress = stage_start + (stage_end - stage_start) * ratio
        next_progress = max(last_progress, min(stage_end, next_progress))
        now = time.monotonic()

        if next_progress <= last_progress:
            return
        if next_progress < stage_end and now - last_commit_at < PROGRESS_UPDATE_INTERVAL_SEC:
            return

        job.progress = next_progress
        try:
            session.commit()
            session.refresh(job)
        except Exception:
            session.rollback()
            disabled = True
            logger.exception("更新任务进度失败，后续进度回调将被忽略")
            return

        last_progress = next_progress
        last_commit_at = now

    return report


def run_processing_pipeline(
    session: Session,
    media_item: MediaItem,
    cancel_event: threading.Event | None = None,
) -> PipelineResult:
    if cancel_event is None:
        cancel_event = threading.Event()

    job = Job(
        media_item_id=media_item.id,
        type="process_media",
        status="running",
        stage="probing",
        progress=0.0,
        started_at=utc_now(),
    )
    session.add(job)

    try:
        session.commit()
        session.refresh(media_item)
        # 1. 探测媒体元数据
        _check_cancel(cancel_event, "探测")
        logger.info("[%s] [1/5] 探测媒体元数据...", media_item.file_name)
        add_job_log(session, job, "info", f"Probing media: {media_item.file_name}")
        probe = probe_media(media_item.file_path)
        media_item.duration_ms = probe.duration_ms
        media_item.status = "probing"
        job.progress = 0.10
        _commit_and_refresh(session, media_item, job)
        logger.info("[%s] [1/5] 探测完成，时长 %s ms", media_item.file_name, probe.duration_ms)

        # 2. 提取音频
        _check_cancel(cancel_event, "音频提取")
        logger.info("[%s] [2/5] 提取音频...", media_item.file_name)
        audio_path = Path(settings.cache_dir) / f"{media_item.id}.mp3"
        add_job_log(session, job, "info", "Extracting audio")
        job.stage = "extracting_audio"
        media_item.status = "extracting_audio"
        _commit_and_refresh(session, media_item, job)
        extract_audio(media_item.file_path, audio_path)
        job.stage = "ready_for_transcription"
        job.progress = 0.25
        _commit_and_refresh(session, media_item, job)
        logger.info("[%s] [2/5] 音频提取完成", media_item.file_name)

        # 3. 语音转录
        _check_cancel(cancel_event, "语音转录")
        logger.info("[%s] [3/5] 语音转录中...", media_item.file_name)
        add_job_log(session, job, "info", "Starting speech transcription")
        job.stage = "transcribing"
        media_item.status = "transcribing"
        _commit_and_refresh(session, media_item, job)

        from app.services.transcriber import create_transcriber_from_settings
        transcriber = create_transcriber_from_settings(settings)
        segments = transcriber.transcribe(
            audio_path,
            on_progress=_make_progress_reporter(session, job, 0.25, 0.60),
            total_duration_ms=media_item.duration_ms,
        )

        # 转录完成后再次检查取消（转录本身不可中断，但后续步骤可以跳过）
        _check_cancel(cancel_event, "转录完成")

        add_job_log(session, job, "info", f"Transcription complete. Got {len(segments)} segments. Saving segments...")
        logger.info("[%s] [3/5] 转录完成，共 %d 个片段", media_item.file_name, len(segments))

        # 在删除旧字幕前再次检查取消，避免销毁已翻译数据
        _check_cancel(cancel_event, "保存字幕")

        session.execute(delete(SubtitleSegment).where(SubtitleSegment.media_item_id == media_item.id))

        db_segments = []
        for seg in segments:
            db_seg = SubtitleSegment(
                media_item_id=media_item.id,
                index_no=seg.index_no,
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                source_text=seg.text,
                confidence=seg.confidence,
            )
            session.add(db_seg)
            db_segments.append(db_seg)

        job.progress = 0.60
        job.stage = "ready_for_translation"
        media_item.status = "transcribed"
        _commit_and_refresh(session, media_item, job)

        # 4. 字幕翻译
        _check_cancel(cancel_event, "翻译")
        logger.info("[%s] [4/5] 字幕翻译中...", media_item.file_name)
        add_job_log(session, job, "info", f"Starting translation from {media_item.source_language} to {media_item.target_language}")
        job.stage = "translating"
        media_item.status = "translating"
        _commit_and_refresh(session, media_item, job)

        from app.services.translator import create_translator_from_settings, TranslationRequest
        translator = create_translator_from_settings(settings)

        translation_requests = [
            TranslationRequest(index_no=seg.index_no, text=seg.source_text)
            for seg in db_segments
        ]

        translation_results = translator.translate_segments(
            source_lang=media_item.source_language,
            target_lang=media_item.target_language,
            segments=translation_requests,
            on_progress=_make_progress_reporter(session, job, 0.60, 0.90),
        )

        failed_count = 0
        for res in translation_results:
            seg = db_segments[res.index_no - 1]
            if res.success:
                seg.translated_text = res.translated_text
            else:
                seg.translated_text = ""
                failed_count += 1
                add_job_log(session, job, "warning", f"Segment {res.index_no} translation failed: {res.error}")

        if failed_count > 0:
            add_job_log(session, job, "warning", f"Translation complete with {failed_count} segments failed")
            logger.warning("[%s] [4/5] 翻译完成，%d 个片段失败", media_item.file_name, failed_count)
        else:
            add_job_log(session, job, "info", "Translation complete successfully")
            logger.info("[%s] [4/5] 翻译完成", media_item.file_name)

        job.progress = 0.90
        job.stage = "ready_for_export"
        media_item.status = "translated"
        _commit_and_refresh(session, media_item, job)

        # 5. 导出字幕为 SRT
        _check_cancel(cancel_event, "导出")
        logger.info("[%s] [5/5] 导出 SRT 字幕...", media_item.file_name)
        add_job_log(session, job, "info", "Exporting subtitles to SRT file")
        job.stage = "exporting_subtitles"
        _commit_and_refresh(session, media_item, job)

        output_srt_path = export_media_subtitles(session, media_item)
        media_item.subtitle_path = str(output_srt_path)

        # 6. Pipeline 完成
        job.status = "succeeded"
        job.stage = "completed"
        job.progress = 1.0
        job.finished_at = utc_now()
        media_item.status = "ready_for_review"
        add_job_log(session, job, "info", f"Job pipeline completed successfully. Subtitles saved to: {output_srt_path}")
        logger.info("[%s] [完成] 全部完成！字幕已保存: %s", media_item.file_name, output_srt_path)

        session.commit()
        return PipelineResult(job_id=job.id, media_item_id=media_item.id, stage="completed")

    except JobCancelled:
        job.status = "cancelled"
        job.stage = "cancelled"
        job.error_message = "任务被用户主动取消"
        job.finished_at = utc_now()
        media_item.status = "failed"
        add_job_log(session, job, "warning", "Job cancelled by user")
        try:
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("提交取消状态失败")
        raise

    except Exception as exc:
        job.status = "failed"
        job.stage = "failed"
        job.error_code = exc.__class__.__name__
        job.error_message = str(exc)
        job.finished_at = utc_now()
        media_item.status = "failed"
        add_job_log(session, job, "error", str(exc))
        try:
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("提交失败状态时发生二次异常")
        raise


def export_media_subtitles(session: Session, media_item: MediaItem) -> Path:
    segments = list(
        session.scalars(
            select(SubtitleSegment)
            .where(SubtitleSegment.media_item_id == media_item.id)
            .order_by(SubtitleSegment.index_no)
        )
    )
    output_path = (
        Path(media_item.subtitle_path)
        if media_item.subtitle_path
        else Path(media_item.file_path).with_suffix(".srt")
    )
    return write_srt(segments, output_path)
