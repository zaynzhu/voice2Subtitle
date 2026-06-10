from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.entities import Job, MediaItem, Project
from app.services.job_pipeline import _make_progress_reporter


def test_progress_reporter_maps_stage_progress_and_throttles() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        project = Project(name="test", media_root=".")
        media_item = MediaItem(
            project=project,
            file_path="sample.mp4",
            file_name="sample.mp4",
            fingerprint="sample",
        )
        job = Job(
            media_item=media_item,
            type="process_media",
            status="running",
            stage="transcribing",
            progress=0.25,
        )
        session.add(project)
        session.add(media_item)
        session.add(job)
        session.commit()
        session.refresh(job)

        report = _make_progress_reporter(session, job, 0.25, 0.60)
        report(0.5)
        assert round(job.progress, 3) == 0.425

        report(0.6)
        assert round(job.progress, 3) == 0.425

        report(1.0)
        assert round(job.progress, 3) == 0.600
