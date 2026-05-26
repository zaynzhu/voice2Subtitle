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
        add_job_log(session, job, "info", f"Probing media: {media_item.file_name}")
        probe = probe_media(media_item.file_path)
        media_item.duration_ms = probe.duration_ms
        media_item.status = "probing"
        session.flush()

        audio_path = Path(settings.cache_dir) / f"{media_item.id}.mp3"
        add_job_log(session, job, "info", "Extracting audio")
        extract_audio(media_item.file_path, audio_path)
        job.stage = "ready_for_transcription"
        job.progress = 0.25
        media_item.status = "extracting_audio"
        session.flush()

        raise NotImplementedError("Transcription pipeline is not connected yet")
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
