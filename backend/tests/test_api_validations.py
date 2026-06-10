import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.exports import export_media
from app.api.projects import create_project
from app.api.subtitle_edits import SubtitleEditPayload, update_subtitle
from app.db import Base
from app.models.entities import MediaItem, Project, SubtitleSegment
from app.models.schemas import ProjectCreate


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


def test_create_project_rejects_missing_media_root(tmp_path) -> None:
    with make_session() as session:
        payload = ProjectCreate(
            name="missing",
            media_root=str(tmp_path / "missing"),
            output_mode="beside_video",
        )

        with pytest.raises(HTTPException) as exc_info:
            create_project(payload, session)

        assert exc_info.value.status_code == 400
        assert "目录不存在" in exc_info.value.detail


def test_update_subtitle_rejects_invalid_time_range() -> None:
    with make_session() as session:
        project = Project(name="test", media_root=".")
        media_item = MediaItem(
            project=project,
            file_path="sample.mp4",
            file_name="sample.mp4",
            fingerprint="sample",
        )
        segment = SubtitleSegment(
            media_item=media_item,
            index_no=1,
            start_ms=0,
            end_ms=1000,
            source_text="hello",
        )
        session.add(project)
        session.add(media_item)
        session.add(segment)
        session.commit()
        session.refresh(segment)

        payload = SubtitleEditPayload(
            source_text="hello",
            translated_text="你好",
            edited_text="",
            start_ms=1000,
            end_ms=1000,
        )

        with pytest.raises(HTTPException) as exc_info:
            update_subtitle(segment.id, payload, session)

        assert exc_info.value.status_code == 400
        assert "结束时间必须晚于开始时间" in exc_info.value.detail


def test_export_media_rejects_empty_subtitles() -> None:
    with make_session() as session:
        project = Project(name="test", media_root=".")
        media_item = MediaItem(
            project=project,
            file_path="sample.mp4",
            file_name="sample.mp4",
            fingerprint="sample",
        )
        session.add(project)
        session.add(media_item)
        session.commit()
        session.refresh(media_item)

        with pytest.raises(HTTPException) as exc_info:
            export_media(media_item.id, session)

        assert exc_info.value.status_code == 400
        assert "没有可导出的字幕" in exc_info.value.detail
