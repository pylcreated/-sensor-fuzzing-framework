#!/usr/bin/env python3
"""Simple test for genetic algorithm functionality."""

from sensor_fuzz.data_gen.genetic_rl import TestCase, GeneticGenerator

def test_basic_genetic():
    """方法说明：执行 test basic genetic 相关逻辑。"""
    print("Testing basic genetic algorithm functionality...")

    # Create test data
    sensor_configs = [{"range": [0, 10], "signal_type": "voltage"}]
    protocols = ["mqtt"]

    # Create generator
    generator = GeneticGenerator(population_size=10, max_generations=2)

    # Initialize population
    generator.initialize_population(sensor_configs, protocols)
    print(f" Initialized population with {len(generator.population)} test cases")

    # Test evolution
    execution_results = [
        {"protocol": "mqtt", "error_type": "timeout", "success": True, "coverage": 0.3},
    ]

    evolved = generator.evolve(sensor_configs, protocols, execution_results)
    print(f" Evolution completed, population size: {len(evolved)}")

    # Check fitness scores
    fitness_scores = [tc.fitness_score for tc in evolved]
    print(f" Fitness scores range: {min(fitness_scores):.3f} - {max(fitness_scores):.3f}")

    print(" Basic genetic algorithm test passed!")

if __name__ == "__main__":
    test_basic_genetic()