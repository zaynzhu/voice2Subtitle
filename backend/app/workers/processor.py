"""串行后台处理器：从 JobQueue 中依次取出任务并执行 job pipeline。"""

import logging
import threading
import time

from app.workers.queue import JobQueue

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    """任务被用户主动取消时抛出的异常。"""


class SerialProcessor:
    """串行 Worker 处理器。

    每次从 JobQueue 中取出一个 media_item_id，
    创建新的数据库 session，调用 run_processing_pipeline 执行处理。
    通过后台 daemon 线程保持持续运行。
    支持通过 cancel_current() 取消当前正在执行的任务。
    """

    def __init__(self, session_factory, queue: JobQueue) -> None:
        self._session_factory = session_factory
        self._queue = queue
        self._running: bool = False
        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()

    def cancel_current(self) -> dict:
        """取消当前正在执行的任务并清空队列中所有等待任务。

        Returns:
            包含 cancelled_count 和 cleared_count 的字典。
        """
        logger.info("收到取消当前任务的请求")
        self._cancel_event.set()
        cleared = self._queue.clear()
        logger.info("已清空队列中 %d 个等待任务", cleared)
        return {"cleared_queue": cleared}

    def recover_interrupted_jobs(self) -> int:
        """恢复被意外中断的 Job。

        查找所有 status='running' 的 Job，
        将其 status 改为 'interrupted'，stage 改为 'interrupted'，
        并将对应的 MediaItem status 改为 'failed'。

        Returns:
            被恢复（标记为 interrupted）的 Job 数量。
        """
        from app.models.entities import Job, MediaItem

        with self._session_factory() as session:
            try:
                running_jobs: list[Job] = (
                    session.query(Job).filter(Job.status == "running").all()
                )

                if not running_jobs:
                    return 0

                recovered_count = 0
                for job in running_jobs:
                    job.status = "interrupted"
                    job.stage = "interrupted"

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

    def stop(self, timeout: float | None = 5.0) -> None:
        """通知后台 worker 线程停止并等待其退出。"""
        self._running = False
        logger.info("SerialProcessor 后台 worker 线程已请求停止")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            logger.info("SerialProcessor 后台 worker 线程已停止")

    def _worker_loop(self) -> None:
        """后台 worker 主循环。

        持续从队列中取出 media_item_id 并调用 pipeline 处理。
        队列为空时每秒轮询一次。
        支持通过 cancel_event 取消当前任务。
        """
        from app.models.entities import MediaItem
        from app.services.job_pipeline import run_processing_pipeline

        logger.info("SerialProcessor _worker_loop 开始运行")

        while self._running:
            # 在 dequeue 前清除残留取消信号，避免毒杀新任务
            self._cancel_event.clear()
            media_item_id = self._queue.dequeue()

            if media_item_id is None:
                time.sleep(1)
                continue

            # dequeue 后再次检查：若 clear 之后、dequeue 之后有新的 cancel 到达，跳过此任务
            if self._cancel_event.is_set():
                logger.info("media_item_id=%d 在入队后收到取消信号，跳过", media_item_id)
                continue

            logger.info("开始处理 media_item_id=%d", media_item_id)
            try:
                with self._session_factory() as session:
                    media_item: MediaItem | None = session.get(
                        MediaItem, media_item_id
                    )
                    if media_item is None:
                        logger.warning(
                            "media_item_id=%d 不存在，跳过本次处理", media_item_id
                        )
                        continue

                    run_processing_pipeline(session, media_item, cancel_event=self._cancel_event)
                logger.info("media_item_id=%d 处理完成", media_item_id)
            except JobCancelled:
                logger.info("media_item_id=%d 的任务已被用户取消", media_item_id)
                self._cancel_event.clear()
            except Exception:
                logger.exception(
                    "处理 media_item_id=%d 时发生异常", media_item_id
                )

        logger.info("SerialProcessor _worker_loop 已退出")


# 模块级全局单例（None 表示尚未初始化）
processor: SerialProcessor | None = None


def init_processor(session_factory) -> SerialProcessor:
    """初始化全局 SerialProcessor 单例并返回。"""
    global processor
    from app.workers.queue import job_queue

    processor = SerialProcessor(session_factory=session_factory, queue=job_queue)
    return processor