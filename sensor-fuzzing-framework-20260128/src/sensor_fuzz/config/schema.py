"""Default JSON Schema for framework configuration."""

from __future__ import annotations

DEFAULT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "protocols": {
            "type": "object",
            "properties": {
                "profinet": {
                    "type": "object",
                    "properties": {
                        "endpoint": {"type": "string"},
                        "device_name": {"type": "string"},
                        "restartless_switch": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
                "i2c": {
                    "type": "object",
                    "properties": {
                        "bus": {"type": "integer", "minimum": 0},
                        "address": {"type": "integer", "minimum": 0},
                        "restartless_switch": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
                "spi": {
                    "type": "object",
                    "properties": {
                        "bus": {"type": "integer", "minimum": 0},
                        "device": {"type": "integer", "minimum": 0},
                        "mode": {"type": "integer", "minimum": 0, "maximum": 3},
                        "restartless_switch": {"type": "boolean"},
                    },
                    "additionalProperties": True,
                },
            },
            "additionalProperties": True,
        },
        "sensors": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "object",
                    "properties": {
                        "range": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "precision": {"type": "number"},
                        "signal_type": {"type": "string"},
                        "protocol": {"type": "string"},
                        "model": {"type": "string"},
                        "restartless_switch": {"type": "boolean"},
                    },
                    "required": ["range", "precision", "signal_type"],
                }
            },
        },
        "strategy": {
            "type": "object",
            "properties": {
                "anomaly_types": {"type": "array", "items": {"type": "string"}},
                "concurrency": {"type": "integer", "minimum": 1},
                "duration_hours": {"type": "number", "minimum": 0},
                "ai_enabled": {"type": "boolean"},
                "anomaly_contamination": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "anomaly_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
        },
        "sil_mapping": {
            "type": "object",
            "patternProperties": {
                "SIL[1-4]": {
                    "type": "object",
                    "properties": {
                        "coverage": {"type": "number", "minimum": 0.9, "maximum": 1.0},
                        "duration_hours": {"type": "number", "minimum": 0},
                        "max_false_positive": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 0.05,
                        },
                    },
                    "required": ["coverage"],
                }
            },
        },
    },
    "required": ["protocols", "sensors", "strategy", "sil_mapping"],
    "additionalProperties": False,
}
