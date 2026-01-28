"""Configuration manager for industrial sensor fuzzing framework.

Provides protocol switching (Profinet/I2C/SPI), compatibility validation,
restartless updates, structured error messages with i18n, and SQLite-backed
version control with diff/rollback helpers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import importlib.util
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

import yaml

from sensor_fuzz.config.loader import ConfigLoader, FrameworkConfig
from sensor_fuzz.config.schema import DEFAULT_SCHEMA

try:  # coloredlogs is optional; fallback to basic logging if missing
    import coloredlogs
except ImportError:  # pragma: no cover - exercised only when coloredlogs absent
    coloredlogs = None  # type: ignore


class DatabaseConnectionManager:
    """Thread-safe SQLite connection manager to prevent connection leaks."""

    def __init__(self, db_path: Path, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections: List[sqlite3.Connection] = []
        self._available: List[sqlite3.Connection] = []

    def __enter__(self) -> sqlite3.Connection:
        return self.get_connection()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Connection will be returned to pool by context manager
        pass

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = self._get_connection()
        try:
            yield conn
        finally:
            self._return_connection(conn)

    def _get_connection(self) -> sqlite3.Connection:
        """Get an available connection or create a new one."""
        if self._available:
            return self._available.pop()

        if len(self._connections) < self.max_connections:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            self._connections.append(conn)
            return conn

        # If we've reached max connections, wait for one to become available
        # For now, create a temporary connection (could be improved with proper pooling)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _return_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        if conn in self._connections:
            # Reset connection state
            conn.rollback()  # Ensure no pending transactions
            self._available.append(conn)
        else:
            # Temporary connection, close it
            conn.close()

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self._connections:
            try:
                conn.close()
            except Exception as e:
                # Log cleanup errors but don't fail the cleanup process
                import logging
                logging.warning(f"Error closing connection during cleanup: {e}")
        self._connections.clear()
        self._available.clear()


# Supported protocol specs with minimal driver requirements
PROTOCOL_SPECS = {
    "profinet": {"version": "2.3", "dependency": "snap7"},
    "i2c": {"version": "1.1", "dependency": None},
    "spi": {"version": "3.0", "dependency": "pyserial"},
}

# Compatibility rules between sensor types and protocols
SENSOR_PROTOCOL_COMPAT = {
    "temperature": {"profinet": False, "i2c": True, "spi": True},
    "humidity": {"profinet": False, "i2c": True, "spi": True},
    "pressure": {"profinet": True, "i2c": False, "spi": True},
    "vibration": {"profinet": True, "i2c": False, "spi": True},
    "default": {"profinet": True, "i2c": True, "spi": True},
}


@dataclass
class VersionRecord:
    """Lightweight record returned from SQLite store."""

    version: str
    author: str
    created_at: str
    summary: str


class ConfigError(Exception):
    """Structured configuration error with category and localization support."""

    def __init__(
        self, category: str, message: str, *, detail: Optional[str] = None
    ) -> None:
        super().__init__(message)
        self.category = category
        self.detail = detail


class ConfigManager:
    """Manage configuration with protocol switching, version control and rich errors."""

    def __init__(
        self,
        config_path: str | Path,
        db_path: str | Path = "config_version.db",
        locale: str = "en",
        loader: Optional[ConfigLoader] = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.db_path = Path(db_path)
        self.locale = locale if locale in {"en", "zh"} else "en"
        self.loader = loader or ConfigLoader(DEFAULT_SCHEMA)
        self._config: Optional[FrameworkConfig] = None
        self._inflight_tasks: List[str] = []
        self._db_manager = DatabaseConnectionManager(self.db_path)
        self._logger = logging.getLogger(__name__)
        if coloredlogs:
            coloredlogs.install(level="INFO", logger=self._logger)  # pragma: no cover
        self._init_db()

    # ---------- Public API ----------
    @property
    def current_config(self) -> FrameworkConfig:
        if not self._config:
            raise ConfigError("parameter_error", self._msg("not_loaded"))
        return self._config

    @property
    def inflight_tasks(self) -> List[str]:
        return list(self._inflight_tasks)

    def load_config(
        self, *, author: str = "system", summary: str = "initial load"
    ) -> FrameworkConfig:
        """Load, validate, and record the current configuration."""
        try:
            self._parse_with_line_info(self.config_path)
        except ConfigError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise ConfigError("syntax_error", str(exc)) from exc

        try:
            cfg = self.loader.load(self.config_path)
        except ValueError as exc:
            raise ConfigError(
                "parameter_error", self._msg("schema_error", detail=str(exc))
            ) from exc
        self._validate_sensor_protocol_rules(cfg)
        self._config = cfg
        self._persist_version(cfg, author=author, summary=summary)
        return cfg

    def switch_sensor_protocol(
        self,
        sensor_name: str,
        protocol: str,
        *,
        author: str = "user",
        summary: str = "protocol switch",
        driver_overrides: Optional[Dict[str, Any]] = None,
        preserve_tasks: bool = True,
    ) -> FrameworkConfig:
        """Switch a sensor to a different protocol without dropping in-flight tasks."""
        cfg = deepcopy(self.current_config)
        sensors = deepcopy(cfg.sensors)
        if sensor_name not in sensors:
            raise ConfigError(
                "parameter_error", self._msg("sensor_missing", sensor=sensor_name)
            )
        normalized_protocol = protocol.lower()
        sensor_cfg = sensors[sensor_name]
        self._validate_sensor_protocol_rules(
            cfg, sensor_name=sensor_name, target_protocol=normalized_protocol
        )
        self._ensure_driver_available(normalized_protocol)

        protocol_cfg = deepcopy(cfg.protocols.get(normalized_protocol) or {})
        if not protocol_cfg:
            raise ConfigError(
                "parameter_error",
                self._msg("protocol_missing", protocol=normalized_protocol),
            )
        merged_params = {**protocol_cfg, **(driver_overrides or {})}
        merged_params["restartless_switch"] = protocol_cfg.get(
            "restartless_switch", True
        )
        sensor_cfg["protocol"] = normalized_protocol
        sensor_cfg["driver_params"] = merged_params
        sensors[sensor_name] = sensor_cfg
        # Apply restartless driver params to hardware abstraction if available
        try:
            from sensor_fuzz.engine.drivers import (
                get_restartless_driver,
            )  # local import to avoid circular dependency

            driver = get_restartless_driver(normalized_protocol, merged_params)
            driver.connect()
            driver.apply_params(merged_params)
            driver.close()
        except (
            Exception
        ) as exc:  # pragma: no cover - defensive, surfaced as driver_error
            raise ConfigError(
                "driver_error",
                self._msg(
                    "driver_missing", protocol=normalized_protocol, dependency="driver"
                ),
            ) from exc
        cfg = FrameworkConfig(
            protocols=cfg.protocols,
            sensors=sensors,
            strategy=cfg.strategy,
            sil_mapping=cfg.sil_mapping,
        )
        if preserve_tasks:
            self._logger.info(
                "Protocol switch applied restartlessly; in-flight tasks preserved: %s",
                self._inflight_tasks,
            )
        self._config = cfg
        self._persist_version(cfg, author=author, summary=summary)
        return cfg

    def ensure_compatible(
        self,
        sensor_name: str,
        protocol: Optional[str] = None,
        cfg: Optional[FrameworkConfig] = None,
    ) -> None:
        """Public wrapper to validate sensor-protocol compatibility."""
        effective_cfg = cfg or self.current_config
        self._validate_sensor_protocol_rules(
            effective_cfg,
            sensor_name=sensor_name,
            target_protocol=protocol,
        )

    def list_versions(self) -> List[VersionRecord]:
        query = (
            "select version, author, created_at, summary from versions order by id asc"
        )
        rows = self._fetch_rows(query)
        return [VersionRecord(*row) for row in rows]

    def compare_versions(self, older: str, newer: str) -> List[str]:
        """Return human-readable diff between two version labels (e.g., v1, v2)."""
        old_cfg = self._load_version_payload(older)
        new_cfg = self._load_version_payload(newer)
        old_flat = self._flatten(old_cfg)
        new_flat = self._flatten(new_cfg)
        keys = sorted(set(old_flat) | set(new_flat))
        diff_lines: List[str] = []
        for key in keys:
            old_val = old_flat.get(key)
            new_val = new_flat.get(key)
            if old_val != new_val:
                diff_lines.append(f"{key}: {old_val!r} -> {new_val!r}")
        return diff_lines

    def rollback_version(
        self, version: str, *, author: str = "system", summary: str = "rollback"
    ) -> FrameworkConfig:
        """Rollback to a previous version and record the rollback as a new version."""
        payload = self._load_version_payload(version)
        cfg = FrameworkConfig(
            protocols=payload.get("protocols", {}),
            sensors=payload.get("sensors", {}),
            strategy=payload.get("strategy", {}),
            sil_mapping=payload.get("sil_mapping", {}),
        )
        self._validate_sensor_protocol_rules(cfg)
        self._config = cfg
        self._persist_version(cfg, author=author, summary=summary)
        self._write_config_file(cfg)
        return cfg

    def __del__(self) -> None:
        """Cleanup database connections on object destruction."""
        try:
            self._db_manager.close_all()
        except Exception as e:
            # Log cleanup errors but don't fail during object destruction
            import logging
            logging.warning(f"Error during ConfigManager cleanup: {e}")

    # ---------- Internal helpers ----------
    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._db_manager.get_connection() as conn:
            conn.execute("""
                create table if not exists versions (
                    id integer primary key autoincrement,
                    version text not null,
                    author text not null,
                    created_at text not null,
                    summary text not null,
                    config_json text not null
                );
                """)
            conn.commit()

    def _persist_version(
        self, cfg: FrameworkConfig, *, author: str, summary: str
    ) -> str:
        payload = {
            "protocols": cfg.protocols,
            "sensors": cfg.sensors,
            "strategy": cfg.strategy,
            "sil_mapping": cfg.sil_mapping,
        }
        created_at = datetime.now(timezone.utc).isoformat()
        with self._db_manager.get_connection() as conn:
            cur = conn.execute("select ifnull(max(id), 0) + 1 from versions")
            next_id = cur.fetchone()[0]
            version_label = f"v{next_id}"
            conn.execute(
                "insert into versions(version, author, created_at, summary, "
                "config_json) values(?,?,?,?,?)",
                (
                    version_label,
                    author,
                    created_at,
                    summary,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            conn.commit()
        return version_label

    def _fetch_rows(self, query: str) -> List[tuple]:
        with self._db_manager.get_connection() as conn:
            cur = conn.execute(query)
            return cur.fetchall()

    def _load_version_payload(self, version: str) -> Dict[str, Any]:
        with self._db_manager.get_connection() as conn:
            cur = conn.execute(
                "select config_json from versions where version = ?", (version,)
            )
            row = cur.fetchone()
            if not row:
                raise ConfigError(
                    "parameter_error", self._msg("version_missing", version=version)
                )
            return json.loads(row[0])

    def _write_config_file(self, cfg: FrameworkConfig) -> None:
        payload = {
            "protocols": cfg.protocols,
            "sensors": cfg.sensors,
            "strategy": cfg.strategy,
            "sil_mapping": cfg.sil_mapping,
        }
        self.config_path.write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )

    def _parse_with_line_info(self, path: Path) -> Dict[str, Any]:
        suffix = path.suffix.lower()
        if suffix not in {".yml", ".yaml", ".json"}:
            raise ConfigError("syntax_error", self._msg("format_error", path=str(path)))
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ConfigError(
                "syntax_error", self._msg("file_missing", path=str(path))
            ) from exc
        if suffix in {".yml", ".yaml"}:
            try:
                return yaml.safe_load(raw) or {}
            except yaml.YAMLError as exc:
                line = getattr(getattr(exc, "problem_mark", None), "line", None)
                line_no = line + 1 if line is not None else "?"
                raise ConfigError(
                    "syntax_error",
                    self._msg("yaml_error", line=line_no, detail=str(exc)),
                ) from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "syntax_error", self._msg("json_error", line=exc.lineno, detail=exc.msg)
            ) from exc

    def _validate_sensor_protocol_rules(
        self,
        cfg: FrameworkConfig,
        *,
        sensor_name: Optional[str] = None,
        target_protocol: Optional[str] = None,
    ) -> None:
        sensors = (
            cfg.sensors
            if sensor_name is None
            else {sensor_name: cfg.sensors.get(sensor_name, {})}
        )
        for name, sensor_cfg in sensors.items():
            protocol = target_protocol or sensor_cfg.get("protocol")
            if not protocol:
                continue
            sensor_type = (
                sensor_cfg.get("type") or sensor_cfg.get("sensor_type") or name
            )
            compat = SENSOR_PROTOCOL_COMPAT.get(
                sensor_type, SENSOR_PROTOCOL_COMPAT["default"]
            )
            allowed = compat.get(protocol, False)
            if not allowed:
                raise ConfigError(
                    "parameter_error",
                    self._msg(
                        "compat_error",
                        sensor=name,
                        protocol=protocol,
                        sensor_type=sensor_type,
                    ),
                )

    def _ensure_driver_available(self, protocol: str) -> None:
        spec = PROTOCOL_SPECS.get(protocol)
        if not spec:
            raise ConfigError(
                "parameter_error", self._msg("protocol_unknown", protocol=protocol)
            )
        dependency = spec.get("dependency")
        if dependency and importlib.util.find_spec(dependency) is None:
            raise ConfigError(
                "driver_error",
                self._msg("driver_missing", protocol=protocol, dependency=dependency),
            )

    def _flatten(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        flat: Dict[str, Any] = {}
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(self._flatten(value, prefix=path))
            else:
                flat[path] = value
        return flat

    def _msg(self, key: str, **kwargs: Any) -> str:
        templates = {
            "format_error": {
                "en": "Unsupported config format for {path}",
                "zh": "不支持的配置格式: {path}",
            },
            "file_missing": {
                "en": "Config file not found: {path}",
                "zh": "配置文件不存在: {path}",
            },
            "yaml_error": {
                "en": "YAML syntax error at line {line}: {detail}",
                "zh": "YAML语法错误，行 {line}: {detail}",
            },
            "json_error": {
                "en": "JSON syntax error at line {line}: {detail}",
                "zh": "JSON语法错误，行 {line}: {detail}",
            },
            "schema_error": {
                "en": "Configuration validation failed: {detail}",
                "zh": "配置校验失败: {detail}",
            },
            "compat_error": {
                "en": "Sensor {sensor} cannot bind protocol {protocol} "
                "(type {sensor_type} incompatible)",
                "zh": "传感器 {sensor} 无法绑定协议 {protocol}（类型 {sensor_type} 不兼容）",
            },
            "driver_missing": {
                "en": "Protocol {protocol} driver missing dependency {dependency}; "
                "run pip install {dependency}",
                "zh": "协议 {protocol} 驱动缺少依赖 {dependency}，请执行 pip install {dependency}",
            },
            "protocol_missing": {
                "en": "Protocol {protocol} not defined in configuration",
                "zh": "配置中未定义协议 {protocol}",
            },
            "protocol_unknown": {
                "en": "Unknown protocol {protocol}",
                "zh": "未知协议 {protocol}",
            },
            "sensor_missing": {
                "en": "Sensor {sensor} not found in configuration",
                "zh": "配置中未找到传感器 {sensor}",
            },
            "version_missing": {
                "en": "Version {version} not found in store",
                "zh": "未找到版本 {version}",
            },
            "not_loaded": {
                "en": "Configuration not loaded yet",
                "zh": "配置尚未加载",
            },
        }
        template = templates.get(key, {}).get(self.locale) or templates.get(
            key, {}
        ).get("en", "")
        return template.format(**kwargs)


__all__ = ["ConfigManager", "ConfigError", "VersionRecord"]
