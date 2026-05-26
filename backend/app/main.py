import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import exports, health, jobs, media, projects, subtitle_edits, subtitles
from app.db import SessionLocal, init_db
from app.workers.processor import init_processor

# 全局 processor 引用，在 on_startup 中初始化
_processor = None


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
        global _processor
        # 初始化数据库表结构
        init_db()
        # 初始化串行 Worker 处理器
        _processor = init_processor(SessionLocal)
        # 恢复上次异常中断的 Job
        recovered = _processor.recover_interrupted_jobs()
        if recovered:
            logging.getLogger(__name__).warning(
                "恢复了 %d 个被中断的 job", recovered
            )
        # 启动后台 worker 线程
        _processor.start()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        # 通知后台 worker 线程停止
        if _processor:
            _processor.stop()

    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(media.router)
    app.include_router(subtitles.router)
    app.include_router(subtitle_edits.router)
    app.include_router(jobs.router)
    app.include_router(exports.router)
    return app


app = create_app()
