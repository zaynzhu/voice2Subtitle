# AGENTS.md

This file provides guidance to AI agents working with code in this repository.

## Project

Voice2Subtitle — 本地视频转字幕工作站。FastAPI + React SPA。

## Quick Start

```bash
# 全栈启动（自动检测最佳 Python 环境）
python start-backend.py

# 或手动启动
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 19001 --reload
cd frontend && npm run dev    # 127.0.0.1:19000
```

## Commands

| Command | Dir | Purpose |
|---------|-----|---------|
| `python -m pytest` | backend/ | Run all tests |
| `python -m pytest tests/test_x.py` | backend/ | Run single test |
| `npm run build` | frontend/ | Production build → dist/ |

## Key Conventions

- **Python**: snake_case, backend/ as working directory
- **TypeScript**: camelCase vars, PascalCase components
- **API**: `/api/` prefix, defined in `backend/app/api/`
- **Frontend**: Chinese UI text, single-file App() component, no router/state library
- **Models**: placed in `whisper_model/` at project root (gitignored)
- **Config**: env vars with `V2S_` prefix, see `.env.example`

## Architecture Summary

- Backend: FastAPI + SQLAlchemy + SQLite WAL, serial worker thread
- Frontend: React SPA in single main.tsx (~600 lines), vanilla CSS
- Whisper: dual-engine (faster-whisper / openai-whisper), auto-detected at runtime
- Pipeline: scan → probe → extract audio → transcribe → translate → write SRT