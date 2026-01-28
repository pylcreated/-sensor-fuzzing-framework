"""POC injection catalog placeholder."""

from __future__ import annotations

from typing import Dict, List

POC_LIBRARY = {
    "mqtt": ["buffer-overflow"],
    "http": ["sql-injection"],
    "opcua": ["auth-bypass"],
    "profinet": ["dcp-flood"],
}


def list_pocs(protocol: str) -> List[str]:
    return POC_LIBRARY.get(protocol.lower(), [])


def build_poc_tasks(protocol: str, target: Dict) -> List[Dict]:
    return [
        {"protocol": protocol, "poc": poc, "target": target}
        for poc in list_pocs(protocol)
    ]
