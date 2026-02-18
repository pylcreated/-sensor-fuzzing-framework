"""严重度分析模块：按规则将缺陷映射为严重等级。"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Set

LEVELS = {
    "minor": 1,
    "medium": 2,
    "severe": 3,
    "critical": 4,
}


DEFAULT_WEIGHTS = {
    "deadlock": 0.45,
    "crash": 0.35,
    "safety": 0.40,
    "resource_leak": 0.20,
    "exploitability": 0.25,
    "reproducibility": 0.15,
}


def _normalize_ablation(ablation: Optional[Iterable[str]]) -> Set[str]:
    if ablation is None:
        return set()
    return {str(item).strip().lower() for item in ablation if str(item).strip()}


def score_defect(
    defect: Dict,
    *,
    weights: Optional[Dict[str, float]] = None,
    ablation: Optional[Iterable[str]] = None,
) -> float:
    """Compute weighted severity score in [0, 1]-ish range."""
    merged = dict(DEFAULT_WEIGHTS)
    if weights:
        merged.update(weights)

    disabled = _normalize_ablation(ablation)
    score = 0.0
    for feature, weight in merged.items():
        if feature in disabled:
            continue

        value = defect.get(feature)
        if isinstance(value, bool):
            score += weight if value else 0.0
        elif isinstance(value, (int, float)):
            bounded = min(max(float(value), 0.0), 1.0)
            score += bounded * weight
        elif feature == "safety" and defect.get("category") == "safety":
            score += weight
    return score


def _score_to_level(score: float) -> str:
    if score >= 0.75:
        return "critical"
    if score >= 0.45:
        return "severe"
    if score >= 0.20:
        return "medium"
    return "minor"


def classify(
    defect: Dict,
    *,
    strategy: str = "rule",
    weights: Optional[Dict[str, float]] = None,
    ablation: Optional[Iterable[str]] = None,
) -> str:
    """根据缺陷特征判定严重度等级。"""
    if strategy == "weighted":
        return _score_to_level(score_defect(defect, weights=weights, ablation=ablation))

    category = defect.get("category", "")
    if category == "safety" or defect.get("deadlock"):
        return "critical"
    if defect.get("crash"):
        return "severe"
    if defect.get("resource_leak"):
        return "medium"
    return "minor"
