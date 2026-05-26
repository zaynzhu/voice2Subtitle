"""串行后台处理器：从 JobQueue 中依次取出任务并执行 job pipeline。"""

import logging
import threading
import time

from app.workers.queue import JobQueue

logger = logging.getLogger(__name__)


class SerialProcessor:
    """串行 Worker 处理器。

    每次从 JobQueue 中取出一个 media_item_id，
    创建新的数据库 session，调用 run_processing_pipeline 执行处理。
    通过后台 daemon 线程保持持续运行。
    """

    def __init__(self, session_factory, queue: JobQueue) -> None:
        """初始化串行处理器。

        Args:
            session_factory: 可调用对象，调用后返回一个新的 SQLAlchemy Session（即 SessionLocal）。
            queue: JobQueue 实例，提供待处理的 media_item_id。
        """
        self._session_factory = session_factory
        self._queue = queue
        self._running: bool = False
        self._thread: threading.Thread | None = None

    def recover_interrupted_jobs(self) -> int:
        """恢复被意外中断的 Job。

        查找所有 status='running' 的 Job，
        将其 status 改为 'interrupted'，stage 改为 'interrupted'，
        并将对应的 MediaItem status 改为 'failed'。

        Returns:
            被恢复（标记为 interrupted）的 Job 数量。
        """
        from app.models.entities import Job, MediaItem

        session = self._session_factory()
        try:
            # 查询所有仍在运行状态的 Job
            running_jobs: list[Job] = (
                session.query(Job).filter(Job.status == "running").all()
            )

            if not running_jobs:
                return 0

            recovered_count = 0
            for job in running_jobs:
                # 将 Job 标记为 interrupted
                job.status = "interrupted"
                job.stage = "interrupted"

                # 将对应的 MediaItem 标记为 failed
                media_item: MediaItem | None = session.get(
                    MediaItem, job.media_item_id
                )
                if media_item is not None:
                    media_item.status = "failed"

                recovered_count += 1

            session.commit()
            logger.info("恢复了 %d 个被中断的 Job", recovered_count)
            return recovered_count
        except Exception:
            session.rollback()
            logger.exception("恢复中断 Job 时发生错误")
            return 0
        finally:
            session.close()

    def start(self) -> None:
        """启动后台 daemon 线程，运行 _worker_loop。"""
        self._running = True
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="SerialProcessor-Worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("SerialProcessor 后台 worker 线程已启动")

    def stop(self) -> None:
        """通知后台 worker 线程停止。"""
        self._running = False
        logger.info("SerialProcessor 后台 worker 线程已请求停止")

    def _worker_loop(self) -> None:
        """后台 worker 主循环。

        持续从队列中取出 media_item_id 并调用 pipeline 处理。
        队列为空时每秒轮询一次。
        """
        from app.models.entities import MediaItem
        from app.services.job_pipeline import run_processing_pipeline

        logger.info("SerialProcessor _worker_loop 开始运行")

        while self._running:
            media_item_id = self._queue.dequeue()

            # 队列为空，等待 1 秒后继续
            if media_item_id is None:
                time.sleep(1)
                continue

            logger.info("开始处理 media_item_id=%d", media_item_id)
            session = self._session_factory()
            try:
                # 查询对应的 MediaItem
                media_item: MediaItem | None = session.get(
                    MediaItem, media_item_id
                )
                if media_item is None:
                    logger.warning(
                        "media_item_id=%d 不存在，跳过本次处理", media_item_id
                    )
                    continue

                # 调用 job pipeline 执行实际处理
                run_processing_pipeline(session, media_item)
                logger.info("media_item_id=%d 处理完成", media_item_id)
            except Exception:
                logger.exception(
                    "处理 media_item_id=%d 时发生异常", media_item_id
                )
            finally:
                session.close()

        logger.info("SerialProcessor _worker_loop 已退出")


# 模块级全局单例（None 表示尚未初始化）
processor: SerialProcessor | None = None


def init_processor(session_factory) -> SerialProcessor:
    """初始化全局 SerialProcessor 单例并返回。

    Args:
        session_factory: 可调用对象，调用后返回新的 SQLAlchemy Session（即 SessionLocal）。

    Returns:
        初始化完成的 SerialProcessor 实例。
    """
    global processor
    from app.workers.queue import job_queue

    processor = SerialProcessor(session_factory=session_factory, queue=job_queue)
    return processor
