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
- Added media pipeline services and API shells:
  - `backend/app/services/media_probe.py`
  - `backend/app/services/audio_extractor.py`
  - `backend/app/services/subtitle_writer.py`
  - `backend/app/services/job_pipeline.py`
  - `backend/app/services/file_utils.py`
  - API routes for processing, exporting, and editing subtitles
- Added frontend foundation:
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - React entrypoint and API client
  - Workstation UI shell with project form, project list, media queue, player placeholder, subtitle table, and logs
  - Subtitle edit panel and processing/export/save actions
- Added project hygiene:
  - `.gitignore`
  - `.env.example`
  - `README.md`
- Added backend tests:
  - subtitle timestamp formatting
  - subtitle export selection priority
  - file fingerprint behavior

## Current Capabilities

- Backend can initialize SQLite tables.
- Backend can create projects.
- Backend can scan a project media directory for `.mkv`, `.mp4`, and `.mov`.
- Backend stores media fingerprints based on path, size, and modified time.
- Frontend can create a project, scan it, list media, and show placeholder subtitle data.
- Frontend can select a subtitle row, edit text and timestamps, and call save/export/process APIs.
- Pure helper functions for timestamp formatting and file fingerprinting now have direct tests.

## Verification

- Python backend syntax was checked with AST parsing and passed.
- `python -m compileall backend\app` was attempted, but Windows denied writes to generated `__pycache__` files. This appears to be a local filesystem permission issue, not a syntax failure.
- Backend tests have been added but not run yet because the test runner environment has not been set up.
- Pure-function verification passed for file fingerprinting and timestamp formatting.
- The generated `__pycache__` paths are ignored by `.gitignore`.
- Frontend build has not been run yet because dependencies have not been installed.

## Not Implemented Yet

- faster-whisper transcription.
- translator interface and translation implementation.
- job queue execution and durable background worker loop.
- translator retry and batch recovery behavior.
- serving frontend static files from FastAPI.
- Dockerfile / compose.

## Next Steps

1. Run lightweight backend import/schema checks.
2. Install frontend dependencies and run a build when network/dependency access is available.
3. Add tests for scanner, timestamp formatting, and subtitle export.
4. Connect the job pipeline to a real transcriber implementation.
5. Serve the built frontend from FastAPI and add a Docker packaging pass.
