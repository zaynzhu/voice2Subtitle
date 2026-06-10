from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import MediaItem, SubtitleSegment
from app.services.job_pipeline import export_media_subtitles

router = APIRouter(prefix="/api", tags=["exports"])


@router.post("/media/{media_id}/export")
def export_media(media_id: int, session: Session = Depends(get_session)) -> dict:
    media_item = session.get(MediaItem, media_id)
    if media_item is None:
        raise HTTPException(status_code=404, detail="Media item not found")

    has_subtitle = session.scalar(
        select(SubtitleSegment.id)
        .where(SubtitleSegment.media_item_id == media_id)
        .limit(1)
    )
    if has_subtitle is None:
        raise HTTPException(status_code=400, detail="没有可导出的字幕，请先完成转录或导入字幕")

    output_path = export_media_subtitles(session, media_item)
    media_item.subtitle_path = str(output_path)
    media_item.status = "exported"
    session.commit()
    return {"media_id": media_id, "subtitle_path": str(output_path)}
