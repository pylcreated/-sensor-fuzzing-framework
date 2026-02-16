"""Distributed scheduler client (placeholder)."""

from __future__ import annotations

import redis


class SchedulerClient:
    """类说明：封装 SchedulerClient 的相关行为。"""
    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._client = redis.from_url(redis_url)

    def enqueue_task(self, task: dict) -> None:
        """方法说明：执行 enqueue task 相关逻辑。"""
        self._client.lpush("sensor_fuzz:tasks", task)
