import random

import numpy as np
import pytest

from sensor_fuzz import ai as ai_pkg
from sensor_fuzz.data_gen.boundary import generate_boundary_cases
from sensor_fuzz.data_gen.anomaly import generate_anomaly_values
from sensor_fuzz.data_gen.protocol_errors import generate_protocol_errors
from sensor_fuzz.data_gen.signal_distortion import distort_signal
from sensor_fuzz.data_gen.mutation_strategy import AdaptiveMutator, MutatorFeedback
from sensor_fuzz.data_gen.precheck import (
    benchmark_prechecks,
    poc_safety_ok,
    protocol_compat_ok,
    protobuf_syntax_ok,
)
from sensor_fuzz.data_gen.poc import list_pocs, build_poc_tasks


def test_boundary_cases_with_analog_under_over():
    cases = generate_boundary_cases({"range": [4, 20], "signal_type": "4-20mA", "anomaly_freq": 2}, tolerance=0.001)
    descs = {c["desc"] for c in cases}
    assert {"underflow-4ma", "overflow-20ma"}.issubset(descs)
    assert all(c["freq"] == 2 for c in cases)


def test_boundary_voltage_cases_include_guardrails():
    cases = generate_boundary_cases({"range": [-1, 9], "signal_type": "0-10V"})
    descs = {c["desc"] for c in cases}
    assert {"underflow-0v", "overflow-10v"}.issubset(descs)
    assert all(c.get("freq") == 1 for c in cases)


def test_anomaly_values_cover_analog():
    anomalies = generate_anomaly_values({"range": [0, 10], "signal_type": "0-10V"})
    descs = {a.get("desc") for a in anomalies}
    assert {"over-high", "non-numeric", "stuck-high-10v", "underflow-voltage"}.issubset(descs)


def test_anomaly_values_for_current():
    anomalies = generate_anomaly_values({"range": [4, 20], "signal_type": "current"})
    descs = {a.get("desc") for a in anomalies}
    assert {"stuck-low-4ma", "underflow-current", "stuck-high-20ma"}.issubset(descs)


def test_protocol_errors_crc_and_offset():
    errors = generate_protocol_errors("mqtt", crc_flip=(0xAAAA, 0x01))
    assert any(e.get("mutation") == "crc" and e.get("mask") == 0xAAAA for e in errors)
    assert any(e.get("desc") == "field-offset" for e in errors)
    generic = generate_protocol_errors("unknown")
    assert any(e.get("desc") == "field-offset" for e in generic)


def test_protocol_errors_no_crc_when_disabled():
    errors = generate_protocol_errors("mqtt", crc_flip=None)
    assert not any(e.get("mutation") == "crc" for e in errors)


def test_protocol_errors_http_and_modbus():
    http_errors = generate_protocol_errors("http")
    assert any(e.get("desc") == "json-depth" for e in http_errors)
    assert any(e.get("desc") == "field-offset" and e.get("field") == "headers" for e in http_errors)

    modbus_errors = generate_protocol_errors("modbus")
    assert any(e.get("mutation") == "crc" for e in modbus_errors)
    assert any(e.get("field") == "function_code" for e in modbus_errors)


def test_signal_distortion():
    cases = distort_signal({"signal_type": "4-20mA"})
    assert any(c["desc"] == "drift" for c in cases)


def test_signal_distortion_voltage_noise():
    cases = distort_signal({"signal_type": "0-10V"})
    assert any(c["desc"] == "noise" and c.get("noise_rms") for c in cases)


def test_mutator_updates_and_choice():
    random.seed(0)
    mut = AdaptiveMutator()
    mut.update([MutatorFeedback(category="boundary", detected=True)])
    assert mut.weights["boundary"] > 1.0
    chosen = mut.choose()
    assert chosen in mut.weights


def test_mutator_fallback_when_weights_zero():
    mut = AdaptiveMutator()
    mut.weights = {k: 0.0 for k in mut.weights}
    assert mut.choose() == "boundary"
    mut.update([MutatorFeedback(category="protocol_error", detected=False)])
    assert mut.weights["protocol_error"] < 1.0


def test_mutator_fallback_on_random_overflow(monkeypatch):
    mut = AdaptiveMutator()

    def fake_uniform(_a: float, _b: float) -> float:
        return 999.0  # force loop to exhaust and hit final return

    monkeypatch.setattr(random, "uniform", fake_uniform)
    assert mut.choose() == "boundary"


def test_precheck_benchmark():
    cases = [
        {"protocol": "mqtt", "payload": b"ok"},
        {"protocol": "http", "payload": b""},
    ]
    results = benchmark_prechecks(
        cases,
        [
            lambda c: bool(c.get("payload")),
            lambda c: c.get("protocol") == "mqtt",
        ],
    )
    assert results["check_0"] == 0.5
    assert results["check_1"] == 0.5


def test_precheck_benchmark_handles_exceptions():
    cases = [{"protocol": "mqtt", "payload": b"ok"}]

    def boom(_: dict) -> bool:
        raise ValueError("boom")

    results = benchmark_prechecks(cases, [boom])
    assert results["check_0"] == 0.0


def test_precheck_helpers_direct_calls():
    assert protobuf_syntax_ok(b"msg") is True
    assert protobuf_syntax_ok(b"") is False
    assert protocol_compat_ok({"protocol": "mqtt"}, "mqtt") is True
    assert protocol_compat_ok({"protocol": "http"}, "mqtt") is False
    assert poc_safety_ok("safe") is True
    assert poc_safety_ok("over-voltage-burn") is False


def test_poc_listing_and_tasks():
    mqtt_pocs = list_pocs("mqtt")
    assert "buffer-overflow" in mqtt_pocs
    assert list_pocs("unknown") == []

    target = {"host": "127.0.0.1"}
    tasks = build_poc_tasks("profinet", target)
    assert tasks and tasks[0]["protocol"] == "profinet"
    assert tasks[0]["target"] is target


def test_lstm_optional_path():
    data = np.zeros((2, 3, 1), dtype=np.float32)
    labels = np.zeros(2, dtype=np.float32)
    if ai_pkg.lstm.torch is None:
        with pytest.raises(ImportError):
            ai_pkg.lstm.train_lstm(data, labels, epochs=1)
    else:
        model = ai_pkg.lstm.train_lstm(data, labels, epochs=1, lr=1e-2)
        scores = ai_pkg.lstm.predict(model, data)
        assert scores.shape[0] == 2
