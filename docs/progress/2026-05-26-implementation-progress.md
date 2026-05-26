# Implementation Progress - 2026-05-26

## Goal

Build Voice2Subtitle as a local web-based subtitle workstation first, then Dockerize it later. The local backend should listen on port `19000`.

## Completed

- Created and committed the design document:
  - `docs/plans/2026-05-26-voice2subtitle-web-workstation-design.md`
- Added backend foundation:
  - `backend/pyproject.toml`
  - `backend/app/config.py`
  - `backend/app/db.py`
  - `backend/app/main.py`
  - API routers for health, projects, media, and subtitles
  - SQLite models for projects, media items, jobs, subtitle segments, and job logs
  - Pydantic schemas
  - Media scanner service
- Added frontend foundation:
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - React entrypoint and API client
  - Workstation UI shell with project form, project list, media queue, player placeholder, subtitle table, and logs
- Added project hygiene:
  - `.gitignore`
  - `.env.example`
  - `README.md`

## Current Capabilities

- Backend can initialize SQLite tables.
- Backend can create projects.
- Backend can scan a project media directory for `.mkv`, `.mp4`, and `.mov`.
- Backend stores media fingerprints based on path, size, and modified time.
- Frontend can create a project, scan it, list media, and show placeholder subtitle data.

## Verification

- Python backend syntax was checked with AST parsing and passed.
- `python -m compileall backend\app` was attempted, but Windows denied writes to generated `__pycache__` files. This appears to be a local filesystem permission issue, not a syntax failure.
- The generated `__pycache__` paths are ignored by `.gitignore`.
- Frontend build has not been run yet because dependencies have not been installed.

## Not Implemented Yet

- ffprobe metadata extraction.
- ffmpeg audio extraction.
- faster-whisper transcription.
- translator interface and translation implementation.
- job queue execution.
- subtitle editing save API.
- SRT export.
- serving frontend static files from FastAPI.
- tests.
- Dockerfile / compose.

## Next Steps

1. Run lightweight backend import/schema checks.
2. Install frontend dependencies and run a build when network/dependency access is available.
3. Add tests for scanner and subtitle formatting.
4. Add `media_probe.py` and duration population through `ffprobe`.
5. Add job queue shell before connecting Whisper.
