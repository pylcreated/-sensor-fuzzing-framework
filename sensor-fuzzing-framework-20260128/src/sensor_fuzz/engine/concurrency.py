"""Concurrency helpers using asyncio.

- ``TaskRunner`` keeps backward compatibility with the old thread-pool based
    executor (still used by some drivers/tests).
- ``AsyncBoundedExecutor`` is a new, fully-async helper that gates concurrency
    with a semaphore and applies per-task timeouts. It is designed for the
    refactored execution engine targeting high-throughput async IO.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, Iterable, List, Optional


class TaskRunner:
    """Run tasks concurrently with bounded thread pool."""

    def __init__(self, max_workers: int = 32) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create a new loop if none is set (common in thread/bootstrap contexts)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop

    async def run_calls(self, funcs: Iterable[Callable[[], Any]]) -> List[Any]:
        """异步方法说明：执行 run calls 相关流程。"""
        tasks = [self._loop.run_in_executor(self._executor, f) for f in funcs]
        return await asyncio.gather(*tasks)

    async def run_coroutines(self, coros: Iterable[Awaitable[Any]]) -> List[Any]:
        """异步方法说明：执行 run coroutines 相关流程。"""
        return await asyncio.gather(*coros)

    def shutdown(self) -> None:
        """方法说明：执行 shutdown 相关逻辑。"""
        self._executor.shutdown(wait=False)


class AsyncBoundedExecutor:
    """Run coroutines with bounded concurrency and optional per-task timeout."""

    def __init__(self, max_concurrency: int = 64, task_timeout: Optional[float] = None) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self._task_timeout = task_timeout

    async def _wrap(self, coro: Awaitable[Any]) -> Any:
        """异步方法说明：执行  wrap 相关流程。"""
        async with self._semaphore:
            if self._task_timeout:
                return await asyncio.wait_for(coro, timeout=self._task_timeout)
            return await coro

    async def run(self, coros: Iterable[Awaitable[Any]]) -> List[Any]:
        """Execute coroutines with bounded concurrency.

        Args:
            coros: iterable of coroutines to execute.

        Returns:
            List of coroutine results in submission order.
        """

        tasks = [asyncio.create_task(self._wrap(c)) for c in coros]
        return await asyncio.gather(*tasks)

    def resize(self, max_concurrency: int) -> None:
        """Resize the concurrency window (used by adaptive controllers)."""
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))

    def set_timeout(self, timeout: Optional[float]) -> None:
        """方法说明：执行 set timeout 相关逻辑。"""
        self._task_timeout = timeout
