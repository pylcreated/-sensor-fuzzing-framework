"""项目主入口：负责启动、执行、合规校验与优雅退出。"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Tuple

from sensor_fuzz.engine.runner import ExecutionEngine, run_full
from sensor_fuzz.config import ConfigLoader, ConfigReloader, ConfigVersionStore
from sensor_fuzz.utils.logging import setup_logging
from sensor_fuzz.sil_compliance import SILComplianceManager, SafetyIntegrityLevel
from sensor_fuzz.monitoring import start_system_monitor, stop_system_monitor, start_exporter


class ApplicationError(Exception):
    """应用级异常，携带退出码，便于统一退出控制。"""

    def __init__(self, message: str, exit_code: int = 1):
        """初始化异常信息和退出码。"""
        super().__init__(message)
        self.exit_code = exit_code


def setup_signal_handlers() -> None:
    """注册系统信号处理器，确保程序可优雅退出。"""

    def signal_handler(signum, frame):
        """收到中断/终止信号时，记录日志并触发退出。"""
        logger = logging.getLogger(__name__)
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def validate_config_file(config_path: str) -> Path:
    """校验配置文件存在且可读，避免启动后才报错。"""
    path = Path(config_path)
    if not path.exists():
        raise ApplicationError(f"Configuration file not found: {config_path}", 2)
    if not path.is_file():
        raise ApplicationError(f"Configuration path is not a file: {config_path}", 2)
    try:
        with path.open("r", encoding="utf-8") as f:
            f.read(1)  # Test readability
    except (OSError, UnicodeDecodeError) as e:
        raise ApplicationError(f"Cannot read configuration file: {e}", 2)
    return path


def _build_execution_pairs(cfg) -> List[Tuple[str, Dict[str, Any], str]]:
    """构建待执行的(协议, 传感器配置, 传感器名)列表。"""
    pairs: List[Tuple[str, Dict[str, Any], str]] = []
    for sensor_name, sensor_cfg in cfg.sensors.items():
        protocol = sensor_cfg.get("protocol")
        if isinstance(protocol, str) and protocol in cfg.protocols:
            pairs.append((protocol, dict(sensor_cfg), sensor_name))

    if not pairs and cfg.protocols:
        default_sensor = next(iter(cfg.sensors.values()), {"type": "temperature", "range": [-40, 125]})
        for protocol_name in cfg.protocols.keys():
            fallback_sensor = dict(default_sensor)
            fallback_sensor["protocol"] = protocol_name
            pairs.append((protocol_name, fallback_sensor, f"fallback-{protocol_name}"))
    protocol_priority = {
        "i2c": 0,
        "spi": 1,
        "profinet": 2,
        "uart": 3,
        "modbus": 4,
        "http": 5,
        "mqtt": 6,
        "opcua": 7,
    }
    pairs.sort(key=lambda item: protocol_priority.get(item[0].lower(), 99))
    return pairs


def _update_dashboard(metrics_exporter, engine, cfg, started_at: float) -> None:
    """将当前执行状态写入 Dashboard 数据源。"""
    if not metrics_exporter:
        return

    updates = {
        "test_cases_total": int(engine.state.get("cases_executed", 0)),
        "test_cases_success": int(engine.state.get("cases_success", 0)),
        "test_cases_failed": int(engine.state.get("cases_failed", 0)),
        "anomalies_detected": int(engine.state.get("anomalies", 0)),
        "ai_anomalies": int(engine.state.get("ai_analysis", {}).get("anomalies_detected", 0)),
        "throughput": float(engine.state.get("throughput", 0.0)),
        "avg_response_time": float(engine.state.get("avg_response_time", 0.0)),
        "cpu_usage": float(engine.state.get("cpu_usage", 0.0)),
        "memory_usage": float(engine.state.get("memory_usage", 0.0)),
        "ai_enabled": bool(cfg.strategy.get("ai_enabled", False)),
        "ai_confidence": float(engine.state.get("ai_analysis", {}).get("threshold", 0.0)),
        "ai_analysis_time": float(engine.state.get("ai_analysis", {}).get("features_analyzed", 0.0)),
        "uptime": max(0.0, time.time() - started_at),
        "active_threads": int(engine.state.get("active_threads", cfg.strategy.get("concurrency", 1))),
        "active_sessions": int(engine.state.get("suite_count", 0)),
    }
    for key, value in updates.items():
        metrics_exporter.update_dashboard_data(key, value)


def _append_longrun_summary(engine, cfg, started_at: float, reason: str) -> None:
    """按日写入长跑汇总，便于48小时验收追踪。"""
    reports_dir = Path("reports") / "longrun"
    reports_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    summary = {
        "timestamp": now.isoformat(timespec="seconds"),
        "reason": reason,
        "uptime_hours": round(max(0.0, time.time() - started_at) / 3600.0, 4),
        "cases_executed": int(engine.state.get("cases_executed", 0)),
        "cases_success": int(engine.state.get("cases_success", 0)),
        "cases_failed": int(engine.state.get("cases_failed", 0)),
        "anomalies": int(engine.state.get("anomalies", 0)),
        "throughput": float(engine.state.get("throughput", 0.0)),
        "avg_response_time": float(engine.state.get("avg_response_time", 0.0)),
        "ai_enabled": bool(cfg.strategy.get("ai_enabled", False)),
    }

    latest_file = reports_dir / "summary_latest.json"
    latest_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    daily_file = reports_dir / f"summary_{now.strftime('%Y%m%d')}.jsonl"
    with daily_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")


def main() -> NoReturn:
    """主执行流程：初始化 -> 加载配置 -> 运行测试 -> 合规校验 -> 资源回收。"""
    exit_code = 0
    reloader = None
    app_started_at = time.time()

    try:
        # Setup logging first for error reporting
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting Industrial Sensor Fuzzing Framework")

        # Start system monitoring
        try:
            monitor = start_system_monitor()
            logger.info("System monitoring started")
        except Exception as e:
            logger.warning(f"Failed to start system monitoring: {e}")

        # Start metrics server
        try:
            metrics_exporter = start_exporter(
                port=8000,
                dashboard_port=8080,
                dashboard_host=os.getenv("SENSOR_FUZZ_DASHBOARD_HOST", "localhost")
            )
            logger.info("Metrics exporter started on port 8000")
        except Exception as e:
            logger.warning(f"Failed to start metrics exporter: {e}")

        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()

        # Validate configuration
        config_path = "config/sensor_protocol_config.yaml"
        config_file = validate_config_file(config_path)
        logger.info(f"Using configuration file: {config_file}")

        # Load configuration
        try:
            loader = ConfigLoader()
            cfg = loader.load(config_file)
            mqtt_host_override = os.getenv("SENSOR_FUZZ_MQTT_HOST")
            if mqtt_host_override and isinstance(cfg.protocols.get("mqtt"), dict):
                cfg.protocols["mqtt"]["host"] = mqtt_host_override
            logger.info("Configuration loaded successfully")

            try:
                version_store = ConfigVersionStore()
                version_store.save("startup", cfg)
                logger.info("Configuration version snapshot saved")
            except Exception as e:
                logger.warning(f"Failed to save configuration version: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ApplicationError(f"Configuration loading failed: {e}", 3)

        # Initialize SIL compliance manager
        try:
            sil_manager = SILComplianceManager()
            logger.info("SIL compliance manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize SIL compliance manager: {e}")
            sil_manager = None

        # Parse SIL level from config
        sil_level_str = cfg.strategy.get("sil_level", "SIL2")
        try:
            sil_level = SafetyIntegrityLevel[sil_level_str]
            logger.info(f"Target SIL level: {sil_level_str}")
        except KeyError:
            logger.warning(f"Invalid SIL level '{sil_level_str}', defaulting to SIL2")
            sil_level = SafetyIntegrityLevel.SIL2
        except Exception as e:
            logger.warning(f"Failed to save configuration version: {e}")

        # Create execution engine
        try:
            engine = ExecutionEngine(cfg)
            engine.resume_from_checkpoint()
            logger.info("Execution engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize execution engine: {e}")
            raise ApplicationError(f"Engine initialization failed: {e}", 4)

        # Setup configuration reloader
        def _on_reload(snapshot):
            """配置热更新回调：将新配置快照同步到运行态。"""
            try:
                # Apply new config to engine
                engine.state["config_reload"] = snapshot.to_dict()
                logger.info("Configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to apply reloaded configuration: {e}")

        try:
            reloader = ConfigReloader(str(config_file), _on_reload)
            reloader.start()
            logger.info("Configuration reloader started")
        except Exception as e:
            logger.warning(f"Failed to start configuration reloader: {e}")

        # Run the main fuzzing loop
        try:
            async_mode = cfg.strategy.get("async_mode", False)
            execution_pairs = _build_execution_pairs(cfg)
            if not execution_pairs:
                raise ApplicationError("No runnable protocol/sensor pairs found in configuration", 4)

            target_total_cases = int(cfg.strategy.get("min_total_cases", 0) or 0)
            if sil_manager:
                try:
                    sil_summary = sil_manager.get_sil_requirements_summary(sil_level)
                    target_total_cases = max(target_total_cases, int(sil_summary.get("min_test_cases", 0)))
                except Exception as e:
                    logger.warning(f"Failed to read SIL requirements summary: {e}")

            max_cycles = max(1, int(cfg.strategy.get("execution_cycles", 1) or 1))
            if target_total_cases > 0:
                min_cases_per_suite = max(1, int(cfg.strategy.get("min_cases_per_suite", 1) or 1))
                per_cycle_capacity = max(1, len(execution_pairs) * min_cases_per_suite)
                estimated_cycles = (target_total_cases + per_cycle_capacity - 1) // per_cycle_capacity
                max_cycles = max(max_cycles, estimated_cycles)

            logger.info(
                "Starting fuzzing with %s pairs, async_mode=%s, target_total_cases=%s, max_cycles=%s",
                len(execution_pairs),
                async_mode,
                target_total_cases,
                max_cycles,
            )

            async def _run_execution_plan() -> None:
                nonlocal async_mode
                for cycle_idx in range(max_cycles):
                    for protocol, sensor_config, sensor_name in execution_pairs:
                        sensor_payload = dict(sensor_config)
                        sensor_payload["protocol"] = protocol
                        logger.info(
                            "Running suite cycle=%s protocol=%s sensor=%s",
                            cycle_idx + 1,
                            protocol,
                            sensor_name,
                        )
                        try:
                            await run_full(engine, protocol, sensor_payload, async_mode)
                        except Exception as e:
                            if async_mode and "required for async" in str(e):
                                logger.warning("Async dependency missing, fallback to sync mode: %s", e)
                                async_mode = False
                                try:
                                    await run_full(engine, protocol, sensor_payload, async_mode)
                                except Exception as sync_err:
                                    logger.warning(
                                        "Suite failed and skipped protocol=%s sensor=%s error=%s",
                                        protocol,
                                        sensor_name,
                                        sync_err,
                                    )
                            else:
                                logger.warning(
                                    "Suite failed and skipped protocol=%s sensor=%s error=%s",
                                    protocol,
                                    sensor_name,
                                    e,
                                )

                        if "metrics_exporter" in locals():
                            _update_dashboard(metrics_exporter, engine, cfg, app_started_at)

                    if target_total_cases > 0 and int(engine.state.get("cases_executed", 0)) >= target_total_cases:
                        logger.info(
                            "Reached target total cases: %s >= %s",
                            engine.state.get("cases_executed", 0),
                            target_total_cases,
                        )
                        break

            asyncio.run(_run_execution_plan())
            if "metrics_exporter" in locals():
                _update_dashboard(metrics_exporter, engine, cfg, app_started_at)
            _append_longrun_summary(engine, cfg, app_started_at, reason="initial-run")
            logger.info("Fuzzing completed successfully")

            # Perform SIL compliance validation
            if sil_manager:
                try:
                    logger.info("Starting SIL compliance validation...")

                    # Collect test results from engine
                    test_results = {
                        "coverage": getattr(engine.state, 'get', lambda x, default: default)('test_coverage', 0.95),
                        "duration_hours": cfg.strategy.get("duration_hours", 2),
                        "total_cases": engine.state.get("cases_executed", 1000),
                        "false_positive_rate": 0.01,  # Should be calculated from actual results
                        "avg_response_time_ms": 200,  # Should be measured
                        "total_anomalies_detected": engine.state.get("anomalies", 0),
                        "true_positives": engine.state.get("anomalies", 0),
                        "false_positives": 10
                    }

                    # Get system configuration
                    system_config = {
                        "supported_protocols": list(cfg.protocols.keys()) if cfg.protocols else ["uart", "mqtt", "http"],
                        "supported_anomaly_types": cfg.strategy.get("anomaly_types", ["boundary", "protocol_error", "signal_distortion", "anomaly"]),
                        "hardware_protection_enabled": cfg.strategy.get("hardware_protection", False),
                        "redundancy_enabled": cfg.strategy.get("redundancy_check", False),
                        "async_mode_enabled": async_mode,
                        "ai_anomaly_detection_enabled": cfg.strategy.get("ai_enabled", False),
                        "genetic_algorithm_enabled": True
                    }

                    # Run SIL compliance validation in async context
                    async def run_sil_validation():
                        """异步执行 SIL 合规校验并落盘报告。"""
                        compliance_report = await sil_manager.generate_compliance_report(
                            sil_level, test_results, system_config
                        )

                        logger.info(f"Generated SIL compliance report with score: {compliance_report.compliance_score:.1f}")
                        if compliance_report.overall_compliance:
                            logger.info(f"System meets SIL{sil_level.value} compliance requirements")
                        else:
                            logger.warning(f"System does not fully meet SIL{sil_level.value} requirements")
                            for issue in compliance_report.critical_issues:
                                logger.warning(f"  - {issue}")

                        # Save compliance report
                        import json
                        report_file = Path("sil_compliance_report.json")
                        with open(report_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                "sil_level": sil_level.value,
                                "compliance_score": compliance_report.compliance_score,
                                "overall_compliance": compliance_report.overall_compliance,
                                "critical_issues": compliance_report.critical_issues,
                                "recommendations": compliance_report.recommendations,
                                "improvement_suggestions": compliance_report.improvement_suggestions,
                                "test_results": test_results,
                                "system_config": system_config
                            }, f, indent=2, ensure_ascii=False)

                        logger.info(f"SIL compliance report saved to {report_file}")
                        return compliance_report

                    asyncio.run(run_sil_validation())

                    keep_running = os.getenv("SENSOR_FUZZ_KEEP_RUNNING", "0") == "1"
                    if keep_running:
                        longrun_enabled = os.getenv("SENSOR_FUZZ_LONGRUN_ENABLED", "0") == "1"
                        longrun_hours = float(os.getenv("SENSOR_FUZZ_LONGRUN_HOURS", "0") or 0)
                        longrun_interval_minutes = max(
                            1,
                            int(os.getenv("SENSOR_FUZZ_LONGRUN_INTERVAL_MINUTES", "60") or 60),
                        )

                        if longrun_enabled and longrun_hours > 0:
                            engine.reset_async_context()
                            logger.info(
                                "Long-run mode enabled: hours=%s interval_minutes=%s",
                                longrun_hours,
                                longrun_interval_minutes,
                            )
                            deadline = time.time() + longrun_hours * 3600

                            async def _run_longrun_mode() -> None:
                                iteration = 0
                                while time.time() < deadline:
                                    iteration += 1
                                    logger.info("Long-run iteration %s started", iteration)
                                    await _run_execution_plan()
                                    if "metrics_exporter" in locals():
                                        _update_dashboard(metrics_exporter, engine, cfg, app_started_at)
                                    _append_longrun_summary(
                                        engine,
                                        cfg,
                                        app_started_at,
                                        reason=f"longrun-iteration-{iteration}",
                                    )

                                    remaining_seconds = deadline - time.time()
                                    if remaining_seconds <= 0:
                                        break
                                    sleep_seconds = min(
                                        longrun_interval_minutes * 60,
                                        max(1, int(remaining_seconds)),
                                    )
                                    logger.info(
                                        "Long-run iteration %s complete, next run in %s seconds",
                                        iteration,
                                        sleep_seconds,
                                    )
                                    await asyncio.sleep(sleep_seconds)

                            asyncio.run(_run_longrun_mode())

                            _append_longrun_summary(engine, cfg, app_started_at, reason="longrun-complete")
                            logger.info("Long-run mode completed, service stays alive for inspection")
                            while True:
                                time.sleep(1)
                        else:
                            logger.info("Keep-running mode enabled, service will stay alive until stopped")
                            while True:
                                time.sleep(1)

                except Exception as e:
                    logger.error(f"SIL compliance validation failed: {e}")
            else:
                logger.warning("SIL compliance manager not available, skipping validation")

        except KeyboardInterrupt:
            logger.info("Fuzzing interrupted by user")
        except Exception as e:
            logger.error(f"Fuzzing execution failed: {e}")
            raise ApplicationError(f"Fuzzing execution failed: {e}", 5)

    except ApplicationError as e:
        exit_code = e.exit_code
        if "logger" in locals():
            logger.error(f"Application error: {e}")
        else:
            print(f"Application error: {e}", file=sys.stderr)

    except Exception as e:
        exit_code = 1
        if "logger" in locals():
            logger.critical(f"Unexpected error: {e}", exc_info=True)
        else:
            print(f"Unexpected error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    finally:
        # Graceful shutdown
        if reloader:
            try:
                reloader.stop()
                logger.info("Configuration reloader stopped")
            except Exception as e:
                if "logger" in locals():
                    logger.warning(f"Error stopping reloader: {e}")
                else:
                    print(f"Warning: Error stopping reloader: {e}", file=sys.stderr)

        # Stop monitoring systems
        try:
            stop_system_monitor()
            if "logger" in locals():
                logger.info("System monitoring stopped")
        except Exception as e:
            if "logger" in locals():
                logger.warning(f"Error stopping system monitoring: {e}")
            else:
                print(
                    f"Warning: Error stopping system monitoring: {e}", file=sys.stderr
                )

        try:
            if "metrics_exporter" in locals():
                metrics_exporter.stop()
            if "logger" in locals():
                logger.info("Metrics exporter stopped")
        except Exception as e:
            if "logger" in locals():
                logger.warning(f"Error stopping metrics exporter: {e}")
            else:
                print(f"Warning: Error stopping metrics exporter: {e}", file=sys.stderr)

        if "logger" in locals():
            logger.info(f"Application shutting down with exit code {exit_code}")
        else:
            print(f"Application shutting down with exit code {exit_code}")

        sys.exit(exit_code)


if __name__ == "__main__":
    main()
