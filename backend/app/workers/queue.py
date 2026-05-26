"""全局单例内存任务队列，用于串行后台 Worker 的任务调度。"""

import collections
import threading


class JobQueue:
    """线程安全的内存 FIFO 任务队列。

    内部使用 collections.deque 存储待处理的 media_item_id，
    并用 threading.Lock 保证并发安全。
    """

    def __init__(self) -> None:
        self._deque: collections.deque[int] = collections.deque()
        self._lock = threading.Lock()

    def enqueue(self, media_item_id: int) -> None:
        """将 media_item_id 入队。若已在队列中则忽略（去重）。"""
        with self._lock:
            if media_item_id not in self._deque:
                self._deque.append(media_item_id)

    def dequeue(self) -> int | None:
        """取出最早入队的 id，队列为空时返回 None。"""
        with self._lock:
            if self._deque:
                return self._deque.popleft()
            return None

    def is_empty(self) -> bool:
        """判断队列是否为空。"""
        with self._lock:
            return len(self._deque) == 0

    def size(self) -> int:
        """返回队列中当前的任务数量。"""
        with self._lock:
            return len(self._deque)


# 模块级全局单例
job_queue: JobQueue = JobQueue()
