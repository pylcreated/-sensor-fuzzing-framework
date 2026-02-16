"""Execution engine implementing protocol dispatch, concurrency, checkpoints."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

try:  # coloredlogs is optional; fallback to basic logging if missing
    import coloredlogs
except ImportError:  # pragma: no cover - exercised only when coloredlogs absent
    coloredlogs = None  # type: ignore

from sensor_fuzz.config.loader import FrameworkConfig
from sensor_fuzz.config.config_manager import ConfigManager
from sensor_fuzz.data_gen import (
    AdaptiveMutator,
    build_poc_tasks,
    distort_signal,
    generate_anomaly_values,
    generate_boundary_cases,
    generate_protocol_errors,
    poc_safety_ok,
    protocol_compat_ok,
    protobuf_syntax_ok,
)

try:
    from sensor_fuzz.ai import AnomalyDetector

    AI_AVAILABLE = True
except ImportError:
    AnomalyDetector = None
    AI_AVAILABLE = False
from sensor_fuzz.engine.checkpoint import Checkpoint, CheckpointStore
from sensor_fuzz.engine.concurrency import AsyncBoundedExecutor
from sensor_fuzz.engine.memory_pool import ConnectionObjectPool
from sensor_fuzz.engine.drivers import (
    HttpDriver,
    MqttDriver,
    ModbusTcpDriver,
    OpcUaDriver,
    UartDriver,
    get_restartless_driver,
    driver_pool,
)
from sensor_fuzz.monitoring import metrics


class ExecutionEngine:
    """Drive test cases across protocol drivers with basic scheduling."""

    def __init__(
        self,
        cfg: Optional[FrameworkConfig] = None,
        checkpoint_path: str = "checkpoints/state.json",
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self.state: Dict[str, Any] = {}
        self.cfg = cfg
        self.checkpoints = CheckpointStore(checkpoint_path)
        self._max_concurrency = self._resolve_concurrency_limit(cfg)
        self._executor = AsyncBoundedExecutor(
            max_concurrency=self._max_concurrency,
            task_timeout=(cfg.strategy.get("task_timeout") if cfg else None),
        )
        self.mutator = AdaptiveMutator()
        self._logger = logging.getLogger(__name__)
        if coloredlogs:
            coloredlogs.install(level="INFO", logger=self._logger)  # pragma: no cover

        # Initialize connection pools for memory optimization
        self._connection_pools: Dict[str, ConnectionObjectPool] = {}

        # Initialize AI anomaly detector if available
        self.anomaly_detector = None
        if AI_AVAILABLE and cfg and cfg.strategy.get("ai_enabled", False):
            try:
                self.anomaly_detector = AnomalyDetector(
                    contamination=cfg.strategy.get("anomaly_contamination", 0.1),
                    min_threshold=cfg.strategy.get("anomaly_threshold", 0.1),
                )
                self._logger.info("AI anomaly detector initialized")
            except Exception as e:
                self._logger.warning(f"Failed to initialize AI anomaly detector: {e}")
                self.anomaly_detector = None
        self.config_manager = config_manager

    def _resolve_concurrency_limit(self, cfg: Optional[FrameworkConfig]) -> int:
        """Derive a safe concurrency limit respecting config and CPU cores."""
        if cfg:
            cfg_value = cfg.strategy.get("concurrency")
            if cfg_value:
                return max(1, int(cfg_value))
        cpu_based = min(512, (os.cpu_count() or 4) * 2)
        return max(4, cpu_based)

    def _make_sync_driver(self, proto: str) -> Any:
        """Create or get a synchronous driver for the specified protocol."""
        p = proto.lower()

        # Legacy sync mode with connection pooling
        if p not in self._connection_pools:
            # Create connection pool for this protocol
            if p == "mqtt":
                factory = lambda: MqttDriver(
                    host=self.cfg.protocols.get("mqtt", {}).get("host", "localhost")
                    if self.cfg else "localhost",
                    async_mode=False
                )
            elif p == "http":
                factory = lambda: HttpDriver(
                    base_url=self.cfg.protocols.get("http", {}).get("base_url", "http://localhost")
                    if self.cfg else "http://localhost"
                )
            elif p == "modbus":
                factory = lambda: ModbusTcpDriver(
                    host=self.cfg.protocols.get("modbus", {}).get("host", "localhost")
                    if self.cfg else "localhost",
                    async_mode=False
                )
            elif p == "opcua":
                factory = lambda: OpcUaDriver(
                    endpoint=self.cfg.protocols.get("opcua", {}).get(
                        "endpoint", "opc.tcp://localhost:4840"
                    ) if self.cfg else "opc.tcp://localhost:4840"
                )
            elif p == "uart":
                factory = lambda: UartDriver(
                    port=self.cfg.protocols.get("uart", {}).get("port", "COM1")
                    if self.cfg else "COM1",
                    async_mode=False
                )
            elif p in ("i2c", "spi", "profinet"):
                params = self.cfg.protocols.get(p, {}) if self.cfg else {}
                factory = lambda: get_restartless_driver(p, params)
            else:
                raise ValueError(f"Unsupported protocol: {proto}")

            self._connection_pools[p] = ConnectionObjectPool(factory, max_size=20, timeout=300.0, cleanup_interval=60.0)

        # Acquire connection from pool
        return self._connection_pools[p].acquire()

    async def _make_async_driver(self, proto: str) -> Any:
        """Create or get an asynchronous driver for the specified protocol."""
        p = proto.lower()

        # Use async driver pool for true async I/O
        if p == "mqtt":
            kwargs = {
                "host": self.cfg.protocols.get("mqtt", {}).get("host", "localhost") if self.cfg else "localhost",
                "port": self.cfg.protocols.get("mqtt", {}).get("port", 1883) if self.cfg else 1883,
            }
        elif p == "modbus":
            kwargs = {
                "host": self.cfg.protocols.get("modbus", {}).get("host", "localhost") if self.cfg else "localhost",
                "port": self.cfg.protocols.get("modbus", {}).get("port", 502) if self.cfg else 502,
            }
        elif p == "uart":
            kwargs = {
                "port": self.cfg.protocols.get("uart", {}).get("port", "COM1") if self.cfg else "COM1",
                "baudrate": self.cfg.protocols.get("uart", {}).get("baudrate", 9600) if self.cfg else 9600,
            }
        else:
            raise ValueError(f"Async mode not supported for protocol: {proto}")

        # Return async driver from pool
        return await driver_pool.get_driver(p, **kwargs)

    async def _make_driver_async(self, proto: str, async_mode: bool = False) -> Any:
        """Create or get a driver for the specified protocol (async version)."""
        if async_mode:
            try:
                return await self._make_async_driver(proto)
            except ValueError:
                # Async mode not supported, fall back to sync mode
                return self._make_sync_driver(proto)
        else:
            # For sync mode, just call the sync version
            return self._make_sync_driver(proto)

    async def run_suite(self, protocol: str, sensor: Dict[str, Any], async_mode: bool = False) -> None:
        """Run test suite for a protocol and sensor combination."""
        # Determine sensor name for metrics and compatibility checks
        sensor_name = (
            sensor.get("name") or sensor.get("id") or sensor.get("type") or "unknown"
        )

        if self.config_manager and self.cfg:
            if not self.cfg.sensors:
                sensor_name = "unknown"
            else:
                sensor_name = (
                    sensor_name
                    if sensor_name != "unknown"
                    else next(iter(self.cfg.sensors))
                )
            self.config_manager.ensure_compatible(
                sensor_name=sensor_name, protocol=protocol, cfg=self.cfg
            )

        driver = await self._make_driver_async(protocol, async_mode)
        try:
            cases = self._build_cases(protocol, sensor)
            send_tasks = [self._dispatch_case(driver, c, protocol, sensor_name) for c in cases]
            results = await self._executor.run(send_tasks)
            self.state["last_results"] = results
            metrics.TEST_CASES_TOTAL.labels(
                protocol=protocol, sensor_type=sensor_name, category="generated"
            ).inc(len(cases))
            self.state["cases_executed"] = self.state.get("cases_executed", 0) + len(cases)

            # AI-powered anomaly analysis
            if self.anomaly_detector and results:
                try:
                    await self._analyze_with_ai(results, cases)
                except Exception as e:
                    self._logger.warning(f"AI analysis failed: {e}")

            self._save_checkpoint(None)
        finally:
            # Release connection back to pool
            self._connection_pools[protocol.lower()].release(driver)

    def _build_cases(
        self, protocol: str, sensor: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """方法说明：执行  build cases 相关逻辑。"""
        cases: List[Dict[str, Any]] = []
        # Boundary
        for c in generate_boundary_cases(sensor):
            cases.append({"payload": c, "category": "boundary"})
        # Anomalies
        for c in generate_anomaly_values(sensor):
            cases.append({"payload": c, "category": "anomaly"})
        # Protocol errors
        for err in generate_protocol_errors(protocol):
            cases.append({"payload": err, "category": "protocol_error"})
        # Signal distortion
        for d in distort_signal(sensor):
            cases.append({"payload": d, "category": "signal_distortion"})
        # POC
        for poc_task in build_poc_tasks(protocol, sensor):
            if poc_safety_ok(poc_task["poc"]):
                cases.append({"payload": poc_task, "category": "poc"})
        # Prechecks
        cases = [c for c in cases if protocol_compat_ok(sensor, protocol)]
        cases = [c for c in cases if protobuf_syntax_ok(b"ok")]
        return cases

    async def _dispatch_case(
        self, driver: Any, case: Dict[str, Any], protocol: str, sensor_name: str
    ) -> Any:
        """Send a single case through the driver with per-case observability."""
        start = asyncio.get_running_loop().time()
        result = await driver.send(case["payload"])
        duration = asyncio.get_running_loop().time() - start
        metrics.RESPONSE_TIME.labels(protocol=protocol, sensor_type=sensor_name).observe(
            duration
        )
        metrics.TEST_CASES_TOTAL.labels(
            protocol=protocol, sensor_type=sensor_name, category="executed"
        ).inc()
        return result

    def _save_checkpoint(self, last_case_id: Optional[str]) -> None:
        """方法说明：执行  save checkpoint 相关逻辑。"""
        ckpt = Checkpoint(
            cases_executed=self.state.get("cases_executed", 0),
            anomalies_found=self.state.get("anomalies", 0),
            last_case_id=last_case_id,
            metadata={"note": "auto-save"},
        )
        self.checkpoints.save(ckpt)

    def resume_from_checkpoint(self) -> None:
        """方法说明：执行 resume from checkpoint 相关逻辑。"""
        if not self.checkpoints.exists():
            return
        ckpt = self.checkpoints.load()
        self.state["resumed_from"] = ckpt
        # Restore state from checkpoint
        self.state["cases_executed"] = ckpt.cases_executed
        self.state["anomalies"] = ckpt.anomalies_found
        if ckpt.metadata:
            self.state.update(ckpt.metadata)

    async def _analyze_with_ai(
        self, results: List[Any], cases: List[Dict[str, Any]]
    ) -> None:
        """Analyze test results using AI anomaly detection."""
        if not self.anomaly_detector:
            return

        try:
            # Prepare data for AI analysis
            # Convert results to numerical features for LSTM
            import numpy as np

            features = []
            labels = []

            for i, (result, case) in enumerate(zip(results, cases)):
                # Extract features from result and case
                feature_vector = self._extract_features(result, case)
                features.append(feature_vector)

                # Determine if this is anomalous based on result
                is_anomalous = self._is_result_anomalous(result)
                labels.append(is_anomalous)

            if len(features) < 10:  # Need minimum data for training
                return

            features_array = np.array(features)
            labels_array = np.array(labels, dtype=int)

            # Train/update the detector
            if not self.anomaly_detector.is_trained:
                await self.anomaly_detector.fit_async(features_array, labels_array)
                self._logger.info("AI anomaly detector trained on initial data")
            else:
                # Online learning: update with new data
                predictions = self.anomaly_detector.predict(features_array)
                # Update detector with any new anomalies found
                new_anomalies = np.sum(predictions)
                if new_anomalies > 0:
                    self._logger.info(f"AI detected {new_anomalies} new anomalies")

            # Store AI analysis results
            self.state["ai_analysis"] = {
                "features_analyzed": len(features),
                "anomalies_detected": int(
                    np.sum(self.anomaly_detector.predict(features_array))
                ),
                "detector_trained": self.anomaly_detector.is_trained,
                "threshold": self.anomaly_detector.threshold,
            }

            # Update metrics
            metrics.ANOMALIES_DETECTED.labels(
                detection_method="ai_lstm", severity="unknown"
            ).inc(self.state["ai_analysis"]["anomalies_detected"])

        except Exception as e:
            self._logger.warning(f"AI analysis error: {e}")
            # Don't fail the entire suite due to AI issues

    def _extract_features(self, result: Any, case: Dict[str, Any]) -> List[float]:
        """Extract numerical features from test result and case for AI analysis."""
        features = []

        # Result-based features
        if isinstance(result, dict):
            features.extend(
                [
                    float(result.get("response_time", 0)),
                    float(result.get("success", 0)),
                    float(result.get("error_code", 0)),
                    len(str(result.get("response", ""))),
                ]
            )
        else:
            # Default features for non-dict results
            features.extend([0.0, 1.0, 0.0, 0.0])

        # Case-based features
        case_payload = case.get("payload", {})
        if isinstance(case_payload, dict):
            features.extend(
                [
                    len(str(case_payload)),
                    hash(str(case_payload)) % 1000 / 1000.0,  # Normalized hash
                    float(case.get("category") == "anomaly"),
                    float(case.get("category") == "boundary"),
                ]
            )
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])

        return features

    def _is_result_anomalous(self, result: Any) -> bool:
        """Determine if a test result indicates an anomaly."""
        if isinstance(result, dict):
            # Check for error indicators
            if result.get("error_code", 0) != 0:
                return True
            if not result.get("success", True):
                return True
            if (
                result.get("response_time", 0) > 10.0
            ):  # Slow responses might be anomalous
                return True
        return False

    def stop(self) -> None:
        """方法说明：执行 stop 相关逻辑。"""
        if hasattr(self, "task_runner"):
            self.task_runner.shutdown()


async def run_full(
    engine: ExecutionEngine, protocol: str, sensor: Dict[str, Any], async_mode: bool = False
) -> None:
    """异步方法说明：执行 run full 相关流程。"""
    await engine.run_suite(protocol, sensor, async_mode)
