from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import Job, JobLog, MediaItem, SubtitleSegment
from app.services.audio_extractor import extract_audio
from app.services.media_probe import probe_media
from app.services.subtitle_writer import write_srt


@dataclass(frozen=True)
class PipelineResult:
    job_id: int
    media_item_id: int
    stage: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def add_job_log(session: Session, job: Job, level: str, message: str) -> None:
    session.add(JobLog(job_id=job.id, level=level, message=message))


def run_processing_pipeline(session: Session, media_item: MediaItem) -> PipelineResult:
    job = Job(
        media_item_id=media_item.id,
        type="process_media",
        status="running",
        stage="probing",
        progress=0.0,
        started_at=utc_now(),
    )
    session.add(job)
    session.flush()

    try:
        print("[DEBUG] 步骤 1: 正在执行 ffprobe 探测媒体...", flush=True)
        add_job_log(session, job, "info", f"Probing media: {media_item.file_name}")
        probe = probe_media(media_item.file_path)
        media_item.duration_ms = probe.duration_ms
        media_item.status = "probing"
        session.flush()

        print("[DEBUG] 步骤 2: 正在执行 ffmpeg 提取音频...", flush=True)
        audio_path = Path(settings.cache_dir) / f"{media_item.id}.mp3"
        add_job_log(session, job, "info", "Extracting audio")
        extract_audio(media_item.file_path, audio_path)
        job.stage = "ready_for_transcription"
        job.progress = 0.25
        media_item.status = "extracting_audio"
        session.flush()

        # 3. 语音转录
        print("[DEBUG] 步骤 3: 正在装载 Whisper 模型并开始语音转录...", flush=True)
        add_job_log(session, job, "info", "Starting speech transcription")
        job.stage = "transcribing"
        media_item.status = "transcribing"
        session.flush()

        from app.services.transcriber import create_transcriber_from_settings
        transcriber = create_transcriber_from_settings(settings)
        segments = transcriber.transcribe(audio_path)

        print(f"[DEBUG] 步骤 3 完成，共获得 {len(segments)} 条字幕段，正在保存转录结果...", flush=True)
        add_job_log(session, job, "info", f"Transcription complete. Got {len(segments)} segments. Saving segments...")
        
        # 清理可能已存在的旧字幕段，避免残留
        from sqlalchemy import delete
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
        session.flush()

        # 4. 字幕翻译
        print(f"[DEBUG] 步骤 4: 正在启动字幕翻译，源语言: {media_item.source_language} -> 目标语言: {media_item.target_language}...", flush=True)
        add_job_log(session, job, "info", f"Starting translation from {media_item.source_language} to {media_item.target_language}")
        job.stage = "translating"
        media_item.status = "translating"
        session.flush()

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
            print(f"[DEBUG] 步骤 4 完成，翻译结束，但有 {failed_count} 句翻译失败", flush=True)
            add_job_log(session, job, "warning", f"Translation complete with {failed_count} segments failed")
        else:
            print("[DEBUG] 步骤 4 完成，全部字幕段翻译成功！", flush=True)
            add_job_log(session, job, "info", "Translation complete successfully")

        job.progress = 0.90
        job.stage = "ready_for_export"
        media_item.status = "translated"
        session.flush()

        # 5. 导出字幕为 SRT
        print("[DEBUG] 步骤 5: 正在导出字幕为 srt 物理文件...", flush=True)
        add_job_log(session, job, "info", "Exporting subtitles to SRT file")
        job.stage = "exporting_subtitles"
        session.flush()

        output_srt_path = export_media_subtitles(session, media_item)
        media_item.subtitle_path = str(output_srt_path)

        # 6. Pipeline 完成
        job.status = "succeeded"
        job.stage = "completed"
        job.progress = 1.0
        job.finished_at = utc_now()
        media_item.status = "ready_for_review"
        add_job_log(session, job, "info", f"Job pipeline completed successfully. Subtitles saved to: {output_srt_path}")
        
        session.commit()
        return PipelineResult(job_id=job.id, media_item_id=media_item.id, stage="completed")

    except Exception as exc:
        job.status = "failed"
        job.stage = "failed"
        job.error_code = exc.__class__.__name__
        job.error_message = str(exc)
        job.finished_at = utc_now()
        media_item.status = "failed"
        add_job_log(session, job, "error", str(exc))
        session.commit()
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
