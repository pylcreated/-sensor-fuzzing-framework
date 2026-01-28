"""Adaptive mutation strategy skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import random


@dataclass
class MutatorFeedback:
    category: str
    detected: bool


class AdaptiveMutator:
    """Adjust mutation weights based on SUT feedback."""

    def __init__(self) -> None:
        self.weights: Dict[str, float] = {
            "boundary": 1.0,
            "protocol_error": 1.0,
            "signal_distortion": 1.0,
            "anomaly": 1.0,
        }

    def update(self, feedback: List[MutatorFeedback]) -> None:
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
