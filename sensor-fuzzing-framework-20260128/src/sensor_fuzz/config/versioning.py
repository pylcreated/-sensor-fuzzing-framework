"""Simple on-disk configuration version store."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sensor_fuzz.config.loader import FrameworkConfig


class ConfigVersionStore:
    """Persist configuration versions for rollback and audit."""

    def __init__(
        self, base_dir: str | Path = ".sf_config_versions", retain: int = 20
    ) -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._retain = retain

    def save(self, name: str, config: FrameworkConfig) -> Path:
        """方法说明：执行 save 相关逻辑。"""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self._base / f"{name}-{ts}.json"
        payload: Dict[str, Any] = {
            "saved_at": ts,
            "protocols": config.protocols,
            "sensors": config.sensors,
            "strategy": config.strategy,
            "sil_mapping": config.sil_mapping,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._prune_excess()
        return path

    def list_versions(self) -> list[Path]:
        """方法说明：执行 list versions 相关逻辑。"""
        return sorted(self._base.glob("*.json"))

    def load(self, path: str | Path) -> Dict[str, Any]:
        """方法说明：执行 load 相关逻辑。"""
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Failed to load version file {path}: {exc}") from exc

    def latest(self) -> Optional[Path]:
        """方法说明：执行 latest 相关逻辑。"""
        versions = self.list_versions()
        return versions[-1] if versions else None

    def rollback_latest(self) -> Optional[Dict[str, Any]]:
        """方法说明：执行 rollback latest 相关逻辑。"""
        latest = self.latest()
        if latest is None:
            return None
        return self.load(latest)

    def _prune_excess(self) -> None:
        """方法说明：执行  prune excess 相关逻辑。"""
        if self._retain <= 0:
            return
        versions = self.list_versions()
        if len(versions) <= self._retain:
            return
        for path in versions[: -self._retain]:
            try:
                path.unlink()
            except OSError:
                # Keep going even if cleanup fails
                continue
