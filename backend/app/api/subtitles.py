from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import MediaItem, SubtitleSegment
from app.models.schemas import SubtitleSegmentRead

router = APIRouter(prefix="/api", tags=["subtitles"])


@router.get("/media/{media_id}/subtitles", response_model=list[SubtitleSegmentRead])
def list_subtitles(media_id: int, session: Session = Depends(get_session)) -> list[SubtitleSegment]:
    if session.get(MediaItem, media_id) is None:
        raise HTTPException(status_code=404, detail="Media item not found")

    return list(
        session.scalars(
            select(SubtitleSegment)
            .where(SubtitleSegment.media_item_id == media_id)
            .order_by(SubtitleSegment.index_no)
        )
    )
