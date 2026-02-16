"""日志落地模块：提供面向 ELK 的批量日志写入能力。"""

from __future__ import annotations

from typing import Dict, List

try:
    from elasticsearch import Elasticsearch
except Exception:  # pragma: no cover
    Elasticsearch = None


class ElkSink:
    """ELK 日志写入器：可在 ES 不可用时自动降级。"""
    def __init__(
        self, host: str = "http://localhost:9200", index: str = "sensor-fuzz-logs"
    ) -> None:
        """初始化 ES 连接参数与可用性状态。"""
        self.host = host
        self.index = index
        self._available = Elasticsearch is not None
        self.es = None

    def _ensure_client(self) -> None:
        if not self._available or self.es is not None:
            return
        self.es = Elasticsearch(hosts=[self.host])

    def write_logs(self, docs: List[Dict]) -> None:
        """批量写入日志文档，内部复用对象池减少内存分配。"""
        actions = []
        pooled_docs = []
        try:
            for d in docs:
                # Use pooled log objects
                log_entry = self._get_log_from_pool()
                log_entry.clear()
                log_entry.update(d)
                log_entry["_index"] = self.index
                log_entry["_source"] = log_entry.copy()
                actions.append(log_entry)
                pooled_docs.append(log_entry)

            if not actions:
                return
            if not self._available:
                return  # degrade silently when ES not installed
            self._ensure_client()
            if self.es is None:
                return
            self.es.bulk(operations=actions, refresh="false")
        finally:
            # Release log objects back to pool
            for log_entry in pooled_docs:
                self._release_log_to_pool(log_entry)

    def _get_log_from_pool(self):
        """从日志对象池获取可复用字典。"""
        try:
            from sensor_fuzz.engine.memory_pool import LogObjectPool
            if not hasattr(self, '_log_pool'):
                self._log_pool = LogObjectPool(max_size=500, timeout=180.0)
            return self._log_pool.acquire()
        except ImportError:
            return {}

    def _release_log_to_pool(self, log_entry):
        """将日志字典归还到对象池。"""
        try:
            if hasattr(self, '_log_pool'):
                self._log_pool.release(log_entry)
        except Exception:
            pass
