from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import Job, MediaItem
from app.services.job_pipeline import add_job_log, run_processing_pipeline
from app.workers.processor import processor as _get_processor
from app.workers.queue import job_queue

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
    job_queue.enqueue(media_id)

    return {
        "media_item_id": media_id,
        "status": "queued",
        "message": "Media processing has been enqueued"
    }


@router.post("/jobs/cancel")
def cancel_jobs(session: Session = Depends(get_session)) -> dict:
    """取消当前正在执行的任务并清空等待队列，同时释放 GPU 显存。"""
    from app.workers.processor import processor as proc

    # 1. 通知 processor 取消当前任务
    cancel_result = {"cleared_queue": 0}
    if proc is not None:
        cancel_result = proc.cancel_current()

    # 2. 将数据库中所有 running/queued 的 Job 标记为 cancelled
    active_jobs = list(
        session.scalars(
            select(Job).where(Job.status.in_(["running", "queued"]))
        )
    )
    cancelled_count = 0
    for job in active_jobs:
        job.status = "cancelled"
        job.stage = "cancelled"
        job.error_message = "任务被用户主动取消"
        cancelled_count += 1

        # 将对应的 MediaItem 标记为 failed
        media_item = session.get(MediaItem, job.media_item_id)
        if media_item is not None and media_item.status in ("running", "queued", "probing", "extracting_audio", "transcribing", "translating"):
            media_item.status = "failed"

    session.commit()

    # 3. 尝试释放 GPU 显存
    gpu_message = "GPU 显存未释放（无可用 GPU 或未安装 torch）"
    try:
        import gc
        gc.collect()
        try:
            import torch  # type: ignore[import-untyped]
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                gpu_message = "GPU 显存已释放"
        except ImportError:
            pass
    except Exception:
        pass

    return {
        "cancelled_jobs": cancelled_count,
        "cleared_queue": cancel_result["cleared_queue"],
        "gpu_released": gpu_message,
    }