"""模块说明：tests/test_config_loader.py 的主要实现与辅助逻辑。"""

import json
import time
from pathlib import Path

import pytest

from sensor_fuzz.config import ConfigLoader, DEFAULT_SCHEMA, ConfigVersionStore, ConfigReloader


def test_load_yaml(tmp_path: Path):
    """方法说明：执行 test load yaml 相关逻辑。"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
protocols:
  mqtt:
    host: localhost
    port: 1883
    version: 5.0
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
    loader = ConfigLoader(DEFAULT_SCHEMA)
    cfg = loader.load(config_path)
    assert cfg.protocols["mqtt"]["port"] == 1883
    assert cfg.sensors["temperature"]["range"] == [0, 100]
    assert cfg.sil_mapping["SIL1"]["coverage"] == 0.95


def test_sil_validation_bounds(tmp_path: Path):
    """方法说明：执行 test sil validation bounds 相关逻辑。"""
    config_path = tmp_path / "config.json"
    payload = {
        "protocols": {},
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.5}},
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_protocol_restartless_flag_validation(tmp_path: Path):
    """方法说明：执行 test protocol restartless flag validation 相关逻辑。"""
    config_path = tmp_path / "cfg.json"
    payload = {
        "protocols": {
            "i2c": {"bus": 1, "address": 32, "restartless_switch": "yes"},
        },
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_i2c_negative_bus_and_spi_mode(tmp_path: Path):
    """方法说明：执行 test i2c negative bus and spi mode 相关逻辑。"""
    config_path = tmp_path / "cfg.json"
    payload = {
        "protocols": {
            "i2c": {"bus": -1, "address": 32},
            "spi": {"bus": 0, "device": 0, "mode": 4},
        },
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_sensor_restartless_flag_type(tmp_path: Path):
    """方法说明：执行 test sensor restartless flag type 相关逻辑。"""
    config_path = tmp_path / "cfg.json"
    payload = {
        "protocols": {"i2c": {"bus": 1, "address": 32}},
        "sensors": {"temp": {"range": [0, 1], "precision": 0.1, "signal_type": "analog", "protocol": "i2c", "restartless_switch": "x"}},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_sil_false_positive_range(tmp_path: Path):
    """方法说明：执行 test sil false positive range 相关逻辑。"""
    config_path = tmp_path / "cfg.json"
    payload = {
        "protocols": {},
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.96, "max_false_positive": 0.2}},
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_config_dump_roundtrip(tmp_path: Path):
    """方法说明：执行 test config dump roundtrip 相关逻辑。"""
    loader = ConfigLoader(DEFAULT_SCHEMA)
    payload = {
        "protocols": {"i2c": {"bus": 1, "address": 32}},
        "sensors": {"temp": {"range": [0, 1], "precision": 0.1, "signal_type": "analog", "protocol": "i2c"}},
        "strategy": {"anomaly_types": ["boundary"]},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    config_path = tmp_path / "cfg.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    cfg = loader.load(config_path)
    out_path = tmp_path / "out.json"
    loader.dump(cfg, out_path)
    reloaded = loader.load(out_path)
    assert reloaded.protocols["i2c"]["address"] == 32


def test_sensor_unknown_protocol(tmp_path: Path):
    """方法说明：执行 test sensor unknown protocol 相关逻辑。"""
    config_path = tmp_path / "cfg.json"
    payload = {
        "protocols": {"i2c": {"bus": 1, "address": 32}},
        "sensors": {"temp": {"range": [0, 100], "precision": 0.1, "signal_type": "analog", "protocol": "spi"}},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_invalid_extension(tmp_path: Path):
    """方法说明：执行 test invalid extension 相关逻辑。"""
    config_path = tmp_path / "config.txt"
    config_path.write_text("{}", encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_read_error(monkeypatch, tmp_path: Path):
    """方法说明：执行 test read error 相关逻辑。"""
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)

    def _boom(*_, **__):
        """方法说明：执行  boom 相关逻辑。"""
        raise OSError("disk error")

    monkeypatch.setattr(Path, "read_text", _boom)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_parse_error(tmp_path: Path):
    """方法说明：执行 test parse error 相关逻辑。"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("::notyaml::", encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_root_not_object(tmp_path: Path):
    """方法说明：执行 test root not object 相关逻辑。"""
    config_path = tmp_path / "config.json"
    config_path.write_text("[]", encoding="utf-8")
    loader = ConfigLoader(DEFAULT_SCHEMA)
    with pytest.raises(ValueError):
        loader.load(config_path)


