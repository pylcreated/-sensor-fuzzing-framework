"""Comprehensive Prometheus metrics for industrial sensor fuzzing."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram
import time

# Core execution metrics
TEST_CASES_TOTAL = Counter(
    "sf_test_cases_total",
    "Total test cases generated",
    ["protocol", "sensor_type", "category"],
)

TEST_CASES_SUCCESS = Counter(
    "sf_test_cases_success_total",
    "Total successful test cases",
    ["protocol", "sensor_type"],
)

TEST_CASES_FAILED = Counter(
    "sf_test_cases_failed_total",
    "Total failed test cases",
    ["protocol", "sensor_type", "error_type"],
)

# Anomaly detection metrics
ANOMALIES_DETECTED = Counter(
    "sf_anomalies_detected_total",
    "Total detected anomalies",
    ["detection_method", "severity"],
)

FALSE_POSITIVES = Counter(
    "sf_false_positives_total", "Total false positive detections", ["detection_method"]
)

# Performance metrics
RESPONSE_TIME = Histogram(
    "sf_response_time_seconds",
    "Response time for test cases",
    ["protocol", "sensor_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0),
)

THROUGHPUT = Gauge(
    "sf_throughput_cases_per_second", "Test case throughput", ["protocol"]
)

# Resource usage metrics
CPU_USAGE = Gauge("sf_cpu_usage_percent", "CPU usage percent")
MEMORY_USAGE = Gauge("sf_memory_usage_bytes", "Memory usage in bytes")
DISK_USAGE = Gauge("sf_disk_usage_bytes", "Disk usage in bytes")

# Thread pool metrics
ACTIVE_THREADS = Gauge("sf_active_threads", "Number of active threads")
THREAD_POOL_SIZE = Gauge("sf_thread_pool_size", "Thread pool size")

# AI metrics
AI_ANALYSIS_TIME = Histogram(
    "sf_ai_analysis_time_seconds",
    "Time spent on AI analysis",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

AI_CONFIDENCE = Gauge(
    "sf_ai_confidence_score", "AI anomaly detection confidence score", ["model_type"]
)

# System health metrics
UPTIME = Gauge("sf_uptime_seconds", "Application uptime in seconds")
LAST_SUCCESSFUL_TEST = Gauge(
    "sf_last_successful_test_timestamp", "Timestamp of last successful test"
)
CONFIG_RELOADS = Counter("sf_config_reloads_total", "Total configuration reloads")

# Error tracking
ERRORS_TOTAL = Counter(
    "sf_errors_total", "Total errors by type", ["error_type", "component"]
)

# Test session metrics
ACTIVE_SESSIONS = Gauge("sf_active_sessions", "Number of active test sessions")
SESSION_DURATION = Histogram(
    "sf_session_duration_seconds",
    "Duration of test sessions",
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400),
)

# Custom business metrics
SIL_COVERAGE = Gauge(
    "sf_sil_coverage_percent", "SIL coverage percentage achieved", ["sil_level"]
)

PROTOCOL_COVERAGE = Gauge(
    "sf_protocol_coverage_percent", "Protocol test coverage percentage", ["protocol"]
)

# Initialize uptime tracking
_start_time = time.time()
UPTIME.set_function(lambda: time.time() - _start_time)
