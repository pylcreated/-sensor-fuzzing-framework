#!/usr/bin/env python3
"""72-hour continuous memory stability test for sensor fuzzing framework.

This script runs continuous operations to validate memory leak rate < 0.005%
over extended periods, with periodic memory monitoring and statistics.
"""

import argparse
import asyncio
import gc
import json
import logging
import psutil
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import threading

from sensor_fuzz.config.loader import FrameworkConfig
from sensor_fuzz.engine import ExecutionEngine
from sensor_fuzz.data_gen import generate_boundary_cases
from sensor_fuzz.monitoring.log_sink import ElkSink


class MemoryMonitor:
    """Memory monitoring and statistics collector."""

    def __init__(self, log_file: str = "memory_stability.log"):
        """方法说明：执行   init   相关逻辑。"""
        self.log_file = Path(log_file)
        self.readings: List[Dict] = []
        self.start_time = time.time()
        self.process = psutil.Process()
        self._running = False
        self._monitor_thread = None

    def start_monitoring(self, interval: float = 60.0):
        """Start background memory monitoring."""
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

    def _monitor_loop(self, interval: float):
        """Background monitoring loop."""
        while self._running:
            reading = self._take_reading()
            self.readings.append(reading)

            # Log to file
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(reading) + '\n')

            time.sleep(interval)

    def _take_reading(self) -> Dict:
        """Take a memory reading with timestamp."""
        mem_info = self.process.memory_info()
        return {
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': time.time() - self.start_time,
            'rss_mb': mem_info.rss / 1024 / 1024,
            'vms_mb': mem_info.vms / 1024 / 1024,
            'cpu_percent': self.process.cpu_percent()
        }

    def get_statistics(self) -> Dict:
        """Calculate memory statistics."""
        if not self.readings:
            return {}

        rss_values = [r['rss_mb'] for r in self.readings]
        elapsed_times = [r['elapsed_seconds'] for r in self.readings]

        # Calculate leak rate (MB per hour)
        if len(rss_values) > 1 and elapsed_times[-1] > elapsed_times[0]:
            leak_rate_mbh = (rss_values[-1] - rss_values[0]) / (elapsed_times[-1] - elapsed_times[0]) * 3600
        else:
            leak_rate_mbh = 0

        return {
            'total_readings': len(self.readings),
            'duration_hours': elapsed_times[-1] / 3600 if elapsed_times else 0,
            'initial_memory_mb': rss_values[0] if rss_values else 0,
            'final_memory_mb': rss_values[-1] if rss_values else 0,
            'peak_memory_mb': max(rss_values) if rss_values else 0,
            'min_memory_mb': min(rss_values) if rss_values else 0,
            'memory_growth_mb': (rss_values[-1] - rss_values[0]) if rss_values else 0,
            'leak_rate_mb_per_hour': leak_rate_mbh,
            'leak_rate_percent': (leak_rate_mbh / (rss_values[0] if rss_values else 1)) * 100
        }