def test_version_store(tmp_path: Path):
    """方法说明：执行 test version store 相关逻辑。"""
    store = ConfigVersionStore(tmp_path)
    loader = ConfigLoader(DEFAULT_SCHEMA)
    payload = {
        "protocols": {},
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    cfg = loader.load(_write(tmp_path / "cfg.yml", payload))
    saved = store.save("unit", cfg)
    versions = store.list_versions()
    assert saved in versions
    loaded = store.load(saved)
    assert loaded["sil_mapping"]["SIL1"]["coverage"] == 0.95
    assert store.latest() == saved
    rolled = store.rollback_latest()
    assert rolled["sil_mapping"]["SIL1"]["coverage"] == 0.95


def test_version_store_prune_and_latest_none(tmp_path: Path):
    """方法说明：执行 test version store prune and latest none 相关逻辑。"""
    store = ConfigVersionStore(tmp_path, retain=1)
    loader = ConfigLoader(DEFAULT_SCHEMA)
    payload = {
        "protocols": {},
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    cfg = loader.load(_write(tmp_path / "cfg1.yml", payload))
    first = store.save("unit1", cfg)
    cfg2 = loader.load(_write(tmp_path / "cfg2.yml", payload))
    second = store.save("unit2", cfg2)
    versions = store.list_versions()
    assert second in versions
    assert first not in versions  # pruned
    empty_store = ConfigVersionStore(tmp_path / "empty", retain=1)
    assert empty_store.rollback_latest() is None


def test_version_store_retain_zero_keeps_all(tmp_path: Path):
    """方法说明：执行 test version store retain zero keeps all 相关逻辑。"""
    store = ConfigVersionStore(tmp_path, retain=0)
    loader = ConfigLoader(DEFAULT_SCHEMA)
    payload = {
        "protocols": {},
        "sensors": {},
        "strategy": {},
        "sil_mapping": {"SIL1": {"coverage": 0.95}},
    }
    cfg = loader.load(_write(tmp_path / "cfg1.yml", payload))
    first = store.save("unit1", cfg)
    cfg2 = loader.load(_write(tmp_path / "cfg2.yml", payload))
    second = store.save("unit2", cfg2)
    versions = store.list_versions()
    assert {first, second}.issubset(set(versions))


def test_version_store_load_error(tmp_path: Path):
    """方法说明：执行 test version store load error 相关逻辑。"""
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{notjson}", encoding="utf-8")
    store = ConfigVersionStore(tmp_path)
    with pytest.raises(ValueError):
        store.load(bad_file)


def test_reloader_reload_and_override(tmp_path: Path):
    """方法说明：执行 test reloader reload and override 相关逻辑。"""
    config_path = tmp_path / "cfg.yml"
    config_path.write_text(
        """
protocols: {}
sensors: {}
strategy: {}
sil_mapping:
  SIL1:
    coverage: 0.95
        """,
        encoding="utf-8",
    )
    snapshots = []
    errors = []

    def on_reload(snapshot):
        """方法说明：执行 on reload 相关逻辑。"""
        snapshots.append(snapshot)

    def on_error(exc):
        """方法说明：执行 on error 相关逻辑。"""
        errors.append(exc)

    reloader = ConfigReloader(
        config_path,
        on_reload=on_reload,
        interval_sec=0.05,
        on_error=on_error,
        sil_mapping_override={"SIL1": {"coverage": 0.99}},
    )
    reloader.start()
    assert _wait(lambda: len(snapshots) >= 1)

    config_path.write_text(
        """
protocols: {}
sensors: {}
strategy: {}
sil_mapping:
  SIL1:
    coverage: 0.96
        """,
        encoding="utf-8",
    )
    assert _wait(lambda: len(snapshots) >= 2)
    reloader.update_sil_override({"SIL1": {"coverage": 0.97}})
    assert _wait(lambda: len(snapshots) >= 3)
    reloader.stop()

    assert errors == []
    # override applied on reload and on update
    assert snapshots[-2].config.sil_mapping["SIL1"]["coverage"] == 0.99
    assert snapshots[-1].config.sil_mapping["SIL1"]["coverage"] == 0.97


def test_reloader_error_callback_on_bad_config(tmp_path: Path):
    """方法说明：执行 test reloader error callback on bad config 相关逻辑。"""
    config_path = tmp_path / "cfg.yml"
    config_path.write_text(
        """
protocols: {}
sensors: {}
strategy: {}
sil_mapping:
  SIL1:
    coverage: 0.50
        """,
        encoding="utf-8",
    )
    errors = []

    def on_reload(snapshot):
        """方法说明：执行 on reload 相关逻辑。"""
        pass

    def on_error(exc):
        """方法说明：执行 on error 相关逻辑。"""
        errors.append(exc)

    reloader = ConfigReloader(config_path, on_reload=on_reload, interval_sec=0.05, on_error=on_error)
    reloader.start()
    assert _wait(lambda: len(errors) >= 1)
    # Second start should be a no-op
    reloader.start()
    reloader.stop()
    assert isinstance(errors[0], ValueError)


def _write(path: Path, payload: dict) -> Path:
    """方法说明：执行  write 相关逻辑。"""
    if path.suffix in {".yml", ".yaml"}:
        path.write_text(
            """
protocols: {}
sensors: {}
strategy: {}
sil_mapping:
  SIL1:
    coverage: 0.95
            """,
            encoding="utf-8",
        )
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _wait(predicate, timeout: float = 1.0):
    """方法说明：执行  wait 相关逻辑。"""
    start = time.time()
    while time.time() - start < timeout:
        if predicate():
            return True
        time.sleep(0.05)
    return False
