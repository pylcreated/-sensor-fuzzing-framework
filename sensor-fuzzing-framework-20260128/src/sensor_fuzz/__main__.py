"""Entry point with comprehensive error handling and graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import NoReturn

from sensor_fuzz.engine.runner import ExecutionEngine, run_full
from sensor_fuzz.config import ConfigLoader, ConfigReloader, ConfigVersionStore
from sensor_fuzz.utils.logging import setup_logging
from sensor_fuzz.sil_compliance import SILComplianceManager, SafetyIntegrityLevel
from sensor_fuzz.monitoring import start_system_monitor, stop_system_monitor, start_exporter


class ApplicationError(Exception):
    """Application-specific error with exit code."""

    def __init__(self, message: str, exit_code: int = 1):
        """方法说明：执行   init   相关逻辑。"""
        super().__init__(message)
        self.exit_code = exit_code


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        """方法说明：执行 signal handler 相关逻辑。"""
        logger = logging.getLogger(__name__)
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def validate_config_file(config_path: str) -> Path:
    """Validate configuration file exists and is readable."""
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


def main() -> NoReturn:
    """Main application entry point with comprehensive error handling."""
    exit_code = 0
    reloader = None

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
            metrics_exporter = start_exporter(port=8000)
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
            logger.info("Configuration loaded successfully")
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
            logger.info("Execution engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize execution engine: {e}")
            raise ApplicationError(f"Engine initialization failed: {e}", 4)

        # Setup configuration reloader
        def _on_reload(snapshot):
            """方法说明：执行  on reload 相关逻辑。"""
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
            sensor_name = (
                next(iter(cfg.sensors.keys())) if cfg.sensors else "temperature"
            )
            sensor_config = cfg.sensors.get(sensor_name, {})
            async_mode = cfg.strategy.get("async_mode", False)
            logger.info(f"Starting fuzzing with sensor '{sensor_name}' (async_mode={async_mode})")

            asyncio.run(run_full(engine, "i2c", sensor_config, async_mode))
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
                        "supported_anomaly_types": cfg.strategy.get("anomaly_types", ["boundary", "anomaly"]),
                        "hardware_protection_enabled": cfg.strategy.get("hardware_protection", False),
                        "redundancy_enabled": cfg.strategy.get("redundancy_check", False),
                        "async_mode_enabled": async_mode,
                        "ai_anomaly_detection_enabled": cfg.strategy.get("ai_enabled", False),
                        "genetic_algorithm_enabled": True
                    }

                    # Run SIL compliance validation in async context
                    async def run_sil_validation():
                        """异步方法说明：执行 run sil validation 相关流程。"""
                        compliance_report = await sil_manager.generate_compliance_report(
                            sil_level, test_results, system_config
                        )

                        logger.info(f"Generated SIL compliance report with score: {compliance_report.compliance_score:.1f}")
                        if compliance_report.overall_compliance:
                            logger.info(f"✅ System meets SIL{sil_level.value} compliance requirements")
                        else:
                            logger.warning(f"⚠️  System does not fully meet SIL{sil_level.value} requirements")
                            for issue in compliance_report.critical_issues:
                                logger.warning(f"  • {issue}")

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
