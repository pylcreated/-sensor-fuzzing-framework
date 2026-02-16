"""Genetic algorithm and reinforcement learning for automated test case generation."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from concurrent.futures import ThreadPoolExecutor

from sensor_fuzz.data_gen.boundary import generate_boundary_cases
from sensor_fuzz.data_gen.anomaly import generate_anomaly_values
from sensor_fuzz.data_gen.protocol_errors import generate_protocol_errors
from sensor_fuzz.data_gen.signal_distortion import distort_signal
from sensor_fuzz.ai.lstm import AnomalyDetector


@dataclass
class TestCase:
    """Represents a test case with genetic properties."""
    sensor_config: Dict[str, Any]
    protocol: str
    mutations: List[Dict[str, Any]] = field(default_factory=list)
    fitness_score: float = 0.0
    coverage: float = 0.0
    anomaly_probability: float = 0.0
    generation: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "sensor_config": self.sensor_config,
            "protocol": self.protocol,
            "mutations": self.mutations,
            "fitness_score": self.fitness_score,
            "coverage": self.coverage,
            "anomaly_probability": self.anomaly_probability,
            "generation": self.generation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TestCase:
        """Create from dictionary."""
        return cls(
            sensor_config=data["sensor_config"],
            protocol=data["protocol"],
            mutations=data.get("mutations", []),
            fitness_score=data.get("fitness_score", 0.0),
            coverage=data.get("coverage", 0.0),
            anomaly_probability=data.get("anomaly_probability", 0.0),
            generation=data.get("generation", 0),
        )


class GeneticGenerator:
    """Genetic algorithm for test case generation."""

    def __init__(
        self,
        population_size: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism_rate: float = 0.1,
        max_generations: int = 50,
    ):
        """方法说明：执行   init   相关逻辑。"""
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_rate = elitism_rate
        self.max_generations = max_generations
        self.population: List[TestCase] = []
        self.generation = 0
        self.anomaly_detector = AnomalyDetector(contamination=0.1)

    def initialize_population(self, sensor_configs: List[Dict], protocols: List[str]) -> None:
        """Initialize the population with random test cases."""
        self.population = []
        for _ in range(self.population_size):
            sensor_config = random.choice(sensor_configs)
            protocol = random.choice(protocols)
            test_case = self._generate_random_test_case(sensor_config, protocol)
            self.population.append(test_case)

    def _generate_random_test_case(self, sensor_config: Dict, protocol: str) -> TestCase:
        """Generate a random test case."""
        mutations = []

        # Add boundary cases
        boundary_cases = generate_boundary_cases(sensor_config)
        if boundary_cases:
            mutations.extend(random.sample(boundary_cases, min(2, len(boundary_cases))))

        # Add anomaly values
        anomaly_cases = generate_anomaly_values(sensor_config)
        if anomaly_cases:
            mutations.extend(random.sample(anomaly_cases, min(2, len(anomaly_cases))))

        # Add protocol errors
        protocol_errors = generate_protocol_errors(protocol)
        if protocol_errors:
            mutations.extend(random.sample(protocol_errors, min(2, len(protocol_errors))))

        # Add signal distortion
        distortion_cases = distort_signal(sensor_config)
        if distortion_cases:
            mutations.extend(random.sample(distortion_cases, min(1, len(distortion_cases))))

        return TestCase(
            sensor_config=sensor_config,
            protocol=protocol,
            mutations=mutations,
            generation=self.generation,
        )

    def evaluate_population(self, execution_results: List[Dict]) -> None:
        """Evaluate fitness of all test cases in population."""
        for test_case in self.population:
            self._evaluate_fitness(test_case, execution_results)

    def _evaluate_fitness(self, test_case: TestCase, execution_results: List[Dict]) -> None:
        """Evaluate fitness of a single test case."""
        # Coverage score (0-1): based on code paths covered
        coverage_score = self._calculate_coverage(test_case, execution_results)

        # Anomaly detection score (0-1): based on anomaly probability
        anomaly_score = test_case.anomaly_probability

        # Execution success score (0-1): based on successful executions
        success_score = self._calculate_success_rate(test_case, execution_results)

        # Diversity score (0-1): based on mutation variety
        diversity_score = self._calculate_diversity(test_case)

        # Weighted fitness score
        test_case.fitness_score = (
            0.4 * coverage_score +
            0.3 * anomaly_score +
            0.2 * success_score +
            0.1 * diversity_score
        )
        test_case.coverage = coverage_score

    def _calculate_coverage(self, test_case: TestCase, execution_results: List[Dict]) -> float:
        """Calculate code coverage score."""
        # Simplified coverage calculation based on execution results
        relevant_results = [
            r for r in execution_results
            if r.get("protocol") == test_case.protocol and
            any(m in str(r.get("mutations", [])) for m in test_case.mutations)
        ]
        if not relevant_results:
            return 0.0

        # Coverage based on unique error types and code paths
        unique_errors = len(set(r.get("error_type", "") for r in relevant_results))
        unique_paths = len(set(r.get("code_path", "") for r in relevant_results))

        return min(1.0, (unique_errors + unique_paths) / 20.0)  # Normalize to 0-1

    def _calculate_success_rate(self, test_case: TestCase, execution_results: List[Dict]) -> float:
        """Calculate execution success rate."""
        relevant_results = [
            r for r in execution_results
            if r.get("protocol") == test_case.protocol
        ]
        if not relevant_results:
            return 0.5  # Neutral score for no data

        successful = sum(1 for r in relevant_results if r.get("success", False))
        return successful / len(relevant_results)

    def _calculate_diversity(self, test_case: TestCase) -> float:
        """Calculate mutation diversity score."""
        if not test_case.mutations:
            return 0.0

        mutation_types = set()
        for mutation in test_case.mutations:
            mutation_types.add(mutation.get("desc", "").split("-")[0])

        # Diversity based on unique mutation categories
        return min(1.0, len(mutation_types) / 5.0)  # Max 5 categories

    def select_parents(self) -> List[TestCase]:
        """Select parents using tournament selection."""
        parents = []
        tournament_size = 5

        for _ in range(self.population_size):
            tournament = random.sample(self.population, tournament_size)
            winner = max(tournament, key=lambda x: x.fitness_score)
            parents.append(winner)

        return parents

    def crossover(self, parent1: TestCase, parent2: TestCase) -> Tuple[TestCase, TestCase]:
        """Perform crossover between two parents."""
        if random.random() > self.crossover_rate:
            return parent1, parent2

        # Single point crossover for mutations
        if parent1.mutations and parent2.mutations:
            point = random.randint(1, min(len(parent1.mutations), len(parent2.mutations)))
            child1_mutations = parent1.mutations[:point] + parent2.mutations[point:]
            child2_mutations = parent2.mutations[:point] + parent1.mutations[point:]
        else:
            child1_mutations = parent1.mutations or parent2.mutations
            child2_mutations = parent2.mutations or parent1.mutations

        child1 = TestCase(
            sensor_config=random.choice([parent1.sensor_config, parent2.sensor_config]),
            protocol=random.choice([parent1.protocol, parent2.protocol]),
            mutations=child1_mutations,
            generation=self.generation + 1,
        )

        child2 = TestCase(
            sensor_config=random.choice([parent1.sensor_config, parent2.sensor_config]),
            protocol=random.choice([parent1.protocol, parent2.protocol]),
            mutations=child2_mutations,
            generation=self.generation + 1,
        )

        return child1, child2

    def mutate(self, test_case: TestCase, sensor_configs: List[Dict], protocols: List[str]) -> TestCase:
        """Mutate a test case."""
        if random.random() > self.mutation_rate:
            return test_case

        mutated = TestCase(
            sensor_config=test_case.sensor_config,
            protocol=test_case.protocol,
            mutations=test_case.mutations.copy(),
            generation=self.generation + 1,
        )

        # Random mutation operations
        mutation_type = random.choice(["add", "remove", "replace", "config_change"])

        if mutation_type == "add":
            # Add a random mutation
            all_possible = []
            all_possible.extend(generate_boundary_cases(mutated.sensor_config))
            all_possible.extend(generate_anomaly_values(mutated.sensor_config))
            all_possible.extend(generate_protocol_errors(mutated.protocol))
            all_possible.extend(distort_signal(mutated.sensor_config))

            if all_possible:
                new_mutation = random.choice(all_possible)
                if new_mutation not in mutated.mutations:
                    mutated.mutations.append(new_mutation)

        elif mutation_type == "remove" and mutated.mutations:
            # Remove a random mutation
            if mutated.mutations:
                removed = random.choice(mutated.mutations)
                mutated.mutations.remove(removed)

        elif mutation_type == "replace" and mutated.mutations:
            # Replace a mutation
            if mutated.mutations:
                idx = random.randint(0, len(mutated.mutations) - 1)
                all_possible = []
                all_possible.extend(generate_boundary_cases(mutated.sensor_config))
                all_possible.extend(generate_anomaly_values(mutated.sensor_config))
                all_possible.extend(generate_protocol_errors(mutated.protocol))
                all_possible.extend(distort_signal(mutated.sensor_config))

                if all_possible:
                    mutated.mutations[idx] = random.choice(all_possible)

        elif mutation_type == "config_change":
            # Change sensor config or protocol
            if random.random() < 0.5 and sensor_configs:
                mutated.sensor_config = random.choice(sensor_configs)
            elif protocols:
                mutated.protocol = random.choice(protocols)

        return mutated

    def evolve(self, sensor_configs: List[Dict], protocols: List[str], execution_results: List[Dict]) -> List[TestCase]:
        """Evolve the population for one generation."""
        # Evaluate current population
        self.evaluate_population(execution_results)

        # Sort by fitness
        self.population.sort(key=lambda x: x.fitness_score, reverse=True)

        # Elitism: keep best individuals
        elite_count = int(self.elitism_rate * self.population_size)
        new_population = self.population[:elite_count]

        # Generate offspring
        parents = self.select_parents()
        while len(new_population) < self.population_size:
            parent1, parent2 = random.sample(parents, 2)
            child1, child2 = self.crossover(parent1, parent2)

            child1 = self.mutate(child1, sensor_configs, protocols)
            child2 = self.mutate(child2, sensor_configs, protocols)

            new_population.extend([child1, child2])

        # Trim to population size
        self.population = new_population[:self.population_size]
        self.generation += 1

        return self.population

    async def evolve_async(
        self,
        sensor_configs: List[Dict],
        protocols: List[str],
        execution_results: List[Dict]
    ) -> List[TestCase]:
        """Asynchronous evolution using thread pool."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:
            result = await loop.run_in_executor(
                executor,
                lambda: self.evolve(sensor_configs, protocols, execution_results)
            )
        return result


