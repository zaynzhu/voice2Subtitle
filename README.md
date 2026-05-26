# Voice2Subtitle

Local web workstation for generating, reviewing, editing, and exporting subtitles from video files.

Current status: Phase 1 foundation.

- Backend: FastAPI, SQLite WAL, project creation, media scanning, media and subtitle read APIs.
- Frontend: React/Vite workstation shell with project creation, scan action, media queue, preview area, subtitle table, and logs.
- Default backend port: `19000`.

## Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 19000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend development server and it will proxy API calls to `http://127.0.0.1:19000`.

## Notes

Large runtime artifacts are ignored by git:

- `data/`
- `models/`
- SQLite files
- frontend `node_modules/` and `dist/`

The original prototype is outside this repo at `E:\temp\测试翻译`.
