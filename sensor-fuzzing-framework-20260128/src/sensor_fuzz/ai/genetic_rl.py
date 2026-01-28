"""Genetic + reinforcement learning placeholders for test generation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List


@dataclass
class TestCase:
    payload: dict
    fitness: float = 0.0


def genetic_generate(
    seed_cases: List[TestCase], population: int = 10, generations: int = 3
) -> List[TestCase]:
    pop = seed_cases[:]
    for _ in range(generations):
        pop = sorted(pop, key=lambda c: c.fitness, reverse=True)
        parents = pop[: max(1, len(pop) // 2)]
        children: List[TestCase] = []
        while len(children) < population:
            a, b = random.choice(parents), random.choice(parents)
            child_payload = {**a.payload}
            if random.random() < 0.5:
                child_payload.update(b.payload)
            child = TestCase(payload=child_payload, fitness=0.0)
            children.append(child)
        pop = children
    return pop


def rl_score(case: TestCase, reward: float) -> None:
    case.fitness = 0.8 * case.fitness + 0.2 * reward
