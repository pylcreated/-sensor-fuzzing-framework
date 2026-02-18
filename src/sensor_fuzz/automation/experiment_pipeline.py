"""Research experiment pipeline for paper-ready reproducible metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sensor_fuzz.analysis import classify, locate_root_cause, score_defect
from sensor_fuzz.distributed import SchedulerClient
from sensor_fuzz.envsim import SimulatedEnvironment


@dataclass
class ExperimentResult:
    """Unified experiment result object."""

    name: str
    metrics: Dict[str, Any]
    notes: str

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "metrics": self.metrics, "notes": self.notes}


def run_envsim_experiment(seed: int = 2026) -> ExperimentResult:
    """Run a deterministic env simulation scenario and collect stability metrics."""
    sim = SimulatedEnvironment(seed=seed)
    timeline = sim.run_scenario(
        [
            {"temperature_c": 24.0, "light_lux": 240.0, "dt_s": 1.0},
            {
                "temperature_c": 26.5,
                "light_lux": 300.0,
                "vibration_freq_hz": 30.0,
                "vibration_amplitude": 0.4,
                "dt_s": 1.5,
            },
            {
                "temperature_c": 27.0,
                "light_lux": 340.0,
                "vibration_freq_hz": 55.0,
                "vibration_amplitude": 0.9,
                "dt_s": 2.0,
            },
        ],
        temperature_noise_std=0.15,
        light_noise_std=1.5,
        vibration_noise_std=0.02,
    )

    temps = [float(sample["temperature_c"]) for sample in timeline]
    temp_delta = max(temps) - min(temps) if temps else 0.0
    metrics = {
        "sample_count": len(timeline),
        "timeline_seconds": float(timeline[-1]["timestamp_s"] if timeline else 0.0),
        "temperature_span": round(temp_delta, 4),
        "max_vibration_amplitude": round(
            max(float(sample["vibration_amplitude"]) for sample in timeline) if timeline else 0.0,
            4,
        ),
    }
    return ExperimentResult(
        name="envsim_stability",
        metrics=metrics,
        notes="Scenario replay with controlled Gaussian noise.",
    )


def run_distributed_experiment() -> ExperimentResult:
    """Run retry and stale-task recovery checks for scheduler reliability."""
    client = SchedulerClient(redis_url="redis://invalid:6379/0")
    total = 8
    recovered = 0
    done = 0
    failed = 0

    task_ids: List[str] = []
    for i in range(total):
        task_ids.append(
            client.enqueue_task(
                {"case": f"dist-{i}"},
                priority=100 - i,
                max_retries=1,
                timeout_s=1,
                idempotency_key=f"dist-key-{i}",
            )
        )

    for index, task_id in enumerate(task_ids):
        task = client.dequeue_task(worker_id=f"worker-{index}")
        if not task:
            continue

        if index % 4 == 0:
            client.mark_failed(task_id, error="transient", retryable=True)
        elif index % 4 == 1:
            # simulate stale without heartbeat
            pass
        else:
            client.mark_done(task_id, result={"ok": True})

    recovered += client.requeue_stale_tasks(
        now=datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=5)
    )

    for task_id in task_ids:
        status = client.get_task_status(task_id)
        if not status:
            continue
        current = status.get("status")
        if current == "queued":
            next_task = client.dequeue_task(worker_id="recovery")
            if next_task and next_task.get("task_id") == task_id:
                client.mark_done(task_id, result={"recovered": True})
                done += 1
            else:
                failed += 1
        elif current == "done":
            done += 1
        else:
            failed += 1

    metrics = {
        "tasks_total": total,
        "tasks_done": done,
        "tasks_failed": failed,
        "tasks_recovered": recovered,
        "recovery_rate": round((done / total) if total else 0.0, 4),
    }
    return ExperimentResult(
        name="distributed_reliability",
        metrics=metrics,
        notes="Retry + stale requeue + idempotency path validation.",
    )


def run_analysis_experiment(events: Optional[Iterable[Dict[str, Any]]] = None) -> ExperimentResult:
    """Run weighted severity and root-cause scoring with ablation."""
    records = list(events) if events is not None else [
        {"desc": "normal telemetry", "severity": "low", "crash": False},
        {
            "desc": "critical deadlock in i2c driver",
            "severity": "critical",
            "deadlock": True,
            "crash": True,
            "category": "safety",
            "exploitability": 0.8,
            "evidence_count": 5,
        },
        {"desc": "sporadic timeout", "severity": "medium", "resource_leak": True},
    ]

    weighted_levels = [classify(record, strategy="weighted") for record in records]
    weighted_scores = [score_defect(record) for record in records]
    ablated_scores = [score_defect(record, ablation=["deadlock", "safety"]) for record in records]
    root = locate_root_cause(records, strategy="score")

    delta = sum(weighted_scores) - sum(ablated_scores)
    metrics = {
        "sample_count": len(records),
        "critical_count": sum(1 for lv in weighted_levels if lv == "critical"),
        "mean_weighted_score": round(sum(weighted_scores) / max(1, len(weighted_scores)), 4),
        "ablation_score_delta": round(delta, 4),
        "root_cause": root.get("root_cause", "unknown"),
    }
    return ExperimentResult(
        name="analysis_ablation",
        metrics=metrics,
        notes="Weighted severity with feature ablation and score-based root-cause.",
    )


def run_research_pipeline(output_path: str | Path = "reports/experiments/latest.json") -> Dict[str, Any]:
    """Execute all research experiments and write a machine-readable report."""
    results = [
        run_envsim_experiment(),
        run_distributed_experiment(),
        run_analysis_experiment(),
    ]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiments": [result.as_dict() for result in results],
    }

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
