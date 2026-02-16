"""Configuration loading, validation, and SIL mapping checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema
from jsonschema import ValidationError
import yaml

from sensor_fuzz.config.schema import DEFAULT_SCHEMA


@dataclass
class FrameworkConfig:
    """In-memory representation of the framework configuration."""

    protocols: Dict[str, Any]
    sensors: Dict[str, Any]
    strategy: Dict[str, Any]
    sil_mapping: Dict[str, Any]


class ConfigLoader:
    """Load and validate configuration files (YAML/JSON)."""

    def __init__(self, schema: Optional[Dict[str, Any]] = None) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._schema = schema or DEFAULT_SCHEMA

    def load(self, path: str | Path) -> FrameworkConfig:
        """Load and validate configuration from file with caching."""
        path = Path(path)
        mtime = path.stat().st_mtime
        cache_key = f"{path}:{mtime}"

        return self._load_cached(cache_key, str(path))

    @lru_cache(maxsize=16)
    def _load_cached(self, cache_key: str, path_str: str) -> FrameworkConfig:
        """Cached configuration loading."""
        path = Path(path_str)
        suffix = path.suffix.lower()
        if suffix not in {".json", ".yml", ".yaml"}:
            raise ValueError(f"Unsupported config format for {path}: {suffix}")
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise ValueError(f"Failed to read config {path}: {exc}") from exc

        try:
            data = (
                yaml.safe_load(content)
                if suffix in (".yml", ".yaml")
                else json.loads(content)
            )
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ValueError(f"Failed to parse config {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Config root must be an object in {path}")

        if self._schema:
            try:
                jsonschema.validate(data, self._schema)
            except (
                ValidationError
            ) as exc:  # surface schema errors as ValueError for caller expectations
                raise ValueError(str(exc)) from exc
        self._validate_sil_mapping(data.get("sil_mapping", {}))
        protocols = data.get("protocols", {})
        self._validate_protocols(protocols)
        self._validate_sensors(data.get("sensors", {}), protocols)
        return FrameworkConfig(
            protocols=protocols,
            sensors=data.get("sensors", {}),
            strategy=data.get("strategy", {}),
            sil_mapping=data.get("sil_mapping", {}),
        )

    def dump(self, config: FrameworkConfig, path: str | Path) -> None:
        """方法说明：执行 dump 相关逻辑。"""
        payload = {
            "protocols": config.protocols,
            "sensors": config.sensors,
            "strategy": config.strategy,
            "sil_mapping": config.sil_mapping,
        }
        target = Path(path)
        if target.suffix.lower() in {".yml", ".yaml"}:
            target.write_text(
                yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
            )
        else:
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def with_sil_mapping(
        self, config: FrameworkConfig, sil_mapping: Dict[str, Any]
    ) -> FrameworkConfig:
        """Return a new config with updated SIL mapping after validation."""
        self._validate_sil_mapping(sil_mapping)
        return FrameworkConfig(
            protocols=config.protocols,
            sensors=config.sensors,
            strategy=config.strategy,
            sil_mapping=sil_mapping,
        )

    @staticmethod
    def _validate_sil_mapping(sil_mapping: Dict[str, Any]) -> None:
        """方法说明：执行  validate sil mapping 相关逻辑。"""
        for level, cfg in sil_mapping.items():
            if not level.startswith("SIL"):
                raise ValueError(f"Invalid SIL level key: {level}")
            coverage = cfg.get("coverage")
            if coverage is None or not (0.9 <= float(coverage) <= 1.0):
                raise ValueError(f"SIL coverage out of range for {level}: {coverage}")
            # Optional thresholds
            fp = cfg.get("max_false_positive")
            if fp is not None and not (0 <= float(fp) <= 0.05):
                raise ValueError(
                    f"SIL false positive threshold out of range for {level}: {fp}"
                )

    @staticmethod
    def _validate_protocols(protocols: Dict[str, Any]) -> None:
        # Ensure restartless switch flags are boolean when provided
        """方法说明：执行  validate protocols 相关逻辑。"""
        for name in ("profinet", "i2c", "spi"):
            cfg = protocols.get(name)
            if cfg is None:
                continue
            flag = cfg.get("restartless_switch")
            if flag is not None and not isinstance(flag, bool):
                raise ValueError(
                    f"Protocol {name} restartless_switch must be boolean, got {flag!r}"
                )

        # Basic sanity for I2C/SPI bus/device numbers
        i2c_cfg = protocols.get("i2c") or {}
        if "bus" in i2c_cfg and int(i2c_cfg["bus"]) < 0:
            raise ValueError("I2C bus index must be non-negative")
        if "address" in i2c_cfg and int(i2c_cfg["address"]) < 0:
            raise ValueError("I2C address must be non-negative")

        spi_cfg = protocols.get("spi") or {}
        if "bus" in spi_cfg and int(spi_cfg["bus"]) < 0:
            raise ValueError("SPI bus must be non-negative")
        if "device" in spi_cfg and int(spi_cfg["device"]) < 0:
            raise ValueError("SPI device must be non-negative")
        if "mode" in spi_cfg:
            mode = int(spi_cfg["mode"])
            if mode < 0 or mode > 3:
                raise ValueError("SPI mode must be 0-3")

    @staticmethod
    def _validate_sensors(sensors: Dict[str, Any], protocols: Dict[str, Any]) -> None:
        """方法说明：执行  validate sensors 相关逻辑。"""
        for name, cfg in sensors.items():
            protocol = cfg.get("protocol")
            if protocol and protocol not in protocols:
                raise ValueError(
                    f"Sensor {name} references unknown protocol {protocol}"
                )
            restartless = cfg.get("restartless_switch")
            if restartless is not None and not isinstance(restartless, bool):
                raise ValueError(
                    f"Sensor {name} restartless_switch must be boolean, "
                    f"got {restartless!r}"
                )


class ConfigSnapshot:
    """Serializable snapshot of configuration with metadata."""

    def __init__(self, config: FrameworkConfig, path: Path) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self.config = config
        self.path = path
        self.loaded_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """方法说明：执行 to dict 相关逻辑。"""
        return {
            "path": str(self.path),
            "loaded_at": self.loaded_at.isoformat() + "Z",
            "protocols": self.config.protocols,
            "sensors": self.config.sensors,
            "strategy": self.config.strategy,
            "sil_mapping": self.config.sil_mapping,
        }
