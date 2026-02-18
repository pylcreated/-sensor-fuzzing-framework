"""Distributed scheduler client tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sensor_fuzz.distributed.scheduler_client import SchedulerClient


def test_enqueue_with_idempotency_key_returns_same_task_id() -> None:
    client = SchedulerClient(redis_url="redis://invalid:6379/0")
    task_id_1 = client.enqueue_task({"case": "A"}, idempotency_key="case-A")
    task_id_2 = client.enqueue_task({"case": "A-updated"}, idempotency_key="case-A")

    assert task_id_1 == task_id_2


def test_retry_flow_then_fail() -> None:
    client = SchedulerClient(redis_url="redis://invalid:6379/0")
    task_id = client.enqueue_task({"case": "retry"}, max_retries=1)

    assigned = client.dequeue_task(worker_id="w1")
    assert assigned is not None
    assert assigned["task_id"] == task_id
    assert assigned["status"] == "in_progress"

    client.mark_failed(task_id, error="temp", retryable=True)
    state = client.get_task_status(task_id)
    assert state is not None
    assert state["status"] == "queued"
    assert state["retries"] == 1

    assigned_again = client.dequeue_task(worker_id="w2")
    assert assigned_again is not None
    client.mark_failed(task_id, error="perm", retryable=True)

    state2 = client.get_task_status(task_id)
    assert state2 is not None
    assert state2["status"] == "failed"
    assert state2["retries"] == 2


def test_mark_done_with_result_payload() -> None:
    client = SchedulerClient(redis_url="redis://invalid:6379/0")
    task_id = client.enqueue_task({"case": "done"})
    _ = client.dequeue_task(worker_id="worker-done")

    client.mark_done(task_id, result={"passed": True, "latency_ms": 12.3})
    status = client.get_task_status(task_id)
    assert status is not None
    assert status["status"] == "done"
    assert status["result"]["passed"] is True


def test_requeue_stale_task() -> None:
    client = SchedulerClient(redis_url="redis://invalid:6379/0")
    task_id = client.enqueue_task({"case": "stale"}, timeout_s=1)
    _ = client.dequeue_task(worker_id="worker-stale")

    moved = client.requeue_stale_tasks(now=datetime.now(timezone.utc) + timedelta(seconds=5))
    assert moved == 1

    status = client.get_task_status(task_id)
    assert status is not None
    assert status["status"] == "queued"
