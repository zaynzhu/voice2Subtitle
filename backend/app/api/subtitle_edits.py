from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import SubtitleSegment

router = APIRouter(prefix="/api", tags=["subtitle-edits"])


class SubtitleEditPayload(BaseModel):
    source_text: str = ""
    translated_text: str = ""
    edited_text: str = ""
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


@router.patch("/subtitles/{segment_id}")
def update_subtitle(segment_id: int, payload: SubtitleEditPayload, session: Session = Depends(get_session)) -> dict:
    segment = session.get(SubtitleSegment, segment_id)
    if segment is None:
        raise HTTPException(status_code=404, detail="Subtitle segment not found")

    segment.source_text = payload.source_text
    segment.translated_text = payload.translated_text
    segment.edited_text = payload.edited_text
    segment.start_ms = payload.start_ms
    segment.end_ms = payload.end_ms
    segment.is_edited = True
    session.commit()
    return {"id": segment.id, "status": "updated"}
