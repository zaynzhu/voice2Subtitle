from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaProbeResult:
    duration_ms: int | None
    width: int | None
    height: int | None
    audio_streams: int
    video_streams: int


def probe_media(path: str | Path) -> MediaProbeResult:
    media_path = Path(path)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(media_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    payload = json.loads(result.stdout or "{}")
    format_info = payload.get("format", {})
    streams = payload.get("streams", [])

    duration_ms: int | None = None
    duration_value = format_info.get("duration")
    if duration_value is not None:
        try:
            duration_ms = int(float(duration_value) * 1000)
        except (TypeError, ValueError):
            duration_ms = None

    width = None
    height = None
    audio_streams = 0
    video_streams = 0

    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type == "audio":
            audio_streams += 1
        elif codec_type == "video":
            video_streams += 1
            width = width or stream.get("width")
            height = height or stream.get("height")

    return MediaProbeResult(
        duration_ms=duration_ms,
        width=width,
        height=height,
        audio_streams=audio_streams,
        video_streams=video_streams,
    )
