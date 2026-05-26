from __future__ import annotations

from datetime import timedelta
from pathlib import Path


def format_timestamp(milliseconds: int) -> str:
    total_seconds, ms = divmod(int(milliseconds), 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def choose_segment_text(segment) -> str:
    for value in (
        getattr(segment, "edited_text", ""),
        getattr(segment, "translated_text", ""),
        getattr(segment, "source_text", ""),
    ):
        if value and value.strip():
            return value.strip()
    return ""


def write_srt(segments, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    for index, segment in enumerate(segments, start=1):
        lines.append(str(index))
        lines.append(
            f"{format_timestamp(segment.start_ms)} --> {format_timestamp(segment.end_ms)}"
        )
        lines.append(choose_segment_text(segment))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
