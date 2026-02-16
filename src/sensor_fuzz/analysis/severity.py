"""严重度分析模块：按规则将缺陷映射为严重等级。"""

from __future__ import annotations

from typing import Dict

LEVELS = {
    "minor": 1,
    "medium": 2,
    "severe": 3,
    "critical": 4,
}


def classify(defect: Dict) -> str:
    """根据缺陷特征判定严重度等级。"""
    category = defect.get("category", "")
    if category == "safety" or defect.get("deadlock"):
        return "critical"
    if defect.get("crash"):
        return "severe"
    if defect.get("resource_leak"):
        return "medium"
    return "minor"
