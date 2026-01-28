# Config Manager Quick Guide

This document shows how to manage multi-protocol sensor configs, track versions, and read error hints.

## Multi-protocol configuration
- Example config: `config/sensor_protocol_config.yaml` contains Profinet (v2.3), I2C (v1.1), SPI (v3.0) plus sensor bindings.
- Compatibility rules (built-in):
  - Temperature/Humidity: I2C or SPI
  - Pressure/Vibration: Profinet or SPI
- Switch protocol without restart:
  ```python
  from sensor_fuzz.config import ConfigManager

  manager = ConfigManager("config/sensor_protocol_config.yaml", db_path="config_version.db", locale="en")
  manager.load_config()
  manager.switch_sensor_protocol("temperature", "spi", author="qa", summary="move to spi", driver_overrides={"clock_hz": 800000})
  ```

## Version control (SQLite)
- Versions are stored in `config_version.db` with fields: version label (v1, v2...), author, timestamp, summary, config payload.
- List versions:
  ```python
  versions = manager.list_versions()
  ```
- Diff and rollback:
  ```python
  diff_lines = manager.compare_versions("v1", "v2")
  manager.rollback_version("v1", author="qa", summary="rollback to stable")
  ```

## Error messages
- Syntax errors: show line number and detail (YAML/JSON).
- Parameter errors: raised when sensor-protocol compatibility rules are violated or unknown items are referenced.
- Driver errors: raised when protocol driver dependencies are missing (e.g., `pip install pyserial`).
- Locale: set `locale="en"` or `locale="zh"` when creating `ConfigManager`; messages follow the chosen language.
