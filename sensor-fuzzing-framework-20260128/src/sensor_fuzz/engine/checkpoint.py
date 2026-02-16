"""Checkpointing support for断点续测."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class Checkpoint:
    """Serializable checkpoint for test progress."""

    cases_executed: int
    anomalies_found: int
    last_case_id: str | None
    metadata: Dict[str, Any]


class CheckpointStore:
    """类说明：封装 CheckpointStore 的相关行为。"""
    def __init__(self, path: str | Path = "checkpoints/state.json") -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, ckpt: Checkpoint) -> Path:
        """方法说明：执行 save 相关逻辑。"""
        self._path.write_text(json.dumps(asdict(ckpt), indent=2), encoding="utf-8")
        return self._path

    def load(self) -> Checkpoint:
        """方法说明：执行 load 相关逻辑。"""
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return Checkpoint(**data)

    def exists(self) -> bool:
        """方法说明：执行 exists 相关逻辑。"""
        return self._path.exists()
