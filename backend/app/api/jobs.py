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

    try:
        result = run_processing_pipeline(session, media_item)
        session.commit()
        return {"job_id": result.job_id, "media_item_id": result.media_item_id, "stage": result.stage}
    except NotImplementedError as exc:
        session.rollback()
        raise HTTPException(status_code=501, detail=str(exc)) from exc
