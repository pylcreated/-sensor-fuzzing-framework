"""Operation audit log (in-memory + append-to-file)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


class AuditLog:
    def __init__(self, path: str | Path = "logs/security_audit.log") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[Dict] = []

    def record(self, user: str, action: str, target: str) -> None:
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
        return f"{rec['ts']} {rec['user']} {rec['action']} {rec['target']}"

    def entries(self) -> List[Dict]:
        return list(self._records)