class RLScorer:
    """Reinforcement learning-based test case scoring."""

    def __init__(self, learning_rate: float = 0.01, discount_factor: float = 0.9):
        """方法说明：执行   init   相关逻辑。"""
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.q_table: Dict[str, Dict[str, float]] = {}
        self.anomaly_detector = AnomalyDetector(contamination=0.1)

    def get_state(self, test_case: TestCase) -> str:
        """Convert test case to state representation."""
        protocol = test_case.protocol
        mutation_count = len(test_case.mutations)
        mutation_types = set()
        for m in test_case.mutations:
            mutation_types.add(m.get("desc", "").split("-")[0])

        state = f"{protocol}_{mutation_count}_{len(mutation_types)}"
        return state

    def get_actions(self, state: str) -> List[str]:
        """Get available actions for a state."""
        return ["keep", "mutate", "discard", "prioritize"]

    def choose_action(self, state: str, epsilon: float = 0.1) -> str:
        """Choose action using epsilon-greedy policy."""
        if random.random() < epsilon:
            return random.choice(self.get_actions(state))

        if state not in self.q_table:
            return random.choice(self.get_actions(state))

        # Choose best action
        actions = self.q_table[state]
        return max(actions, key=actions.get)

    def update_q_value(self, state: str, action: str, reward: float, next_state: str) -> None:
        """Update Q-value using Q-learning."""
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in self.get_actions(state)}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0.0 for a in self.get_actions(next_state)}

        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state].values())

        # Q-learning update
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )

        self.q_table[state][action] = new_q

    def calculate_reward(self, test_case: TestCase, execution_result: Dict) -> float:
        """Calculate reward based on execution result."""
        reward = 0.0

        # Reward for finding anomalies
        if execution_result.get("anomaly_detected", False):
            reward += 10.0

        # Reward for code coverage
        coverage = execution_result.get("coverage", 0.0)
        reward += coverage * 5.0

        # Reward for unique error types
        if execution_result.get("new_error_type", False):
            reward += 3.0

        # Penalty for failures (but not too harsh)
        if not execution_result.get("success", True):
            reward -= 1.0

        # Reward for anomaly probability
        anomaly_prob = test_case.anomaly_probability
        reward += anomaly_prob * 2.0

        return reward

    def score_test_case(self, test_case: TestCase, execution_result: Optional[Dict] = None) -> float:
        """Score a test case using RL."""
        state = self.get_state(test_case)

        if execution_result:
            # Update Q-values based on result
            reward = self.calculate_reward(test_case, execution_result)
            next_state = state  # Simplified: stay in same state
            action = "evaluate"  # Simplified action
            self.update_q_value(state, action, reward, next_state)

        # Return Q-value as score
        if state in self.q_table and "evaluate" in self.q_table[state]:
            return self.q_table[state]["evaluate"]

        return test_case.fitness_score  # Fallback to genetic fitness


