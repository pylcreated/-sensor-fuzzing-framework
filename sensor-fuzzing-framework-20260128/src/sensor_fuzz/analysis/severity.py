"""Defect severity mapping per IEC61508 style levels."""

from __future__ import annotations

from typing import Dict

LEVELS = {
    "minor": 1,
    "medium": 2,
    "severe": 3,
    "critical": 4,
}


def classify(defect: Dict) -> str:
    category = defect.get("category", "")
    if category == "safety" or defect.get("deadlock"):
        return "critical"
    if defect.get("crash"):
        return "severe"
    if defect.get("resource_leak"):
        return "medium"
    return "minor"
