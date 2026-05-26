from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, media, projects, subtitles
from app.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="Voice2Subtitle", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(media.router)
    app.include_router(subtitles.router)
    return app


app = create_app()
