from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio(video_path: str | Path, audio_path: str | Path) -> Path:
    video = Path(video_path)
    audio = Path(audio_path)
    audio.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-vn",
        "-acodec",
        "mp3",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-b:a",
        "64k",
        str(audio),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg audio extraction failed")

    return audio
