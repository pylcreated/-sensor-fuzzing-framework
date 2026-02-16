"""模块说明：tests/test_analysis.py 的主要实现与辅助逻辑。"""

from sensor_fuzz.analysis.cluster import cluster_anomalies, label_defects
from sensor_fuzz.analysis.severity import classify
from sensor_fuzz.analysis.report import render_html, export_pdf
from sensor_fuzz.analysis.root_cause import locate_root_cause
import pytest


def test_cluster_and_label():
    """方法说明：执行 test cluster and label 相关逻辑。"""
    labels, model = cluster_anomalies([[0, 0], [0.1, 0.1], [10, 10]], eps=0.5, min_samples=1)
    mapping = label_defects(labels)
    assert -1 in mapping or 0 in mapping


def test_severity_classify():
    """方法说明：执行 test severity classify 相关逻辑。"""
    assert classify({"deadlock": True}) == "critical"
    assert classify({"crash": True}) == "severe"


def test_render_html():
    """方法说明：执行 test render html 相关逻辑。"""
    html = render_html({"summary": "ok", "stats": {"test_cases": 1, "anomalies": 0, "false_positives": 0}, "findings": []})
    assert "Sensor Fuzz Test Report" in html


def test_export_pdf_optional(monkeypatch):
    """方法说明：执行 test export pdf optional 相关逻辑。"""
    import sensor_fuzz.analysis.report as report

    monkeypatch.setattr(report, "HTML", None)
    with pytest.raises(ImportError):
        export_pdf("<html></html>", "out.pdf")


def test_locate_root_cause_critical_event():
    """Test locate_root_cause with critical severity event."""
    events = [
        {"desc": "Normal event", "severity": "low"},
        {"desc": "Critical deadlock", "severity": "critical"},
        {"desc": "Another event", "severity": "medium"}
    ]

    result = locate_root_cause(events)

    assert result["root_cause"] == "Critical deadlock"
    assert result["evidence"] == {"desc": "Critical deadlock", "severity": "critical"}


def test_locate_root_cause_high_event():
    """Test locate_root_cause with high severity event."""
    events = [
        {"desc": "Normal event", "severity": "low"},
        {"desc": "High crash", "severity": "high"},
        {"desc": "Medium event", "severity": "medium"}
    ]

    result = locate_root_cause(events)

    assert result["root_cause"] == "High crash"
    assert result["evidence"] == {"desc": "High crash", "severity": "high"}


def test_locate_root_cause_no_severe_events():
    """Test locate_root_cause with no severe events."""
    events = [
        {"desc": "Normal event 1", "severity": "low"},
        {"desc": "Normal event 2", "severity": "medium"},
        {"desc": "Info event", "severity": "info"}
    ]

    result = locate_root_cause(events)

    assert result["root_cause"] == "unknown"
    assert result["evidence"] == [events[0]]  # First event as evidence


def test_locate_root_cause_empty_events():
    """Test locate_root_cause with empty events list."""
    events = []

    result = locate_root_cause(events)

    assert result["root_cause"] == "unknown"
    assert result["evidence"] == []


def test_locate_root_cause_mixed_events():
    """Test locate_root_cause with mixed severity events."""
    events = [
        {"desc": "Low event", "severity": "low"},
        {"desc": "Critical event", "severity": "critical"},
        {"desc": "High event", "severity": "high"}
    ]

    result = locate_root_cause(events)

    # Should pick the first critical/high event found
    assert result["root_cause"] == "Critical event"
    assert result["evidence"] == {"desc": "Critical event", "severity": "critical"}


def test_locate_root_cause_missing_severity():
    """Test locate_root_cause with events missing severity field."""
    events = [
        {"desc": "Event without severity"},
        {"desc": "Another event"}
    ]

    result = locate_root_cause(events)

    assert result["root_cause"] == "unknown"
    assert result["evidence"] == [events[0]]


def test_locate_root_cause_missing_desc():
    """Test locate_root_cause with events missing desc field."""
    events = [
        {"severity": "critical"},  # Missing desc
        {"desc": "Normal event", "severity": "low"}
    ]

    result = locate_root_cause(events)

    assert result["root_cause"] == "unknown"  # No valid desc found
    assert result["evidence"] == {"severity": "critical"}
