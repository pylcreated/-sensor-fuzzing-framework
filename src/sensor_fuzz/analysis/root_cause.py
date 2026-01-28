"""Root cause analysis placeholder combining stack traces, protocol data, env."""

from __future__ import annotations

from typing import Dict, List


def locate_root_cause(events: List[Dict]) -> Dict:
    # Placeholder heuristic: pick first severe event
    for ev in events:
        if ev.get("severity") in {"critical", "high"}:
            return {"root_cause": ev.get("desc", "unknown"), "evidence": ev}
    return {"root_cause": "unknown", "evidence": events[:1] if events else []}
