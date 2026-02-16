"""根因分析模块：结合事件信息给出根因候选。"""

from __future__ import annotations

from typing import Dict, List


def locate_root_cause(events: List[Dict]) -> Dict:
    # Placeholder heuristic: pick first severe event
    """基于启发式规则定位根因事件。"""
    for ev in events:
        if ev.get("severity") in {"critical", "high"}:
            return {"root_cause": ev.get("desc", "unknown"), "evidence": ev}
    return {"root_cause": "unknown", "evidence": events[:1] if events else []}
