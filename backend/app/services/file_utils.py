from __future__ import annotations

from pathlib import Path


def fingerprint_file(path: Path) -> str:
    stat = path.stat()
    return f"{path.resolve()}::{stat.st_size}::{int(stat.st_mtime)}"


def existing_subtitle_path(path: Path) -> str | None:
    srt_path = path.with_suffix(".srt")
    if srt_path.exists():
        return str(srt_path)
    return None
