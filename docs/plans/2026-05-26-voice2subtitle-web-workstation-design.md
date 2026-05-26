# Voice2Subtitle Web Workstation Design

## Background

The current prototype in `E:\temp\测试翻译` is a single Python script that scans a directory for `.mkv` files, extracts audio with FFmpeg, transcribes Japanese speech with Whisper, translates text to Simplified Chinese with `deep-translator`, and writes `.srt` files next to the videos.

The new project should turn that prototype into a local web-based subtitle workstation. The first version should prioritize a reliable end-to-end workflow, clear task state, editable subtitles, and a clean path to later Docker deployment.

## Product Direction

Voice2Subtitle is a single-user local web application for generating, reviewing, editing, and exporting subtitles from local video files.

The first version is not a realtime live-captioning system. It processes existing media files and stores intermediate results so failed steps can be retried without starting over.

The application will run locally first and listen on:

```text
http://127.0.0.1:19000
```

Later, the same architecture should be packaged into Docker and pointed at mounted media directories on a NAS.

## First-Version Scope

Included:

- Create a project bound to a local media folder.
- Scan `.mkv`, `.mp4`, and `.mov` files.
- Probe media metadata with `ffprobe`.
- Extract 16 kHz mono audio with `ffmpeg`.
- Transcribe speech with `faster-whisper`.
- Translate recognized text through a pluggable translator interface.
- Store projects, media items, jobs, logs, and subtitle segments in SQLite.
- Show a web UI with video list, player, subtitle editor, progress, and logs.
- Edit subtitle text and timestamps.
- Export `.srt` and later `.vtt`.
- Resume or retry failed work from the last durable stage.

Deferred:

- True realtime subtitles.
- Multi-user authentication.
- Professional waveform editing.
- Complex timeline editing.
- Streaming transcoding.
- Speaker diarization.
- Distributed workers.

## Recommended Technology Stack

Backend:

- Python
- FastAPI
- SQLite with WAL mode
- SQLAlchemy or SQLModel
- Pydantic schemas
- `ffmpeg` and `ffprobe`
- `faster-whisper`

Frontend:

- React
- Vite
- TypeScript
- HTML5 video
- Table-based subtitle editor

Deployment:

- Local development first.
- Docker Compose later.
- Single-container API plus worker for the first Docker version.
- Optional GPU worker after the core product is stable.

## Architecture

The backend is split into API, services, workers, and persistence.

```text
backend/
  app/
    main.py
    config.py
    db.py
    api/
      projects.py
      media.py
      jobs.py
      subtitles.py
    services/
      scanner.py
      media_probe.py
      audio_extractor.py
      transcriber.py
      translator.py
      subtitle_writer.py
    workers/
      queue.py
      processor.py
    models/
      entities.py
      schemas.py

frontend/
  src/
    app/
    components/
    pages/
    api/
    stores/
    styles/
```

The first worker can be an in-process serial queue. This keeps resource usage predictable and avoids overloading CPU, disk, or GPU. The queue can later be replaced by a separate worker process without changing the user-facing workflow.

## Data Flow

```text
Create project
-> Save media root
-> Scan video files
-> Insert or update media_items
-> User starts processing
-> Create job
-> Probe video with ffprobe
-> Extract audio with ffmpeg
-> Transcribe with faster-whisper
-> Save source subtitle segments
-> Translate segments
-> Save translated subtitle segments
-> Mark ready_for_review
-> User edits subtitles
-> Export srt/vtt
```

Every important stage writes to SQLite. The system should never depend on only in-memory task state for long-running media work.

## Database Design

Use SQLite for the first version. It fits the local single-user workflow, is easy to back up, and will be simple to mount as `/data/app.sqlite3` in Docker.

SQLite should run with WAL mode:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

Core tables:

```text
projects
  id
  name
  media_root
  output_mode
  created_at
  updated_at

media_items
  id
  project_id
  file_path
  file_name
  duration_ms
  status
  source_language
  target_language
  subtitle_path
  fingerprint
  created_at
  updated_at

jobs
  id
  media_item_id
  type
  status
  stage
  progress
  error_code
  error_message
  started_at
  finished_at
  created_at

subtitle_segments
  id
  media_item_id
  index_no
  start_ms
  end_ms
  source_text
  translated_text
  edited_text
  confidence
  speaker
  is_edited
  created_at
  updated_at

job_logs
  id
  job_id
  level
  message
  created_at
```

File fingerprints should include path, file size, and last modified time so rescans can avoid duplicates while still detecting changed files.

## Status Model

Media statuses:

```text
new
queued
probing
extracting_audio
transcribing
transcribed
translating
translated
ready_for_review
exported
failed
```

Job statuses:

```text
pending
running
succeeded
failed
canceled
interrupted
```