class StabilityTest:
    """Continuous stability testing framework."""

    def __init__(self, duration_hours: float = 72.0):
        """方法说明：执行   init   相关逻辑。"""
        self.duration_hours = duration_hours
        self.duration_seconds = duration_hours * 3600
        self.start_time = time.time()
        self.monitor = MemoryMonitor()
        self._shutdown = False
        self.cycle_count = 0  # Track total cycles

        # Test configuration
        self.config = FrameworkConfig(
            sensors={
                "stability_sensor": {
                    "range": [0, 100],
                    "signal_type": "voltage",
                    "anomaly_freq": 1
                }
            },
            protocols={
                "mqtt": {"host": "localhost"},
                "http": {"base_url": "http://localhost:8080"}
            },
            strategy={
                "concurrency": 10,
                "task_timeout": 2.0,
                "ai_enabled": False
            }
        )

        self.engine = ExecutionEngine(cfg=self.config)
        self.log_sink = ElkSink()

        # Setup signal handlers (only on Unix-like systems)
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (OSError, ValueError):
            # Signal handling not available on Windows or other platforms
            pass

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, initiating shutdown...")
        self._shutdown = True

    async def run_test_cycle(self):
        """Run one test cycle."""
        try:
            sensor = {
                "name": "stability_sensor",
                "range": [0, 100],
                "signal_type": "voltage"
            }

            # Test data generation
            cases = generate_boundary_cases(sensor)
            if len(cases) > 100:  # Limit for stability test
                cases = cases[:100]

            # Test connection pooling
            protocols = ["mqtt", "http"]
            for proto in protocols:
                try:
                    driver = self.engine._make_driver(proto)
                    # Simulate brief usage
                    await asyncio.sleep(0.01)
                    self.engine._connection_pools[proto.lower()].release(driver)
                except Exception as e:
                    # Expected if services not running
                    pass

            # Test logging
            log_entries = [{
                "timestamp": time.time(),
                "level": "INFO",
                "message": f"Stability test cycle at {datetime.now().isoformat()}",
                "component": "stability_test",
                "memory_mb": self.monitor._take_reading()['rss_mb']
            }]
            self.log_sink.write_logs(log_entries)

        except Exception as e:
            logging.error(f"Test cycle error: {e}")

    async def run_continuous_test(self):
        """Run the continuous stability test."""
        print(f"Starting {self.duration_hours}-hour memory stability test...")
        print("Press Ctrl+C to stop early")

        self.monitor.start_monitoring(interval=300.0)  # Every 5 minutes

        cycle_count = 0
        last_report = time.time()

        try:
            while not self._shutdown and (time.time() - self.start_time) < self.duration_seconds:
                await self.run_test_cycle()
                self.cycle_count += 1

                # Periodic reporting
                if time.time() - last_report > 3600:  # Every hour
                    elapsed_hours = (time.time() - self.start_time) / 3600
                    stats = self.monitor.get_statistics()
                    print(f"\n[{elapsed_hours:.1f}h] Status Report:")
                    print(f"  Cycles completed: {self.cycle_count}")
                    print(f"  Current memory: {stats.get('final_memory_mb', 0):.2f} MB")
                    print(f"  Peak memory: {stats.get('peak_memory_mb', 0):.2f} MB")
                    print(f"  Leak rate: {stats.get('leak_rate_mb_per_hour', 0):.6f} MB/h")
                    last_report = time.time()

                # Brief pause between cycles
                await asyncio.sleep(1.0)

                # Periodic garbage collection
                if self.cycle_count % 100 == 0:
                    gc.collect()

        except Exception as e:
            logging.error(f"Test execution error: {e}")
        finally:
            self.monitor.stop_monitoring()

    def generate_report(self):
        """Generate final test report."""
        stats = self.monitor.get_statistics()

        report = {
            'test_duration_hours': self.duration_hours,
            'actual_duration_hours': stats.get('duration_hours', 0),
            'total_cycles': self.cycle_count,
            'memory_stats': stats,
            'pool_stats': {},
            'timestamp': datetime.now().isoformat()
        }

        # Get pool statistics
        if hasattr(self.engine, '_connection_pools'):
            for proto, pool in self.engine._connection_pools.items():
                report['pool_stats'][proto] = pool.get_stats()

        # Save report
        with open('memory_stability_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        return report


def main():
    """方法说明：执行 main 相关逻辑。"""
    parser = argparse.ArgumentParser(description='72-hour memory stability test')
    parser.add_argument('--duration', type=float, default=72.0,
                       help='Test duration in hours (default: 72)')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick 1-hour test instead')

    args = parser.parse_args()

    if args.quick:
        args.duration = 1.0

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print(f"Memory Stability Test - {args.duration} hours")
    print("=" * 80)

    test = StabilityTest(duration_hours=args.duration)

    try:
        asyncio.run(test.run_continuous_test())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")

    # Generate final report
    print("\nGenerating final report...")
    report = test.generate_report()

    stats = report['memory_stats']
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Test Duration: {stats.get('duration_hours', 0):.2f} hours")
    print(f"Peak Memory: {stats.get('peak_memory_mb', 0):.2f} MB")
    print(f"Memory Growth: {stats.get('memory_growth_mb', 0):.2f} MB")
    print(f"Leak Rate: {stats.get('leak_rate_mb_per_hour', 0):.6f} MB/hour")
    print(f"Leak Rate: {stats.get('leak_rate_percent', 0):.6f}%")

    # Assessment
    peak_memory = stats.get('peak_memory_mb', 0)
    leak_rate_percent = stats.get('leak_rate_percent', 0)

    if peak_memory <= 350:
        print(" Memory usage target met (≤ 350 MB)")
    else:
        print(" Memory usage target failed (> 350 MB)")

    if abs(leak_rate_percent) < 0.005:
        print(" Memory leak rate acceptable (< 0.005%)")
    else:
        print(" Memory leak rate too high (≥ 0.005%)")

    print(f"\nDetailed report saved to: memory_stability_report.json")
    print(f"Memory log saved to: {test.monitor.log_file}")


if __name__ == "__main__":
    main()