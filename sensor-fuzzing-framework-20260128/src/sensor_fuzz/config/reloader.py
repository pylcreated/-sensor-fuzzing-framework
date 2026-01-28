"""Lightweight configuration reload helper using mtime polling."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from sensor_fuzz.config.loader import ConfigLoader, ConfigSnapshot


class ConfigReloader:
    """Periodically checks config file mtime and reloads on change."""

    def __init__(
        self,
        path: str | Path,
        on_reload: Callable[[ConfigSnapshot], None],
        interval_sec: float = 5.0,
        loader: Optional[ConfigLoader] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        sil_mapping_override: Optional[Dict[str, Any]] = None,
        load_on_start: bool = True,
    ) -> None:
        self._path = Path(path)
        self._on_reload = on_reload
        self._interval = interval_sec
        self._loader = loader or ConfigLoader()
        self._on_error = on_error
        self._sil_override = sil_mapping_override
        self._load_on_start = load_on_start
        self._last_mtime: Optional[float] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._current: Optional[ConfigSnapshot] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if self._load_on_start:
            try:
                self._reload()
            except FileNotFoundError:
                # Wait until file exists
                pass
            except Exception as exc:
                if self._on_error:
                    self._on_error(exc)
        # Guard against a disappearing file between load and loop
        try:
            self._last_mtime = (
                self._path.stat().st_mtime if self._path.exists() else None
            )
        except OSError:
            self._last_mtime = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def update_sil_override(self, sil_mapping: Dict[str, Any]) -> None:
        self._sil_override = sil_mapping
        if self._current:
            try:
                cfg = self._loader.with_sil_mapping(self._current.config, sil_mapping)
                snapshot = ConfigSnapshot(cfg, self._path)
                self._current = snapshot
                self._on_reload(snapshot)
            except Exception as exc:
                if self._on_error:
                    self._on_error(exc)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                stat = self._path.stat()
                if self._last_mtime is None:
                    self._last_mtime = stat.st_mtime
                elif stat.st_mtime != self._last_mtime:
                    self._reload()
                    self._last_mtime = stat.st_mtime
            except FileNotFoundError:
                # Ignore missing file until created
                pass
            except Exception as exc:  # surface reload errors
                if self._on_error:
                    self._on_error(exc)
            time.sleep(self._interval)

    def _reload(self) -> None:
        cfg = self._loader.load(self._path)
        if self._sil_override is not None:
            cfg = self._loader.with_sil_mapping(cfg, self._sil_override)
        snapshot = ConfigSnapshot(cfg, self._path)
        self._current = snapshot
        self._on_reload(snapshot)