When the backend starts, any `running` jobs from a previous process should be marked `interrupted`. If the related media item already has source subtitle segments, the user should be able to resume from translation or review.

## Transcription Strategy

Use a `Transcriber` interface instead of binding the project directly to one library.

First implementation:

```text
FasterWhisperTranscriber
```

Supported models:

```text
tiny
base
small
medium
```

Runtime modes:

```text
Windows GPU: cuda + float16
CPU / NAS: cpu + int8
```

The local first version can default to `base` or `small`. `medium` should remain configurable, but should not be the assumed default for CPU or NAS environments.

## Translation Strategy

Use a `Translator` interface:

```text
translate_segments(source_lang, target_lang, segments)
```

The first implementation can use `deep-translator` because it matches the existing prototype. Translation failures must be recoverable:

- Single segment failure keeps the source text and records a warning.
- Batch failure keeps all transcribed source segments.
- Retrying translation must not overwrite user-edited subtitle text.

Export text priority:

```text
edited_text > translated_text > source_text
```

This keeps manual edits durable even if translation is rerun.

## Web UI

Use a single-page application layout:

```text
Left: project and video list
Center: video player and subtitle overlay
Right: subtitle editor table
Bottom: job progress and logs
```

Core interactions:

- Scan a media folder.
- Filter videos by status.
- Start selected video processing.
- Start all unprocessed videos.
- Pause or cancel queued work.
- View job stage, elapsed time, and recent logs.
- Click a subtitle row to seek the player.
- Highlight the active subtitle row during playback.
- Edit text and timestamps.
- Save edits to SQLite.
- Export subtitles beside the video or to a configured output folder.

## Error Handling

Failures should be explicit and recoverable.

Error codes:

```text
media_probe_failed
audio_extract_failed
model_load_failed
transcribe_failed
translate_failed
subtitle_export_failed
filesystem_permission
```

The UI should show the failed stage, error code, user-readable message, and recent logs. For example:

```text
Translation failed: GoogleTranslator timed out. Transcription results were saved and translation can be retried later.
```

## Local Configuration

Initial local configuration can use `.env`:

```text
V2S_HOST=127.0.0.1
V2S_PORT=19000
V2S_DB_PATH=./data/app.sqlite3
V2S_CACHE_DIR=./data/cache
V2S_MODEL_ROOT=./models/whisper
V2S_OUTPUT_MODE=beside_video
V2S_DEFAULT_SOURCE_LANG=auto
V2S_DEFAULT_TARGET_LANG=zh-CN
V2S_WHISPER_MODEL=base
V2S_WHISPER_DEVICE=auto
V2S_WHISPER_COMPUTE_TYPE=auto
```

Large generated files, model files, cache files, and databases should not be committed.

## Docker Direction

Docker packaging should come after the local web version works.

Expected Docker volume shape:

```yaml
volumes:
  - /path/to/videos:/media/videos
  - /path/to/models:/models/whisper
  - /path/to/data:/data
environment:
  V2S_MEDIA_ROOT: /media/videos
  V2S_MODEL_ROOT: /models/whisper
  V2S_DB_PATH: /data/app.sqlite3
  V2S_OUTPUT_MODE: beside_video
ports:
  - "19000:19000"
```

For a NAS such as the ZSpace Z4S, the CPU mode should be treated as the default:

```text
device=cpu
compute_type=int8
worker_concurrency=1
```

GPU acceleration can be added later through an optional worker profile.

## Testing Strategy

Unit tests:

- Timestamp formatting.
- SRT export.
- Directory scanning and fingerprint deduplication.
- Status transitions.
- Translation failure fallback.
- Edited subtitle export priority.

Integration or manual tests:

- `ffprobe` metadata extraction.
- `ffmpeg` audio extraction.
- `faster-whisper` transcription with a short fixture.
- End-to-end processing of one short media file.

The first automated test suite should use mock transcriber and translator implementations. It should not require downloading Whisper models.

## Implementation Phases

Phase 1: Project foundation

- Create backend and frontend structure.
- Add local configuration.
- Add SQLite schema and migrations.
- Add project and media scanning APIs.

Phase 2: Processing pipeline

- Add ffprobe and ffmpeg services.
- Add transcriber interface and `faster-whisper` implementation.
- Add translator interface and first translator implementation.
- Add serial background worker and job logs.

Phase 3: Review UI

- Add video list, player, task status, and logs.
- Add subtitle editor table.
- Add save and export actions.

Phase 4: Robustness

- Add resume/retry behavior.
- Add interrupted job recovery.
- Add test coverage for core services.
- Improve error reporting.

Phase 5: Docker

- Add production build.
- Serve frontend from FastAPI.
- Add Dockerfile and compose example.
- Validate CPU mode on NAS-like settings.