def genetic_generate(
    sensor_configs: List[Dict],
    protocols: List[str],
    execution_results: List[Dict],
    generations: int = 10,
) -> List[TestCase]:
    """Generate optimized test cases using genetic algorithm."""
    generator = GeneticGenerator(max_generations=generations)
    generator.initialize_population(sensor_configs, protocols)

    for _ in range(generations):
        generator.evolve(sensor_configs, protocols, execution_results)

    # Return top test cases
    generator.population.sort(key=lambda x: x.fitness_score, reverse=True)
    return generator.population[:20]  # Return top 20


async def genetic_generate_async(
    sensor_configs: List[Dict],
    protocols: List[str],
    execution_results: List[Dict],
    generations: int = 10,
) -> List[TestCase]:
    """Asynchronous genetic test case generation."""
    generator = GeneticGenerator(max_generations=generations)
    generator.initialize_population(sensor_configs, protocols)

    for _ in range(generations):
        await generator.evolve_async(sensor_configs, protocols, execution_results)

    # Return top test cases
    generator.population.sort(key=lambda x: x.fitness_score, reverse=True)
    return generator.population[:20]


def rl_score(test_case: TestCase, execution_result: Optional[Dict] = None) -> float:
    """Score test case using reinforcement learning."""
    scorer = RLScorer()
    return scorer.score_test_case(test_case, execution_result)