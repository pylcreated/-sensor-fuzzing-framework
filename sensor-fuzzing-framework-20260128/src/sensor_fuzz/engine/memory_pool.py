"""Memory optimization through object pooling for sensor fuzzing framework.

This module implements object pools to reduce memory allocation overhead and prevent
memory leaks in high-frequency object creation scenarios.
"""

from __future__ import annotations

import time
import threading
from queue import Queue, Empty, Full
from typing import Any, Callable, Generic, Optional, TypeVar
from contextlib import contextmanager

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """Generic object pool with configurable size and timeout-based recycling.

    Features:
    - Thread-safe operations using queue.Queue
    - Configurable maximum pool size
    - Automatic object creation via factory function
    - Timeout-based object recycling and cleanup
    - Statistics tracking for monitoring

    Args:
        factory: Callable that creates new objects when pool is empty
        max_size: Maximum number of objects to keep in pool (default: 100)
        timeout: Seconds after which idle objects are considered stale (default: 300)
        cleanup_interval: Seconds between cleanup runs (default: 60)
    """

    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = 100,
        timeout: float = 300.0,
        cleanup_interval: float = 60.0
    ):
        """方法说明：执行   init   相关逻辑。"""
        self.factory = factory
        self.max_size = max_size
        self.timeout = timeout
        self._pool: Queue[tuple[T, float]] = Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._stats = {
            'created': 0,
            'acquired': 0,
            'released': 0,
            'destroyed': 0,
            'hits': 0,  # objects reused from pool
            'misses': 0  # objects created new
        }

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True
        )
        self._cleanup_thread.start()
        self._last_cleanup = time.time()
        self._cleanup_interval = cleanup_interval

    def acquire(self, timeout: Optional[float] = None) -> T:
        """Acquire an object from the pool, creating one if necessary.

        Args:
            timeout: Maximum time to wait for an object (default: None, no wait)

        Returns:
            Object from pool or newly created
        """
        try:
            obj, _ = self._pool.get(timeout=timeout)
            with self._lock:
                self._stats['acquired'] += 1
                self._stats['hits'] += 1
            return obj
        except Empty:
            # Pool empty, create new object
            obj = self.factory()
            with self._lock:
                self._stats['created'] += 1
                self._stats['acquired'] += 1
                self._stats['misses'] += 1
            return obj

    def release(self, obj: T) -> None:
        """Return an object to the pool for reuse.

        Args:
            obj: Object to return to pool
        """
        try:
            self._pool.put((obj, time.time()), timeout=0.1)
            with self._lock:
                self._stats['released'] += 1
        except Full:
            # Pool full, destroy object
            if hasattr(obj, 'close'):
                try:
                    obj.close()
                except Exception:
                    pass  # Ignore cleanup errors
            with self._lock:
                self._stats['destroyed'] += 1

    def _cleanup_worker(self) -> None:
        """Background worker to clean up stale objects."""
        while True:
            time.sleep(self._cleanup_interval)
            self._cleanup_stale_objects()

    def _cleanup_stale_objects(self) -> None:
        """Remove objects that have been idle longer than timeout."""
        current_time = time.time()
        temp_queue = Queue(maxsize=self.max_size)

        while not self._pool.empty():
            try:
                obj, timestamp = self._pool.get_nowait()
                if current_time - timestamp < self.timeout:
                    temp_queue.put((obj, timestamp))
                else:
                    # Stale object, destroy it
                    if hasattr(obj, 'close'):
                        try:
                            obj.close()
                        except Exception:
                            pass
                    with self._lock:
                        self._stats['destroyed'] += 1
            except Empty:
                break

        # Put back non-stale objects
        while not temp_queue.empty():
            try:
                self._pool.put(temp_queue.get_nowait(), timeout=0.1)
            except Full:
                break

    def get_stats(self) -> dict:
        """Get pool usage statistics."""
        with self._lock:
            return self._stats.copy()

    @contextmanager
    def get(self, timeout: Optional[float] = None):
        """Context manager for automatic object acquisition and release."""
        obj = self.acquire(timeout)
        try:
            yield obj
        finally:
            self.release(obj)


# Specialized pools for framework components

class CaseObjectPool(ObjectPool[dict]):
    """Object pool for fuzzing test cases to reduce memory allocation in data generation."""

    def __init__(self, max_size: int = 200, timeout: float = 600.0):
        """方法说明：执行   init   相关逻辑。"""
        super().__init__(
            factory=lambda: {},
            max_size=max_size,
            timeout=timeout,
            cleanup_interval=60.0
        )


class ConnectionObjectPool(ObjectPool[Any]):
    """Object pool for protocol connection objects to avoid frequent connect/disconnect."""

    def __init__(self, factory: Callable[[], Any], max_size: int = 50, timeout: float = 300.0):
        """方法说明：执行   init   相关逻辑。"""
        super().__init__(
            factory=factory,
            max_size=max_size,
            timeout=timeout,
            cleanup_interval=60.0
        )


class LogObjectPool(ObjectPool[dict]):
    """Object pool for log entries to reduce memory pressure in monitoring feedback."""

    def __init__(self, max_size: int = 500, timeout: float = 180.0):
        """方法说明：执行   init   相关逻辑。"""
        super().__init__(
            factory=lambda: {},
            max_size=max_size,
            timeout=timeout,
            cleanup_interval=60.0
        )