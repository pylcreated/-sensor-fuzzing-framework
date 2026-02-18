"""Tests for automated thesis report builder."""

from __future__ import annotations

import json
from pathlib import Path

from sensor_fuzz.automation.report_builder import (
    build_markdown_report,
    score_from_payload,
    write_markdown_report,
    write_markdown_report_from_json,
)


def _sample_payload() -> dict:
    return {
        "generated_at": "2026-02-18T00:00:00+00:00",
        "experiments": [
            {
                "name": "envsim_stability",
                "metrics": {
                    "sample_count": 3,
                    "timeline_seconds": 4.5,
                    "temperature_span": 1.2,
                },
                "notes": "ok",
            },
            {
                "name": "distributed_reliability",
                "metrics": {
                    "tasks_total": 8,
                    "tasks_done": 8,
                    "tasks_failed": 0,
                    "tasks_recovered": 2,
                    "recovery_rate": 1.0,
                },
                "notes": "ok",
            },
            {
                "name": "analysis_ablation",
                "metrics": {
                    "sample_count": 3,
                    "critical_count": 1,
                    "mean_weighted_score": 0.72,
                    "ablation_score_delta": 0.31,
                    "root_cause": "critical deadlock",
                },
                "notes": "ok",
            },
        ],
    }


def test_score_from_payload_range() -> None:
    score = score_from_payload(_sample_payload())
    assert 0.0 <= score.reliability <= 1.0
    assert 0.0 <= score.stability <= 1.0
    assert 0.0 <= score.analysis_quality <= 1.0
    assert 0.0 <= score.overall <= 1.0


def test_build_markdown_report_contains_sections() -> None:
    markdown = build_markdown_report(_sample_payload())
    assert "# 研究实验自动化报告" in markdown
    assert "## 分项评分" in markdown
    assert "## 实验明细" in markdown


def test_write_markdown_report(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    result = write_markdown_report(_sample_payload(), output)
    assert result.exists()
    assert "综合评分" in result.read_text(encoding="utf-8")


def test_write_markdown_report_from_json(tmp_path: Path) -> None:
    input_json = tmp_path / "latest.json"
    output_md = tmp_path / "latest.md"
    input_json.write_text(json.dumps(_sample_payload(), ensure_ascii=False), encoding="utf-8")

    result = write_markdown_report_from_json(input_json, output_md)
    assert result.exists()
    text = result.read_text(encoding="utf-8")
    assert "envsim_stability" in text
    assert "distributed_reliability" in text
