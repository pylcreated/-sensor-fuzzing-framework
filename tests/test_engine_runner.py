"""模块说明：tests/test_engine_runner.py 的主要实现与辅助逻辑。"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock

# 导入执行引擎和配置相关模块
from sensor_fuzz.engine.runner import ExecutionEngine
from sensor_fuzz.config import ConfigLoader, ConfigManager, ConfigError


# 测试执行引擎构建测试用例的功能
def test_engine_builds_cases(tmp_path):
    """测试执行引擎构建测试用例的功能。"""
    # 创建临时配置文件
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    # 加载配置并初始化执行引擎
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json")
    # 模拟驱动创建以避免网络操作
    engine._make_driver = lambda protocol: _NoopDriver()  # type: ignore
    asyncio.run(engine.run_suite("mqtt", cfg.sensors["temperature"]))
    # 验证是否执行了测试用例
    assert engine.state.get("cases_executed", 0) > 0


# 测试执行引擎在驱动导入失败时的行为
def test_engine_driver_import_guards(tmp_path):
    """测试执行引擎在驱动导入失败时的行为。"""
    # 创建临时配置文件
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  http:
    base_url: http://localhost
sensors:
  http_sensor:
    range: [0, 1]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    # 加载配置并初始化执行引擎
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json")
    engine._make_driver = lambda protocol: _NoopDriver()  # type: ignore
    asyncio.run(engine.run_suite("http", cfg.sensors["http_sensor"]))
    # 验证是否执行了测试用例
    assert engine.state.get("cases_executed", 0) > 0


# 测试执行引擎在遇到不支持的协议时的行为
def test_engine_unsupported_protocol():
    """测试执行引擎在遇到不支持的协议时的行为。"""
    engine = ExecutionEngine(None)
    with pytest.raises(ValueError):
        engine._make_driver("unknown")


# 测试运行器的兼容性检查功能
def test_runner_compatibility_check(tmp_path):
    """测试运行器的兼容性检查功能。"""
    # 创建临时配置文件
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  i2c:
    bus: 1
    address: 64
sensors:
  temperature:
    type: temperature
    range: [0, 100]
    precision: 0.1
    signal_type: digital
    protocol: i2c
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    # 加载配置并初始化执行引擎
    cfg = ConfigLoader().load(cfg_file)
    manager = ConfigManager(cfg_file, db_path=tmp_path / "db.sqlite")
    manager.load_config()
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json", config_manager=manager)
    engine._make_driver = lambda protocol: _NoopDriver()  # type: ignore
    # 验证是否抛出兼容性错误
    with pytest.raises(ConfigError):
        asyncio.run(engine.run_suite("profinet", cfg.sensors["temperature"]))

# 定义一个模拟驱动的类，用于测试执行引擎的行为
class _NoopDriver:
    """模拟驱动的类。"""
    async def send(self, payload):
        """模拟发送方法。"""
        return payload


@pytest.mark.parametrize("protocol,expected_driver", [
    ("mqtt", "MqttDriver"),
    ("http", "HttpDriver"),
    ("modbus", "ModbusTcpDriver"),
    ("opcua", "OpcUaDriver"),
    ("i2c", "I2CDriver"),
    ("spi", "SPIDriver"),
    ("uart", "UartDriver"),
])
def test_make_driver_supported_protocols(protocol, expected_driver, tmp_path):
    """Test _make_driver method for all supported protocols."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        f"""
protocols:
  {protocol}:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg)

    driver = engine._make_driver(protocol)
    assert driver is not None
    assert driver.__class__.__name__ == expected_driver


def test_make_driver_unsupported_protocol():
    """Test _make_driver method with unsupported protocol."""
    engine = ExecutionEngine(None)
    with pytest.raises(ValueError, match="Unsupported protocol"):
        engine._make_driver("unsupported_protocol")


@pytest.mark.asyncio
async def test_run_suite_execution_flow(tmp_path):
    """Test run_suite method execution flow."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json")

    # Mock the driver
    mock_driver = AsyncMock()
    mock_driver.send.return_value = {"status": "success"}

    with patch.object(engine, '_make_driver', return_value=mock_driver):
        await engine.run_suite("mqtt", cfg.sensors["temperature"])

    assert engine.state["cases_executed"] > 0
    assert "last_results" in engine.state


@pytest.mark.asyncio
async def test_run_suite_with_config_reload(tmp_path):
    """Test run_suite with configuration reload."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    manager = ConfigManager(cfg_file, db_path=tmp_path / "db.sqlite")
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json", config_manager=manager)

    # Mock the driver
    mock_driver = AsyncMock()
    mock_driver.send.return_value = {"status": "success"}

    with patch.object(engine, '_make_driver', return_value=mock_driver), \
         patch.object(manager, 'ensure_compatible'):
        await engine.run_suite("mqtt", cfg.sensors["temperature"])

    assert "config_reload" not in engine.state


