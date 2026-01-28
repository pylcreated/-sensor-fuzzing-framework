"""Distributed scheduler client (placeholder)."""

from __future__ import annotations

import redis


class SchedulerClient:
    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._client = redis.from_url(redis_url)

    def enqueue_task(self, task: dict) -> None:
        self._client.lpush("sensor_fuzz:tasks", task)
