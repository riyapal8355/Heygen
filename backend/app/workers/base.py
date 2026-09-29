"""Base Celery Task and async execution bridge."""

import asyncio
import threading
from typing import Any, Coroutine
from celery import Task
from app.core.logging import get_logger

logger = get_logger(__name__)

_worker_loop = None
_worker_thread = None
_worker_lock = threading.Lock()


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop, _worker_thread
    with _worker_lock:
        if _worker_loop is None or not _worker_loop.is_running():
            _worker_loop = asyncio.new_event_loop()

            def run_loop(loop: asyncio.AbstractEventLoop):
                asyncio.set_event_loop(loop)
                loop.run_forever()

            _worker_thread = threading.Thread(target=run_loop, args=(_worker_loop,), daemon=True)
            _worker_thread.start()
        return _worker_loop


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Execute an asyncio coroutine within synchronous Celery worker context safely."""
    loop = _get_worker_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()


class HeyZenBaseTask(Task):
    """Base Celery task providing structured logging and error interception."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Celery task %s [%s] failed: %s",
            self.name,
            task_id,
            exc,
            exc_info=einfo,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Celery task %s [%s] retrying: %s",
            self.name,
            task_id,
            exc,
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "Celery task %s [%s] completed successfully",
            self.name,
            task_id,
        )
        super().on_success(retval, task_id, args, kwargs)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        pass
