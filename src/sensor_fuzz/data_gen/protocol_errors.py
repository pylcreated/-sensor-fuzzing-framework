"""Protocol error injection placeholders."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Tuple

PROTO_FIELDS = {
    "mqtt": ["topic", "qos", "payload"],
    "http": ["method", "path", "headers"],
    "modbus": ["unit_id", "function_code", "address"],
}


def generate_protocol_errors(
    protocol: str, crc_flip: Tuple[int, int] | None = (0xFFFF, 0x0001)
) -> List[Dict[str, Any]]:
    """Generate protocol error scenarios for a given protocol.

    crc_flip=(mask, xor) lets callers tweak CRC flip patterns per protocol.
    Field offset mutations simulate index shifts / misalignment.
    """
    return _generate_protocol_errors_cached(protocol.lower(), crc_flip)


@lru_cache(maxsize=32)
def _generate_protocol_errors_cached(
    protocol: str, crc_flip: Tuple[int, int] | None = (0xFFFF, 0x0001)
) -> List[Dict[str, Any]]:
    """Cached version of protocol error generation."""
    protocol = protocol.lower()
    errors: List[Dict[str, Any]] = []
    crc_mask, crc_xor = crc_flip if crc_flip is not None else (None, None)

    def add_crc(desc: str = "crc-broken") -> None:
        """方法说明：执行 add crc 相关逻辑。"""
        if crc_mask is None:
            return
        errors.append(
            {"desc": desc, "mutation": "crc", "mask": crc_mask, "xor": crc_xor}
        )

    def add_offset(offset: int, field: str | None = None) -> None:
        """方法说明：执行 add offset 相关逻辑。"""
        entry: Dict[str, Any] = {"desc": "field-offset", "offset": offset}
        if field:
            entry["field"] = field
        errors.append(entry)

    if protocol == "mqtt":
        add_crc()
        errors.extend(
            [
                {"desc": "field-missing", "field": "topic"},
                {"desc": "field-missing", "field": "payload"},
            ]
        )
        add_offset(1, "payload")
    elif protocol == "http":
        errors.extend(
            [
                {"desc": "json-depth", "depth": 6},
                {"desc": "field-missing", "field": "path"},
            ]
        )
        add_offset(-1, "headers")
    elif protocol == "modbus":
        add_crc()
        errors.extend(
            [
                {"desc": "field-missing", "field": "function_code"},
            ]
        )
        add_offset(-1, "address")
    else:
        errors.append(
            {
                "desc": "generic-field-missing",
                "field": PROTO_FIELDS.get(protocol, ["field"]),
            }
        )
        add_crc("crc-generic")
        add_offset(1)
    return errors
