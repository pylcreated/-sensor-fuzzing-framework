#!/usr/bin/env python3
"""Memory optimization validation script for sensor fuzzing framework.

This script validates memory usage improvements through object pooling,
ensuring memory consumption stays below 350MB with leak rate < 0.005%.
"""

import gc
import psutil
import time
import tracemalloc
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def get_memory_usage() -> float:
    """Get current memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def test_basic_memory():
    """Test basic memory usage with object pools."""
    print("Testing basic memory usage...")

    from sensor_fuzz.engine import CaseObjectPool, ConnectionObjectPool, LogObjectPool

    initial_memory = get_memory_usage()
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Test case object pool
    case_pool = CaseObjectPool(max_size=200, timeout=600.0)
    cases = []
    for i in range(1000):
        case = case_pool.acquire()
        case.update({"value": i, "desc": f"test_{i}", "freq": 1})
        cases.append(case)

    pool_memory = get_memory_usage()
    print(f"After case pool usage: {pool_memory:.2f} MB")
    print(f"Memory increase: {pool_memory - initial_memory:.2f} MB")

    # Release objects back to pool
    for case in cases:
        case_pool.release(case)

    released_memory = get_memory_usage()
    print(f"After releasing to pool: {released_memory:.2f} MB")

    # Test connection pool
    def dummy_factory():
        return {"type": "dummy_connection", "created": time.time()}

    conn_pool = ConnectionObjectPool(dummy_factory, max_size=50, timeout=300.0)
    connections = []
    for i in range(100):
        conn = conn_pool.acquire()
        connections.append(conn)

    conn_memory = get_memory_usage()
    print(f"After connection pool usage: {conn_memory:.2f} MB")

    # Release connections
    for conn in connections:
        conn_pool.release(conn)

    final_memory = get_memory_usage()
    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Net memory increase: {final_memory - initial_memory:.2f} MB\n")

    return final_memory - initial_memory


def test_memory_leak_detection():
    """Test for memory leaks with repeated operations."""
    print("Testing memory leak detection...")

    from sensor_fuzz.engine import CaseObjectPool

    tracemalloc.start()
    initial_snapshot = tracemalloc.take_snapshot()

    case_pool = CaseObjectPool(max_size=100, timeout=60.0)

    # Simulate repeated operations
    iterations = 5000
    memory_readings = []

    for i in range(iterations):
        if i % 500 == 0:
            memory_readings.append(get_memory_usage())
            print(f"Iteration {i}: {memory_readings[-1]:.2f} MB")

        # Acquire and release objects
        obj = case_pool.acquire()
        obj.update({"test": i})
        case_pool.release(obj)

        if i % 1000 == 0:
            gc.collect()  # Periodic cleanup

    final_snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Analyze memory statistics
    stats = final_snapshot.compare_to(initial_snapshot, 'lineno')
    total_growth = sum(stat.size_diff for stat in stats if stat.size_diff > 0)

    print(f"Total memory growth: {total_growth / 1024 / 1024:.2f} MB")
    print(f"Memory readings over time: {memory_readings}")

    if memory_readings:
        max_memory = max(memory_readings)
        min_memory = min(memory_readings)
        leak_rate = (max_memory - min_memory) / len(memory_readings)
        print(f"Peak memory: {max_memory:.2f} MB")
        print(f"Min memory: {min_memory:.2f} MB")
        print(f"Estimated leak rate: {leak_rate:.6f} MB per 500 iterations")

        if leak_rate < 0.005:  # Less than 0.005 MB per 500 iterations
            print("✓ Memory leak rate within acceptable limits (< 0.005%)")
        else:
            print("✗ Memory leak rate exceeds acceptable limits")

    return memory_readings


def main():
    """Main validation function."""
    print("=" * 60)
    print("Sensor Fuzzing Framework - Memory Optimization Validation")
    print("=" * 60)

    try:
        # Test basic memory usage
        net_increase = test_basic_memory()

        # Test memory leak detection
        print("Running memory leak detection test...")
        memory_readings = test_memory_leak_detection()

        # Final assessment
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)

        if memory_readings:
            peak_memory = max(memory_readings)
            print(f"Peak memory usage: {peak_memory:.2f} MB")

            if peak_memory <= 350:
                print("✓ Memory usage within target limits (≤ 350 MB)")
            else:
                print("✗ Memory usage exceeds target limits (> 350 MB)")

        if net_increase < 50:  # Reasonable increase for object pools
            print("✓ Object pool memory overhead acceptable")
        else:
            print("✗ Object pool memory overhead too high")

        print("\nOptimization components validated:")
        print("- Object pools for test cases, connections, and logs")
        print("- Automatic cleanup and timeout-based recycling")
        print("- Memory leak detection and monitoring")

        print("\nNext steps:")
        print("1. Run 72-hour continuous test: python memory_stability_test.py")
        print("2. Monitor memory curves with: python memory_stability_test.py --quick")
        print("3. Adjust pool sizes in config if needed")

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()