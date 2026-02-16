"""审计日志模块：记录安全操作并落盘。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


class AuditLog:
    """审计日志对象：同时维护内存记录和文件记录。"""
    def __init__(self, path: str | Path = "logs/security_audit.log") -> None:
        """初始化审计文件路径并确保目录存在。"""
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[Dict] = []

    def record(self, user: str, action: str, target: str) -> None:
        """追加一条审计事件并同步写入日志文件。"""
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
        """将审计记录格式化为单行文本。"""
        return f"{rec['ts']} {rec['user']} {rec['action']} {rec['target']}"

    def entries(self) -> List[Dict]:
        """返回审计记录副本，避免外部直接修改内部列表。"""
        return list(self._records)
