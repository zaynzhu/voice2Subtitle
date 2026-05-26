from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import MediaItem, Project
from app.models.schemas import MediaItemRead

router = APIRouter(prefix="/api", tags=["media"])


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
