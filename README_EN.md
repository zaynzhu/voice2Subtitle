<div align="center">

# 🐍 Voice2Subtitle

Local video-to-subtitle workstation — 100% offline

[English](README_EN.md) | [中文](README.md)

</div>

<div align="center">

![License](https://img.shields.io/github/license/zaynzhu/voice2Subtitle?style=for-the-badge)
![Stars](https://img.shields.io/github/stars/zaynzhu/voice2Subtitle?style=for-the-badge)
![Last Commit](https://img.shields.io/github/last-commit/zaynzhu/voice2Subtitle?style=for-the-badge)
![Issues](https://img.shields.io/github/issues/zaynzhu/voice2Subtitle?style=for-the-badge)

</div>

---

> [!TIP]
> Scan local video folders, automatically extract audio, transcribe speech (dual Whisper engines), translate, and generate bilingual subtitles.
> Built-in video player with real-time subtitle overlay, manual editing support, and standard SRT export. Optimized for low-VRAM GPUs — runs smoothly on RTX 3050Ti 4GB.

---

## ✨ Features

- **Dual-Engine Transcription** — Auto-detects `faster-whisper` (CTranslate2) and `openai-whisper` (PyTorch .pt) availability, matches local model format
- **Auto Translation** — Google Translate integration, multi-language support, auto-skips failed sentences without breaking the pipeline
- **Video Player** — Built-in HTML5 player, 12+ video formats, real-time subtitle overlay, click subtitle to jump to timestamp
- **Subtitle Editing** — Bilingual subtitle list, edit source/translation/final text with priority override
- **Batch Processing** — Serial task queue, select and process multiple videos, cancel mid-task anytime
- **GPU Memory Management** — One-click VRAM release, optimized for low-VRAM environments (e.g. RTX 3050Ti 4GB)
- **Task Cancellation** — Stop running transcription tasks, clear queue, release GPU resources at any time
- **SRT Export** — One-click export of standard SRT subtitle files, saved alongside the video

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/zaynzhu/voice2Subtitle.git
cd voice2Subtitle

# Install backend dependencies
cd backend && pip install -e ".[ml]"

# Install frontend dependencies
cd ../frontend && npm install

# Launch (project root)
cd ..
python start-backend.py          # Backend: auto-selects best Python env
# In another terminal
cd frontend && npm run dev       # Frontend: http://127.0.0.1:19000
```

---

## 📦 Installation

### Smart Launch Script (Recommended)

```bash
python start-backend.py
```

Automatically searches PATH and conda environments for the Python installation with the most complete engine support.

### Manual Launch

```bash
# Backend (in backend/ directory)
python -m uvicorn app.main:app --host 127.0.0.1 --port 19001 --reload

# Frontend (in frontend/ directory)
npm run dev
```

### Production Deployment

```bash
cd frontend && npm run build    # Build frontend
cd ../backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 19000
# Backend auto-mounts frontend/dist/ as static files
```

### Requirements

- Python 3.11+
- Node.js 18+
- FFmpeg (audio extraction)
- CUDA optional (GPU-accelerated transcription)

### Whisper Models

Place model files in the project root `whisper_model/` directory:

```
whisper_model/
├── medium.pt           # OpenAI Whisper format (auto-uses openai-whisper engine)
└── medium-ct2/         # CTranslate2 format directory (auto-uses faster-whisper engine)
    ├── model.bin
    ├── config.json
    └── ...
```

Set `V2S_WHISPER_MODEL=auto` (default) to auto-scan the directory.

---

## 💡 Usage

### Scan Videos and Batch Process

1. Open http://127.0.0.1:19000 after launch
2. Click "New Project" and select a local video folder
3. Check the videos you want to process, click "Batch Process"
4. Wait for transcription to complete, view subtitles in the video player

### Edit Subtitles and Export

1. Click subtitle lines in the player to jump to the corresponding scene
2. Edit source text or translation directly in the subtitle list on the right
3. Click "Export SRT" to save alongside the video

### GPU Memory Management

The sidebar model card displays current engine status and GPU info. Click the "Release VRAM" button to clear GPU memory usage.

---

## 📚 Documentation

### Project Structure

```
voice2Subtitle/
├── backend/
│   └── app/
│       ├── api/            # REST routes: projects, media, subtitles, jobs, exports, models
│       ├── models/         # SQLAlchemy ORM + Pydantic schemas
│       ├── services/       # Core business: scanner, audio_extractor, transcriber, translator, subtitle_writer
│       ├── workers/        # Serial task queue + daemon thread processor
│       ├── config.py       # pydantic-settings config (V2S_ prefix)
│       ├── db.py           # SQLAlchemy + SQLite WAL session factory
│       └── main.py         # FastAPI application entry
├── frontend/
│   └── src/
│       ├── main.tsx        # React single-file SPA (no router, no component library)
│       ├── api/client.ts   # Typed fetch wrapper + API calls
│       └── styles/app.css  # CSS custom properties, glassmorphism style
├── whisper_model/          # Whisper model directory (gitignored)
├── data/                   # SQLite database + audio cache (gitignored)
├── start-backend.py        # Smart launch script
└── .env.example            # Environment variable example
```

### API Reference

#### Project Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/projects` | List projects |
| `POST` | `/api/projects` | Create project |
| `DELETE` | `/api/projects/{id}` | Delete project |
| `POST` | `/api/projects/{id}/scan` | Scan video files |
| `POST` | `/api/projects/browse` | Open folder picker dialog |

#### Media Operations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/projects/{id}/media` | List videos in project |
| `GET` | `/api/media/{id}` | Get video details |
| `GET` | `/api/media/{id}/stream` | Stream video (Range requests supported) |
| `POST` | `/api/media/{id}/process` | Submit processing task |
| `POST` | `/api/media/{id}/export` | Export SRT file |
| `POST` | `/api/media/unload-gpu` | Release GPU memory |

#### Tasks & Subtitles

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/media/{id}/jobs` | List tasks |
| `POST` | `/api/jobs/cancel` | Cancel task and release GPU |
| `GET` | `/api/media/{id}/subtitles` | List subtitle segments |
| `PATCH` | `/api/subtitles/{id}` | Edit subtitle segment |
| `GET` | `/api/models` | Get model and engine info |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `V2S_HOST` | `127.0.0.1` | Listen address |
| `V2S_PORT` | `19000` | Production mode port |
| `V2S_DB_PATH` | `./data/app.sqlite3` | Database path |
| `V2S_CACHE_DIR` | `./data/cache` | Audio cache directory |
| `V2S_MODEL_ROOT` | `whisper_model` | Whisper model directory |
| `V2S_WHISPER_MODEL` | `auto` | Model selection (auto scans directory) |
| `V2S_WHISPER_DEVICE` | `auto` | Inference device (auto: GPU→CPU) |
| `V2S_WHISPER_COMPUTE_TYPE` | `auto` | Compute type (auto: GPU float16, CPU int8) |
| `V2S_DEFAULT_SOURCE_LANG` | `auto` | Source language |
| `V2S_DEFAULT_TARGET_LANG` | `zh-CN` | Translation target language |
| `V2S_OUTPUT_MODE` | `beside_video` | SRT export location |

### Supported Video Formats

Scanner: `.mp4` `.mkv` `.mov` `.avi` `.wmv` `.flv` `.webm` `.ts` `.mpg` `.mpeg` `.m4v` `.3gp` `.rmvb` `.rm`

Player: `.mp4` `.mkv` `.mov` `.avi` `.wmv` `.flv` `.webm` `.ts` `.mpg` `.mpeg` `.m4v` `.3gp` `.mp3` `.wav` `.aac` `.flac` `.m4a` `.ogg` `.wma`

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy + SQLite (WAL) + Uvicorn |
| Frontend | React 18 + Vite + TypeScript + Lucide Icons |
| Transcription | faster-whisper / openai-whisper (dual-engine auto-selection) |
| Translation | deep-translator (Google Translate) |
| Audio | FFmpeg |

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/zaynzhu/voice2Subtitle.git
cd voice2Subtitle

# Backend
cd backend
pip install -e ".[dev]"
python -m pytest

# Frontend
cd ../frontend
npm install
npm run dev
```

---

## ⭐ Star History

<a href="https://star-history.com/#zaynzhu/voice2Subtitle&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=zaynzhu/voice2Subtitle&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=zaynzhu/voice2Subtitle&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=zaynzhu/voice2Subtitle&type=Date" />
 </picture>
</a>

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — see the [LICENSE](LICENSE) file for details.
