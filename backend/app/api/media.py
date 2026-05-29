from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import MediaItem, Project
from app.models.schemas import MediaItemRead

router = APIRouter(prefix="/api", tags=["media"])

MIME_MAP = {
    ".mp4": "video/mp4",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".webm": "video/webm",
    ".ts": "video/mp2t",
    ".mpg": "video/mpeg",
    ".mpeg": "video/mpeg",
    ".m4v": "video/x-m4v",
    ".3gp": "video/3gpp",
    ".rmvb": "application/vnd.rn-realmedia-vbr",
    ".rm": "application/vnd.rn-realmedia",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".wma": "audio/x-ms-wma",
}

# 从 MIME_MAP 派生，避免两套集合漂移
STREAMABLE_EXTENSIONS = set(MIME_MAP.keys())


@router.get("/projects/{project_id}/media", response_model=list[MediaItemRead])
def list_project_media(project_id: int, session: Session = Depends(get_session)) -> list[MediaItem]:
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return list(
        session.scalars(
            select(MediaItem)
            .where(MediaItem.project_id == project_id)
            .order_by(MediaItem.file_name)
        )
    )


@router.get("/media/{media_id}", response_model=MediaItemRead)
def get_media_item(media_id: int, session: Session = Depends(get_session)) -> MediaItem:
    item = session.get(MediaItem, media_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Media item not found")
    return item


@router.post("/media/unload-gpu")
def unload_gpu_memory() -> dict:
    """强制进行垃圾回收并清理 PyTorch CUDA 显存缓存，退回所有驻留的 GPU 显存。"""
    import gc
    import logging

    logger = logging.getLogger(__name__)
    logger.info("收到用户主动发起的 GPU 显存资源释放请求...")

    # 1. 强制进行垃圾回收，彻底销毁可能悬挂的模型变量对象
    gc.collect()

    # 2. 强行交还 CUDA 分配缓存给显卡驱动
    cuda_cleaned = False
    try:
        import torch  # type: ignore[import-untyped]
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            cuda_cleaned = True
            logger.info("已成功清空 PyTorch CUDA 显存分配池 (torch.cuda.empty_cache)")
    except ImportError:
        pass

    return {
        "success": True,
        "message": (
            "GPU memory cache has been successfully emptied"
            if cuda_cleaned
            else "GC executed. No active CUDA device found."
        ),
    }


@router.get("/media/{media_id}/stream")
def stream_media(media_id: int, session: Session = Depends(get_session)):
    """流式传输媒体文件，支持 HTTP Range 请求以便视频拖动进度条。"""
    item = session.get(MediaItem, media_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Media item not found")

    file_path = Path(item.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    suffix = file_path.suffix.lower()
    if suffix not in STREAMABLE_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported media format: {suffix}")

    mime_type = MIME_MAP.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=file_path.name,
    )
