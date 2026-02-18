"""Build paper-ready experiment reports from pipeline outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ExperimentScore:
    """Scored summary for thesis reporting."""

    reliability: float
    stability: float
    analysis_quality: float

    @property
    def overall(self) -> float:
        return round(
            self.reliability * 0.4 + self.stability * 0.3 + self.analysis_quality * 0.3,
            4,
        )

    @property
    def risk_level(self) -> str:
        if self.overall >= 0.85:
            return "low"
        if self.overall >= 0.65:
            return "medium"
        return "high"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_from_payload(payload: Dict[str, Any]) -> ExperimentScore:
    """Convert experiment payload metrics to normalized scores."""
    metrics_map = {
        item.get("name"): item.get("metrics", {})
        for item in payload.get("experiments", [])
        if isinstance(item, dict)
    }

    dist = metrics_map.get("distributed_reliability", {})
    env = metrics_map.get("envsim_stability", {})
    ana = metrics_map.get("analysis_ablation", {})

    reliability = _clamp01(float(dist.get("recovery_rate", 0.0)))
    temp_span = float(env.get("temperature_span", 0.0))
    stability = _clamp01(1.0 / (1.0 + temp_span))

    delta = float(ana.get("ablation_score_delta", 0.0))
    mean_score = float(ana.get("mean_weighted_score", 0.0))
    analysis_quality = _clamp01(0.6 * _clamp01(mean_score) + 0.4 * _clamp01(delta))

    return ExperimentScore(
        reliability=round(reliability, 4),
        stability=round(stability, 4),
        analysis_quality=round(analysis_quality, 4),
    )


def _render_table(experiments: List[Dict[str, Any]]) -> str:
    rows = [
        "| 实验名称 | 关键指标 |",
        "|---|---|",
    ]
    for experiment in experiments:
        name = str(experiment.get("name", "unknown"))
        metrics = experiment.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        compact = "; ".join(f"{k}={v}" for k, v in metrics.items())
        rows.append(f"| {name} | {compact} |")
    return "\n".join(rows)


def build_markdown_report(payload: Dict[str, Any]) -> str:
    """Build markdown report text for thesis appendix."""
    score = score_from_payload(payload)
    generated_at = payload.get("generated_at", datetime.now().isoformat())
    experiments = payload.get("experiments", [])
    if not isinstance(experiments, list):
        experiments = []

    lines = [
        "# 研究实验自动化报告",
        "",
        f"- 生成时间：{generated_at}",
        f"- 综合评分：{score.overall}",
        f"- 风险等级：{score.risk_level}",
        "",
        "## 分项评分",
        "",
        f"- 可靠性（调度恢复）：{score.reliability}",
        f"- 稳定性（环境波动）：{score.stability}",
        f"- 分析质量（消融与加权）：{score.analysis_quality}",
        "",
        "## 实验明细",
        "",
        _render_table(experiments),
        "",
        "## 结论与建议",
        "",
        "- 当前流水线已形成环境仿真、分布式可靠性、分析消融三条证据链。",
        "- 当综合评分低于 0.65 时，建议优先提升调度恢复率和异常分析特征质量。",
        "- 建议将本报告与原始 JSON 一同作为论文附录，保证可复现性。",
        "",
    ]
    return "\n".join(lines)


def write_markdown_report(
    payload: Dict[str, Any],
    output_path: str | Path = "reports/experiments/latest.md",
) -> Path:
    """Write markdown report file and return path."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_markdown_report(payload), encoding="utf-8")
    return target


def write_markdown_report_from_json(
    input_json: str | Path = "reports/experiments/latest.json",
    output_md: str | Path = "reports/experiments/latest.md",
) -> Path:
    """Read pipeline JSON and write markdown report."""
    payload = json.loads(Path(input_json).read_text(encoding="utf-8"))
    return write_markdown_report(payload, output_md)
