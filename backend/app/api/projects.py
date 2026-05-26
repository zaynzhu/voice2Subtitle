from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.entities import Project
from app.models.schemas import ProjectCreate, ProjectRead, ScanResult
from app.services.scanner import scan_project_media

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_session)) -> list[Project]:
    return list(session.scalars(select(Project).order_by(Project.created_at.desc())))


@router.post("", response_model=ProjectRead)
def create_project(payload: ProjectCreate, session: Session = Depends(get_session)) -> Project:
    project = Project(
        name=payload.name,
        media_root=payload.media_root,
        output_mode=payload.output_mode,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.post("/{project_id}/scan", response_model=ScanResult)
def scan_project(project_id: int, session: Session = Depends(get_session)) -> ScanResult:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        stats = scan_project_media(session, project)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ScanResult(
        project_id=project.id,
        found=stats.found,
        created=stats.created,
        updated=stats.updated,
        skipped=stats.skipped,
    )
