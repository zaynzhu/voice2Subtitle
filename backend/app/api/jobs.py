from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import Job, MediaItem
from app.services.job_pipeline import add_job_log, run_processing_pipeline

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/media/{media_id}/jobs")
def list_media_jobs(media_id: int, session: Session = Depends(get_session)) -> list[dict]:
    media_item = session.get(MediaItem, media_id)
    if media_item is None:
        raise HTTPException(status_code=404, detail="Media item not found")

    jobs = list(
        session.scalars(
            select(Job)
            .where(Job.media_item_id == media_id)
            .order_by(Job.created_at.desc())
        )
    )
    return [
        {
            "id": job.id,
            "type": job.type,
            "status": job.status,
            "stage": job.stage,
            "progress": job.progress,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "created_at": job.created_at,
        }
        for job in jobs
    ]


@router.post("/media/{media_id}/process")
def process_media(media_id: int, session: Session = Depends(get_session)) -> dict:
    media_item = session.get(MediaItem, media_id)
    if media_item is None:
        raise HTTPException(status_code=404, detail="Media item not found")

    # 更新媒体状态为已排队
    media_item.status = "queued"
    session.commit()

    # 异步入队任务
    from app.workers.queue import job_queue
    job_queue.enqueue(media_id)

    return {
        "media_item_id": media_id,
        "status": "queued",
        "message": "Media processing has been enqueued"
    }
