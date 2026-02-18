"""Distributed scheduler client with retry and task-state support."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import redis
except Exception:  # pragma: no cover - optional dependency path
    redis = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass
class TaskRecord:
    """Internal task representation used for queue and status tracking."""

    task_id: str
    payload: Dict[str, Any]
    status: str
    priority: int
    retries: int
    max_retries: int
    timeout_s: int
    enqueued_at: str
    updated_at: str
    worker_id: Optional[str]
    idempotency_key: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "payload": self.payload,
            "status": self.status,
            "priority": self.priority,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "timeout_s": self.timeout_s,
            "enqueued_at": self.enqueued_at,
            "updated_at": self.updated_at,
            "worker_id": self.worker_id,
            "idempotency_key": self.idempotency_key,
            "result": self.result,
            "error": self.error,
        }


class SchedulerClient:
    """Task queue client with Redis and memory fallback backends."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._queue_name = "sensor_fuzz:tasks"
        self._status_name = "sensor_fuzz:task_status"
        self._index_name = "sensor_fuzz:idempotency"

        self._memory_queue: List[str] = []
        self._memory_status: Dict[str, Dict[str, Any]] = {}
        self._memory_idempotency: Dict[str, str] = {}

        self._redis = None
        if redis is not None:
            try:
                candidate = redis.from_url(redis_url)
                candidate.ping()
                self._redis = candidate
            except Exception:
                self._redis = None

    def _save_status(self, task: TaskRecord) -> None:
        body = task.as_dict()
        if self._redis is not None:
            self._redis.hset(self._status_name, task.task_id, json.dumps(body))
            if task.idempotency_key:
                self._redis.hset(self._index_name, task.idempotency_key, task.task_id)
            return
        self._memory_status[task.task_id] = body
        if task.idempotency_key:
            self._memory_idempotency[task.idempotency_key] = task.task_id

    def _load_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        if self._redis is not None:
            raw = self._redis.hget(self._status_name, task_id)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        return self._memory_status.get(task_id)

    def _push_queue(self, serialized: str, priority: int) -> None:
        if self._redis is not None:
            self._redis.zadd(self._queue_name, {serialized: priority})
            return
        self._memory_queue.append(serialized)
        self._memory_queue.sort(
            key=lambda row: int(json.loads(row).get("priority", 0)), reverse=True
        )

    def _pop_queue(self) -> Optional[Dict[str, Any]]:
        if self._redis is not None:
            rows = self._redis.zpopmax(self._queue_name, count=1)
            if not rows:
                return None
            payload = rows[0][0]
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            return json.loads(payload)
        if not self._memory_queue:
            return None
        return json.loads(self._memory_queue.pop(0))

    def enqueue_task(
        self,
        task: Dict[str, Any],
        *,
        priority: int = 100,
        max_retries: int = 3,
        timeout_s: int = 60,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Enqueue a task and return task id."""
        if idempotency_key:
            existing = self.get_task_id_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        task_id = str(uuid.uuid4())
        now = _now_iso()
        record = TaskRecord(
            task_id=task_id,
            payload=dict(task),
            status="queued",
            priority=int(priority),
            retries=0,
            max_retries=max(int(max_retries), 0),
            timeout_s=max(int(timeout_s), 1),
            enqueued_at=now,
            updated_at=now,
            worker_id=None,
            idempotency_key=idempotency_key,
            result=None,
            error=None,
        )
        serialized = json.dumps(record.as_dict())
        self._push_queue(serialized, record.priority)
        self._save_status(record)
        return task_id

    def dequeue_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Pull one queued task and mark it as in-progress."""
        candidate = self._pop_queue()
        if not candidate:
            return None
        candidate["status"] = "in_progress"
        candidate["worker_id"] = worker_id
        candidate["updated_at"] = _now_iso()
        self._save_status(TaskRecord(**candidate))
        return candidate

    def mark_done(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark task as done with optional result payload."""
        state = self._load_status(task_id)
        if not state:
            return
        state["status"] = "done"
        state["updated_at"] = _now_iso()
        state["result"] = result or {}
        self._save_status(TaskRecord(**state))

    def mark_failed(self, task_id: str, error: str, retryable: bool = True) -> None:
        """Mark task failed and optionally requeue when retries are available."""
        state = self._load_status(task_id)
        if not state:
            return

        state["retries"] = int(state.get("retries", 0)) + 1
        state["error"] = error
        state["updated_at"] = _now_iso()

        can_retry = retryable and state["retries"] <= int(state.get("max_retries", 0))
        if can_retry:
            state["status"] = "queued"
            state["worker_id"] = None
            serialized = json.dumps(state)
            self._push_queue(serialized, int(state.get("priority", 100)))
        else:
            state["status"] = "failed"
        self._save_status(TaskRecord(**state))

    def heartbeat(self, task_id: str, worker_id: str) -> bool:
        """Refresh updated time for an in-progress task."""
        state = self._load_status(task_id)
        if not state:
            return False
        if state.get("status") != "in_progress":
            return False
        if state.get("worker_id") != worker_id:
            return False
        state["updated_at"] = _now_iso()
        self._save_status(TaskRecord(**state))
        return True

    def requeue_stale_tasks(self, now: Optional[datetime] = None) -> int:
        """Move timed-out in-progress tasks back to queue and return count."""
        ref = now or datetime.now(timezone.utc)
        rows: List[Dict[str, Any]]
        if self._redis is not None:
            rows = []
            for raw in self._redis.hvals(self._status_name):
                text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                rows.append(json.loads(text))
        else:
            rows = list(self._memory_status.values())

        moved = 0
        for state in rows:
            if state.get("status") != "in_progress":
                continue
            updated_at = _iso_to_dt(state["updated_at"])
            timeout = timedelta(seconds=int(state.get("timeout_s", 60)))
            if updated_at + timeout <= ref:
                state["status"] = "queued"
                state["worker_id"] = None
                state["updated_at"] = _now_iso()
                self._push_queue(json.dumps(state), int(state.get("priority", 100)))
                self._save_status(TaskRecord(**state))
                moved += 1
        return moved

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task state by id."""
        return self._load_status(task_id)

    def get_task_id_by_idempotency_key(self, idempotency_key: str) -> Optional[str]:
        """Get task id from idempotency key."""
        if self._redis is not None:
            raw = self._redis.hget(self._index_name, idempotency_key)
            if raw is None:
                return None
            return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        return self._memory_idempotency.get(idempotency_key)
