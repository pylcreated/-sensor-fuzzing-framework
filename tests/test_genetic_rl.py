"""Tests for genetic algorithm and reinforcement learning test case generation."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

# 导入遗传算法和强化学习相关模块
from sensor_fuzz.data_gen.genetic_rl import (
    TestCase,
    GeneticGenerator,
    RLScorer,
    genetic_generate,
    rl_score,
)

# 定义测试TestCase类功能的测试类
class TestTestCase:
    """测试TestCase类功能。"""

    def test_test_case_creation(self):
        """测试TestCase的基本创建。"""
        # 定义传感器配置和变异信息
        sensor_config = {"range": [0, 10], "signal_type": "voltage"}
        mutations = [{"desc": "boundary", "value": 10.1}]

        # 创建TestCase实例并验证其属性
        tc = TestCase(
            sensor_config=sensor_config,
            protocol="mqtt",
            mutations=mutations,
            fitness_score=0.8,
        )

        assert tc.sensor_config == sensor_config
        assert tc.protocol == "mqtt"
        assert tc.mutations == mutations
        assert tc.fitness_score == 0.8

    def test_test_case_to_dict(self):
        """测试TestCase的序列化为字典。"""
        # 创建TestCase实例
        tc = TestCase(
            sensor_config={"range": [0, 10]},
            protocol="mqtt",
            mutations=[{"desc": "boundary"}],
            fitness_score=0.8,
            coverage=0.7,
            anomaly_probability=0.6,
            generation=5,
        )

        # 验证序列化结果
        data = tc.to_dict()
        assert data["sensor_config"] == {"range": [0, 10]}
        assert data["protocol"] == "mqtt"
        assert data["fitness_score"] == 0.8
        assert data["coverage"] == 0.7
        assert data["anomaly_probability"] == 0.6
        assert data["generation"] == 5

    def test_test_case_from_dict(self):
        """测试从字典反序列化为TestCase。"""
        # 定义字典数据
        data = {
            "sensor_config": {"range": [0, 10]},
            "protocol": "mqtt",
            "mutations": [{"desc": "boundary"}],
            "fitness_score": 0.8,
            "coverage": 0.7,
            "anomaly_probability": 0.6,
            "generation": 5,
        }

        # 验证反序列化结果
        tc = TestCase.from_dict(data)
        assert tc.sensor_config == {"range": [0, 10]}
        assert tc.protocol == "mqtt"
        assert tc.fitness_score == 0.8
        assert tc.coverage == 0.7
        assert tc.anomaly_probability == 0.6
        assert tc.generation == 5

# 定义测试GeneticGenerator功能的测试类
class TestGeneticGenerator:
    """测试GeneticGenerator功能。"""

    def test_generator_initialization(self):
        """测试遗传生成器的初始化。"""
        # 创建生成器实例并验证其属性
        generator = GeneticGenerator(
            population_size=50,
            mutation_rate=0.1,
            crossover_rate=0.8,
            elitism_rate=0.1,
        )

        assert generator.population_size == 50
        assert generator.mutation_rate == 0.1
        assert generator.crossover_rate == 0.8
        assert generator.elitism_rate == 0.1
        assert generator.generation == 0
        assert len(generator.population) == 0

    def test_population_initialization(self):
        """测试种群初始化。"""
        # 定义传感器配置和协议
        sensor_configs = [
            {"range": [0, 10], "signal_type": "voltage"},
            {"range": [4, 20], "signal_type": "current"},
        ]
        protocols = ["mqtt", "modbus"]

        # 初始化种群并验证其属性
        generator = GeneticGenerator(population_size=10)
        generator.initialize_population(sensor_configs, protocols)

        assert len(generator.population) == 10
        for tc in generator.population:
            assert tc.sensor_config in sensor_configs
            assert tc.protocol in protocols
            assert isinstance(tc.mutations, list)
            assert tc.generation == 0

    def test_fitness_evaluation(self):
        """测试适应度评估。"""
        # 定义执行结果
        generator = GeneticGenerator()
        execution_results = [
            {"protocol": "mqtt", "error_type": "timeout", "code_path": "send", "success": True},
            {"protocol": "mqtt", "error_type": "crc", "code_path": "receive", "success": False},
        ]

        # 创建测试用例并评估适应度
        tc = TestCase(
            sensor_config={"range": [0, 10]},
            protocol="mqtt",
            mutations=[{"desc": "boundary"}],
        )

        generator._evaluate_fitness(tc, execution_results)

        # 验证适应度分数和覆盖率是否在合理范围内
        assert tc.fitness_score >= 0.0
        assert tc.coverage >= 0.0
        assert tc.fitness_score <= 1.0
        assert tc.coverage <= 1.0

    def test_parent_selection(self):
        """Test parent selection."""
        generator = GeneticGenerator(population_size=10)
        # Create mock population with different fitness scores
        generator.population = [
            TestCase(sensor_config={}, protocol="mqtt", fitness_score=i/10.0)
            for i in range(10)
        ]

        parents = generator.select_parents()

        assert len(parents) == 10
        # Should select higher fitness individuals more often
        high_fitness_count = sum(1 for p in parents if p.fitness_score > 0.5)
        assert high_fitness_count >= 3  # At least some high fitness parents

    def test_crossover(self):
        """Test crossover operation."""
        generator = GeneticGenerator()

        parent1 = TestCase(
            sensor_config={"range": [0, 10]},
            protocol="mqtt",
            mutations=[{"desc": "boundary1"}, {"desc": "boundary2"}],
        )
        parent2 = TestCase(
            sensor_config={"range": [4, 20]},
            protocol="modbus",
            mutations=[{"desc": "protocol1"}, {"desc": "protocol2"}],
        )

        child1, child2 = generator.crossover(parent1, parent2)

        assert isinstance(child1, TestCase)
        assert isinstance(child2, TestCase)
        assert child1.generation == 1
        assert child2.generation == 1

    def test_mutation(self):
        """Test mutation operation."""
        sensor_configs = [{"range": [0, 10], "signal_type": "voltage"}]
        protocols = ["mqtt"]

        generator = GeneticGenerator()
        original = TestCase(
            sensor_config=sensor_configs[0],
            protocol="mqtt",
            mutations=[{"desc": "boundary"}],
        )

        # Force mutation by setting high mutation rate
        generator.mutation_rate = 1.0
        mutated = generator.mutate(original, sensor_configs, protocols)

        assert isinstance(mutated, TestCase)
        assert mutated.generation == 1

    def test_evolution(self):
        """Test full evolution cycle."""
        sensor_configs = [{"range": [0, 10], "signal_type": "voltage"}]
        protocols = ["mqtt"]
        execution_results = [
            {"protocol": "mqtt", "error_type": "timeout", "success": True},
        ]

        generator = GeneticGenerator(population_size=20, max_generations=5)
        generator.initialize_population(sensor_configs, protocols)

        evolved = generator.evolve(sensor_configs, protocols, execution_results)

        assert len(evolved) == 20
        assert generator.generation == 1

        # Check that fitness scores are calculated
        for tc in evolved:
            assert hasattr(tc, 'fitness_score')


class TestRLScorer:
    """Test RLScorer functionality."""

    def test_scorer_initialization(self):
        """Test RL scorer initialization."""
        scorer = RLScorer(learning_rate=0.01, discount_factor=0.9)

        assert scorer.learning_rate == 0.01
        assert scorer.discount_factor == 0.9
        assert isinstance(scorer.q_table, dict)

    def test_state_representation(self):
        """Test state representation generation."""
        scorer = RLScorer()

        tc = TestCase(
            sensor_config={"range": [0, 10]},
            protocol="mqtt",
            mutations=[
                {"desc": "boundary-test"},
                {"desc": "protocol-error"},
            ],
        )

        state = scorer.get_state(tc)
        assert "mqtt" in state
        assert "2" in state  # mutation count
        assert "2" in state  # unique mutation types

    def test_action_selection(self):
        """Test action selection."""
        scorer = RLScorer()

        state = "mqtt_2_2"
        actions = scorer.get_actions(state)

        assert "keep" in actions
        assert "mutate" in actions
        assert "discard" in actions
        assert "prioritize" in actions

        # Test epsilon-greedy selection
        action = scorer.choose_action(state, epsilon=1.0)  # Pure exploration
        assert action in actions

    def test_q_value_update(self):
        """Test Q-value updates."""
        scorer = RLScorer()

        state = "mqtt_1_1"
        action = "keep"
        reward = 1.0
        next_state = "mqtt_1_1"

        scorer.update_q_value(state, action, reward, next_state)

        assert state in scorer.q_table
        assert action in scorer.q_table[state]
        assert scorer.q_table[state][action] > 0

    def test_reward_calculation(self):
        """Test reward calculation."""
        scorer = RLScorer()

        tc = TestCase(sensor_config={}, protocol="mqtt", anomaly_probability=0.8)

        # Test anomaly detection reward
        result_anomaly = {"anomaly_detected": True, "coverage": 0.5, "success": True}
        reward = scorer.calculate_reward(tc, result_anomaly)
        assert reward > 10  # High reward for anomaly detection

        # Test failure penalty
        result_failure = {"anomaly_detected": False, "coverage": 0.0, "success": False}
        reward = scorer.calculate_reward(tc, result_failure)
        assert reward < 0  # Penalty for failure

    def test_test_case_scoring(self):
        """Test test case scoring."""
        scorer = RLScorer()

        tc = TestCase(
            sensor_config={},
            protocol="mqtt",
            fitness_score=0.7,
        )

        # Test scoring without execution result
        score = scorer.score_test_case(tc)
        assert score == 0.7  # Should return fitness score as fallback

        # Test scoring with execution result
        result = {"anomaly_detected": True, "coverage": 0.8, "success": True}
        score = scorer.score_test_case(tc, result)
        assert score >= 0.0


class TestGeneticFunctions:
    """Test top-level genetic functions."""

    def test_genetic_generate(self):
        """Test genetic_generate function."""
        sensor_configs = [{"range": [0, 10], "signal_type": "voltage"}]
        protocols = ["mqtt"]
        execution_results = [
            {"protocol": "mqtt", "error_type": "timeout", "success": True},
        ]

        test_cases = genetic_generate(
            sensor_configs,
            protocols,
            execution_results,
            generations=2,
        )

        assert len(test_cases) == 20  # Should return top 20
        assert all(isinstance(tc, TestCase) for tc in test_cases)

        # Should be sorted by fitness (descending)
        for i in range(len(test_cases) - 1):
            assert test_cases[i].fitness_score >= test_cases[i + 1].fitness_score

    def test_rl_score_function(self):
        """Test rl_score function."""
        tc = TestCase(sensor_config={}, protocol="mqtt", fitness_score=0.6)

        score = rl_score(tc)
        assert score == 0.6  # Should return fitness score initially

        # Test with execution result
        result = {"anomaly_detected": True, "coverage": 0.7, "success": True}
        score = rl_score(tc, result)
        assert score >= 0.0