"""抓包模块：基于 pyshark 进行在线抓包（依赖 tshark）。"""

from __future__ import annotations

from typing import List, Optional

try:
    import pyshark
except Exception:  # pragma: no cover
    pyshark = None


def capture(
    interface: str = "eth0", bpf_filter: Optional[str] = None, limit: int = 10
) -> List[str]:
    """执行抓包并返回报文字符串列表。"""
    if pyshark is None:
        return []
    capture_cls = getattr(pyshark, "LiveCapture", None)
    if capture_cls is None:
        capture_cls = getattr(pyshark, "capture", None)
    if capture_cls is None:
        return []

    cap = capture_cls(interface=interface, bpf_filter=bpf_filter)
    packets = []
    for i, pkt in enumerate(cap.sniff_continuously(packet_count=limit)):
        packets.append(str(pkt))
        if i >= limit:
            break
    cap.close()
    return packets