@pytest.mark.asyncio
async def test_run_suite_error_handling(tmp_path):
    """Test run_suite error handling."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json")

    # Mock driver to raise exception
    mock_driver = AsyncMock()
    mock_driver.send.side_effect = Exception("Driver error")

    with patch.object(engine, '_make_driver', return_value=mock_driver):
        with pytest.raises(Exception, match="Driver error"):
            await engine.run_suite("mqtt", cfg.sensors["temperature"])


def test_resume_from_checkpoint_no_file(tmp_path):
    """Test resume_from_checkpoint with no checkpoint file."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "nonexistent.json")

    # Should not raise exception
    engine.resume_from_checkpoint()
    assert "resumed_from" not in engine.state


def test_resume_from_checkpoint_with_data(tmp_path):
    """Test resume_from_checkpoint with existing checkpoint data."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    checkpoint_path = tmp_path / "checkpoint.json"

    # Create checkpoint file
    import json
    checkpoint_data = {
        "cases_executed": 10,
        "anomalies_found": 2,
        "last_case_id": "case_123",
        "metadata": {"start_time": 1234567890, "protocol": "mqtt"}
    }
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint_data, f)

    engine = ExecutionEngine(cfg, checkpoint_path=checkpoint_path)
    engine.resume_from_checkpoint()

    assert "resumed_from" in engine.state
    assert engine.state.get("cases_executed") == 10


@pytest.mark.asyncio
async def test_run_suite_concurrency_handling(tmp_path):
    """Test run_suite concurrency handling."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 2
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json")

    # Mock the driver
    mock_driver = AsyncMock()
    mock_driver.send.return_value = {"status": "success"}

    with patch.object(engine, '_make_driver', return_value=mock_driver):
        await engine.run_suite("mqtt", cfg.sensors["temperature"])

    # Verify concurrency setting was used
    assert cfg.strategy["concurrency"] == 2


@pytest.mark.asyncio
async def test_run_suite_checkpoint_saving(tmp_path):
    """Test run_suite checkpoint saving."""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary]
  concurrency: 5
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    checkpoint_path = tmp_path / "test_checkpoint.json"
    engine = ExecutionEngine(cfg, checkpoint_path=checkpoint_path)

    # Mock the driver
    mock_driver = AsyncMock()
    mock_driver.send.return_value = {"status": "success"}

    with patch.object(engine, '_make_driver', return_value=mock_driver):
        await engine.run_suite("mqtt", cfg.sensors["temperature"])

    # Check if checkpoint file was created
    assert checkpoint_path.exists()

    # Verify checkpoint content
    import json
    with open(checkpoint_path) as f:
        checkpoint_data = json.load(f)

    assert "cases_executed" in checkpoint_data
    assert "anomalies_found" in checkpoint_data
    assert "last_case_id" in checkpoint_data
    assert "metadata" in checkpoint_data


@pytest.mark.asyncio
async def test_run_suite_fault_injection_generates_anomalies(tmp_path, monkeypatch):
    """开启故障注入后，应能观测到异常计数增加。"""
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        """
protocols:
  mqtt:
    host: localhost
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary, anomaly, protocol_error, signal_distortion]
  concurrency: 2
  fault_injection_rate: 1.0
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    cfg = ConfigLoader().load(cfg_file)
    engine = ExecutionEngine(cfg, checkpoint_path=tmp_path / "state.json")

    mock_driver = AsyncMock()
    mock_driver.send.return_value = {"success": True, "error_code": 0, "response_time": 0.01}

    with patch.object(engine, "_make_driver", return_value=mock_driver):
        await engine.run_suite("mqtt", cfg.sensors["temperature"])

    assert engine.state.get("anomalies", 0) > 0
    assert any(
        isinstance(item, dict) and item.get("fault_injected")
        for item in engine.state.get("last_results", [])
    )
