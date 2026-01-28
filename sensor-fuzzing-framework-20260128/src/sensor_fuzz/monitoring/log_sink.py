"""ELK-friendly logging sink placeholder."""

from __future__ import annotations

from typing import Dict, List

try:
    from elasticsearch import Elasticsearch
except Exception:  # pragma: no cover
    Elasticsearch = None


class ElkSink:
    def __init__(
        self, host: str = "http://localhost:9200", index: str = "sensor-fuzz-logs"
    ) -> None:
        self.index = index
        self._available = Elasticsearch is not None
        self.es = Elasticsearch(hosts=[host]) if self._available else None

    def write_logs(self, docs: List[Dict]) -> None:
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
            if not self._available or self.es is None:
                return  # degrade silently when ES not installed
            self.es.bulk(operations=actions, refresh="false")
        finally:
            # Release log objects back to pool
            for log_entry in pooled_docs:
                self._release_log_to_pool(log_entry)

    def _get_log_from_pool(self):
        """Get a log dict from pool."""
        try:
            from sensor_fuzz.engine.memory_pool import LogObjectPool
            if not hasattr(self, '_log_pool'):
                self._log_pool = LogObjectPool(max_size=500, timeout=180.0)
            return self._log_pool.acquire()
        except ImportError:
            return {}

    def _release_log_to_pool(self, log_entry):
        """Release log dict back to pool."""
        try:
            if hasattr(self, '_log_pool'):
                self._log_pool.release(log_entry)
        except Exception:
            pass
