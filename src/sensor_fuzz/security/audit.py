"""Operation audit log (in-memory + append-to-file)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


class AuditLog:
    """类说明：封装 AuditLog 的相关行为。"""
    def __init__(self, path: str | Path = "logs/security_audit.log") -> None:
        """方法说明：执行   init   相关逻辑。"""
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[Dict] = []

    def record(self, user: str, action: str, target: str) -> None:
        """方法说明：执行 record 相关逻辑。"""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "user": user,
            "action": action,
            "target": target,
        }
        self._records.append(entry)
        self._path.write_text(
            "\n".join([self._format(r) for r in self._records]), encoding="utf-8"
        )

    def _format(self, rec: Dict) -> str:
        """方法说明：执行  format 相关逻辑。"""
        return f"{rec['ts']} {rec['user']} {rec['action']} {rec['target']}"

    def entries(self) -> List[Dict]:
        """方法说明：执行 entries 相关逻辑。"""
        return list(self._records)
