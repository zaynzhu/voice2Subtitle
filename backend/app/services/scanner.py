from dataclasses import dataclass
from pathlib import Path

from app.services.file_utils import existing_subtitle_path, fingerprint_file
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import MediaItem, Project

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".mov"}


@dataclass(frozen=True)
class ScanStats:
    found: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0

def scan_project_media(
    session: Session,
    project: Project,
    *,
    default_source_lang: str = "auto",
    default_target_lang: str = "zh-CN",
) -> ScanStats:
    root = Path(project.media_root).expanduser()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Media root does not exist or is not a directory: {root}")

    found = created = updated = skipped = 0
    existing_by_path = {
        item.file_path: item
        for item in session.scalars(
            select(MediaItem).where(MediaItem.project_id == project.id)
        )
    }

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        found += 1
        resolved = str(path.resolve())
        fingerprint = fingerprint_file(path)
        item = existing_by_path.get(resolved)
        subtitle_path = existing_subtitle_path(path)

        if item is None:
            session.add(
                MediaItem(
                    project_id=project.id,
                    file_path=resolved,
                    file_name=path.name,
                    status="new",
                    source_language=default_source_lang,
                    target_language=default_target_lang,
                    subtitle_path=subtitle_path,
                    fingerprint=fingerprint,
                )
            )
            created += 1
            continue

        if item.fingerprint == fingerprint and item.subtitle_path == subtitle_path:
            skipped += 1
            continue

        item.file_name = path.name
        item.fingerprint = fingerprint
        item.subtitle_path = subtitle_path
        if item.status in {"failed", "exported"}:
            item.status = "new"
        updated += 1

    session.commit()
    return ScanStats(found=found, created=created, updated=updated, skipped=skipped)
