"""Tests for research experiment pipeline."""

from __future__ import annotations

from pathlib import Path

from sensor_fuzz.automation.experiment_pipeline import (
    run_analysis_experiment,
    run_distributed_experiment,
    run_envsim_experiment,
    run_research_pipeline,
)


def test_envsim_experiment_outputs_metrics() -> None:
    result = run_envsim_experiment(seed=100)
    assert result.name == "envsim_stability"
    assert result.metrics["sample_count"] >= 1
    assert result.metrics["timeline_seconds"] > 0


def test_distributed_experiment_outputs_recovery_metrics() -> None:
    result = run_distributed_experiment()
    assert result.name == "distributed_reliability"
    assert result.metrics["tasks_total"] == 8
    assert 0.0 <= result.metrics["recovery_rate"] <= 1.0


def test_analysis_experiment_outputs_ablation_metrics() -> None:
    result = run_analysis_experiment()
    assert result.name == "analysis_ablation"
    assert result.metrics["sample_count"] >= 1
    assert "root_cause" in result.metrics


def test_research_pipeline_writes_report(tmp_path: Path) -> None:
    target = tmp_path / "research_latest.json"
    payload = run_research_pipeline(target)

    assert target.exists()
    assert "generated_at" in payload
    assert len(payload["experiments"]) == 3
