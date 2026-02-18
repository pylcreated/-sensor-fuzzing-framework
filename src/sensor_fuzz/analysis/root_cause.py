"""根因分析模块：结合事件信息给出根因候选。"""

from __future__ import annotations

from typing import Dict, Iterable, List, Set


def _normalize_ablation(ablation: Iterable[str] | None) -> Set[str]:
    if ablation is None:
        return set()
    return {str(item).strip().lower() for item in ablation if str(item).strip()}


def _event_score(event: Dict, disabled: Set[str]) -> float:
    score = 0.0
    severity = str(event.get("severity", "")).lower()
    if "severity" not in disabled:
        if severity == "critical":
            score += 1.0
        elif severity == "high":
            score += 0.8
        elif severity == "medium":
            score += 0.4

    if "keyword" not in disabled:
        desc = str(event.get("desc", "")).lower()
        for kw, weight in (
            ("deadlock", 0.6),
            ("overflow", 0.4),
            ("crash", 0.5),
            ("timeout", 0.3),
        ):
            if kw in desc:
                score += weight

    if "evidence_count" not in disabled:
        evidence_count = event.get("evidence_count", 0)
        if isinstance(evidence_count, (int, float)):
            score += min(float(evidence_count), 10.0) * 0.03
    return score


def locate_root_cause(
    events: List[Dict],
    *,
    strategy: str = "first_severe",
    ablation: Iterable[str] | None = None,
) -> Dict:
    """基于启发式规则定位根因事件。"""
    if strategy == "first_severe":
        for ev in events:
            if ev.get("severity") in {"critical", "high"}:
                return {"root_cause": ev.get("desc", "unknown"), "evidence": ev}
        return {"root_cause": "unknown", "evidence": events[:1] if events else []}

    if strategy == "score":
        disabled = _normalize_ablation(ablation)
        best_event: Dict | None = None
        best_score = float("-inf")
        for event in events:
            score = _event_score(event, disabled)
            if score > best_score:
                best_score = score
                best_event = event

        if not best_event:
            return {"root_cause": "unknown", "evidence": []}

        root = best_event.get("desc") or "unknown"
        return {"root_cause": root, "evidence": best_event}

    raise ValueError(f"Unsupported strategy: {strategy}")
