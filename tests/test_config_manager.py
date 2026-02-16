"""模块说明：tests/test_config_manager.py 的主要实现与辅助逻辑。"""

import json
import warnings
from pathlib import Path
from typing import Any

import pytest

from sensor_fuzz.config.config_manager import ConfigManager, ConfigError

# Silence noisy ResourceWarning from SQLite drivers in tests
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.simplefilter("ignore", ResourceWarning)


def _write_config(path: Path, payload: dict[str, Any]) -> Path:
    """方法说明：执行  write config 相关逻辑。"""
    path.write_text(json.dumps(payload), encoding="utf-8") if path.suffix == ".json" else path.write_text(
        _to_yaml(payload), encoding="utf-8"
    )
    return path


def _to_yaml(payload: dict[str, Any]) -> str:
    # simple helper to avoid yaml import in tests
    """方法说明：执行  to yaml 相关逻辑。"""
    lines = ["protocols:"]
    for name, cfg in payload["protocols"].items():
        lines.append(f"  {name}:")
        for key, value in cfg.items():
            lines.append(f"    {key}: {value}")
    lines.append("sensors:")
    for name, cfg in payload["sensors"].items():
        lines.append(f"  {name}:")
        for key, value in cfg.items():
            lines.append(f"    {key}: {json.dumps(value) if isinstance(value, list) else value}")
    lines.append("strategy:")
    for key, value in payload["strategy"].items():
        lines.append(f"  {key}: {value}")
    lines.append("sil_mapping:")
    for key, value in payload["sil_mapping"].items():
        lines.append(f"  {key}:")
        for sk, sv in value.items():
            lines.append(f"    {sk}: {sv}")
    return "\n".join(lines)


def _base_payload() -> dict[str, Any]:
    """方法说明：执行  base payload 相关逻辑。"""
    return {
        "protocols": {
            "profinet": {"endpoint": "192.168.1.10", "device_name": "pn", "restartless_switch": True},
            "i2c": {"bus": 1, "address": 0x40, "restartless_switch": True},
            "spi": {"bus": 0, "device": 0, "mode": 0, "restartless_switch": True},
        },
        "sensors": {
            "temperature": {
                "type": "temperature",
                "range": [-40, 125],
                "precision": 0.1,
                "signal_type": "analog",
                "protocol": "i2c",
            },
            "pressure": {
                "type": "pressure",
                "range": [0, 10],
                "precision": 0.01,
                "signal_type": "analog",
                "protocol": "profinet",
            },
        },
        "strategy": {"anomaly_types": ["boundary"], "concurrency": 2},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }


def test_protocol_switch_and_versioning(tmp_path: Path, monkeypatch):
    """方法说明：执行 test protocol switch and versioning 相关逻辑。"""
    cfg_path = tmp_path / "config.yaml"
    payload = _base_payload()
    _write_config(cfg_path, payload)
    db_path = tmp_path / "config_version.db"
    manager = ConfigManager(cfg_path, db_path=db_path, locale="en")
    manager.load_config(author="init")
    manager._inflight_tasks = ["job-1"]

    import importlib.util

    real_find_spec = importlib.util.find_spec

    def find_spec_allow_spi(name):
        """方法说明：执行 find spec allow spi 相关逻辑。"""
        if name == "pyserial":
            return object()
        return real_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec_allow_spi)

    manager.switch_sensor_protocol(
        "temperature",
        "spi",
        author="alice",
        summary="switch to spi",
        driver_overrides={"clock_hz": 500000},
    )
    cfg = manager.current_config
    assert cfg.sensors["temperature"]["protocol"] == "spi"
    assert cfg.sensors["temperature"]["driver_params"]["clock_hz"] == 500000
    assert manager.inflight_tasks == ["job-1"]

    versions = manager.list_versions()
    assert len(versions) >= 2
    diff = manager.compare_versions(versions[-2].version, versions[-1].version)
    assert any("temperature.protocol" in line for line in diff)

    rolled = manager.rollback_version(versions[-2].version)
    assert rolled.sensors["temperature"]["protocol"] == "i2c"


def test_compatibility_helper(tmp_path: Path):
    """方法说明：执行 test compatibility helper 相关逻辑。"""
    cfg_path = tmp_path / "config.yaml"
    payload = _base_payload()
    _write_config(cfg_path, payload)
    manager = ConfigManager(cfg_path, db_path=tmp_path / "db.sqlite", locale="en")
    manager.load_config()
    # valid
    manager.ensure_compatible("temperature", "i2c")
    # invalid
    with pytest.raises(ConfigError):
        manager.ensure_compatible("temperature", "profinet")


def test_error_messages_and_locale(tmp_path: Path, monkeypatch):
    # syntax error with line number
    """方法说明：执行 test error messages and locale 相关逻辑。"""
    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text("protocols:\n  profinet: [oops\n", encoding="utf-8")
    manager = ConfigManager(bad_path, db_path=tmp_path / "db1.sqlite", locale="en")
    with pytest.raises(ConfigError) as exc:
        manager.load_config()
    assert exc.value.category == "syntax_error"
    assert "line" in str(exc.value)

    # parameter/compatibility error
    cfg_path = tmp_path / "config.yaml"
    payload = _base_payload()
    payload["sensors"]["temperature"]["protocol"] = "profinet"  # incompatible per rules
    _write_config(cfg_path, payload)
    manager = ConfigManager(cfg_path, db_path=tmp_path / "db2.sqlite", locale="zh")
    with pytest.raises(ConfigError) as exc:
        manager.load_config()
    assert exc.value.category == "parameter_error"
    assert "无法绑定协议" in str(exc.value)

    # driver dependency error during switch
    payload = _base_payload()
    payload["sensors"]["temperature"]["protocol"] = "i2c"
    cfg_path = tmp_path / "config2.yaml"
    _write_config(cfg_path, payload)
    manager = ConfigManager(cfg_path, db_path=tmp_path / "db3.sqlite", locale="zh")
    manager.load_config()

    import importlib.util

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name):
        """方法说明：执行 fake find spec 相关逻辑。"""
        if name == "pyserial":
            return None
        return real_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    with pytest.raises(ConfigError) as exc:
        manager.switch_sensor_protocol("temperature", "spi", author="qa")
    assert exc.value.category == "driver_error"
    assert "pip install pyserial" in str(exc.value)
