"""Packet capture placeholder using pyshark (requires tshark installed)."""

from __future__ import annotations

from typing import List, Optional

try:
    import pyshark
except Exception:  # pragma: no cover
    pyshark = None


def capture(
    interface: str = "eth0", bpf_filter: Optional[str] = None, limit: int = 10
) -> List[str]:
    """方法说明：执行 capture 相关逻辑。"""
    if pyshark is None:
        return []
    cap = pyshark.LiveCapture(interface=interface, bpf_filter=bpf_filter)
    packets = []
    for i, pkt in enumerate(cap.sniff_continuously(packet_count=limit)):
        packets.append(str(pkt))
        if i >= limit:
            break
    cap.close()
    return packets
