from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import MediaItem
from app.services.job_pipeline import export_media_subtitles

router = APIRouter(prefix="/api", tags=["exports"])


@router.post("/media/{media_id}/export")
def export_media(media_id: int, session: Session = Depends(get_session)) -> dict:
    media_item = session.get(MediaItem, media_id)
    if media_item is None:
        raise HTTPException(status_code=404, detail="Media item not found")

    output_path = export_media_subtitles(session, media_item)
    media_item.subtitle_path = str(output_path)
    media_item.status = "exported"
    session.commit()
    return {"media_id": media_id, "subtitle_path": str(output_path)}
