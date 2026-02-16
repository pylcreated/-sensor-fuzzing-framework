"""Adaptive mutation strategy skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import random


@dataclass
class MutatorFeedback:
    """类说明：封装 MutatorFeedback 的相关行为。"""
    category: str
    detected: bool


class AdaptiveMutator:
    """Adjust mutation weights based on SUT feedback."""

    def __init__(self) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self.weights: Dict[str, float] = {
            "boundary": 1.0,
            "protocol_error": 1.0,
            "signal_distortion": 1.0,
            "anomaly": 1.0,
        }

    def update(self, feedback: List[MutatorFeedback]) -> None:
        """方法说明：执行 update 相关逻辑。"""
        for fb in feedback:
            if fb.detected:
                self.weights[fb.category] = min(
                    self.weights.get(fb.category, 1.0) * 1.1, 5.0
                )
            else:
                self.weights[fb.category] = max(
                    self.weights.get(fb.category, 1.0) * 0.9, 0.1
                )

    def choose(self) -> str:
        # Weighted random choice to avoid mode collapse
        """方法说明：执行 choose 相关逻辑。"""
        total = sum(self.weights.values())
        if total == 0:
            return "boundary"
        r = random.uniform(0, total)
        upto = 0.0
        for name, weight in self.weights.items():
            upto += weight
            if upto >= r:
                return name
        return "boundary"
