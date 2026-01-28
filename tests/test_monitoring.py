from sensor_fuzz.monitoring.collector import collect_once, SYSTEM_CPU
from sensor_fuzz.monitoring.exporter import start_exporter
from sensor_fuzz.monitoring.log_sink import ElkSink
from sensor_fuzz.monitoring.peripherals import GpioMonitor, EnvMonitor
from sensor_fuzz.monitoring.packet_capture import capture


def test_collect_sets_metrics():
    collect_once()
    assert SYSTEM_CPU._value.get() >= 0  # type: ignore


def test_exporter_starts():
    start_exporter(port=9010)


def test_collect_handles_missing_psutil(monkeypatch):
    import sensor_fuzz.monitoring.collector as collector

    monkeypatch.setattr(collector, "psutil", None)
    collect_once()
    # Prometheus Gauge has _value attr; dummy gauge has _value too
    val = getattr(collector.SYSTEM_CPU, "_value", 0)
    assert hasattr(collector.SYSTEM_CPU, "set")
    # If using real Gauge, _value is MutexValue; check it holds zero
    if hasattr(val, "_value"):
        assert val._value == 0  # type: ignore
    else:
        assert val == 0


def test_peripheral_mock():
    gm = GpioMonitor()
    em = EnvMonitor()
    assert "led" in gm.read_state()
    assert "temperature" in em.read_env()


def test_log_sink_optional_es(monkeypatch):
    sink = ElkSink()
    # Force unavailable path
    monkeypatch.setattr(sink, "_available", False)
    sink.write_logs([{"msg": "ok"}])


def test_log_sink_bulk(monkeypatch):
    sink = ElkSink()

    class _ES:
        def __init__(self):
            self.called = False

        def bulk(self, operations=None, refresh=None):
            self.called = True
            self.ops = operations

    fake_es = _ES()
    sink._available = True
    sink.es = fake_es
    sink.write_logs([{"msg": "ok"}])
    assert fake_es.called


def test_packet_capture_optional_pyshark(monkeypatch):
    import sensor_fuzz.monitoring.packet_capture as pc

    monkeypatch.setattr(pc, "pyshark", None)
    assert capture() == []


def test_packet_capture_with_stub(monkeypatch):
    import sensor_fuzz.monitoring.packet_capture as pc

    class _Cap:
        def __init__(self, interface=None, bpf_filter=None):
            self.closed = False

        def sniff_continuously(self, packet_count=None):
            for i in range(min(packet_count or 1, 2)):
                yield f"pkt-{i}"

        def close(self):
            self.closed = True

    class _Pyshark:
        def __init__(self):
            self.closed = False

        LiveCapture = _Cap

    monkeypatch.setattr(pc, "pyshark", _Pyshark)
    packets = capture(interface="eth0", limit=1)
    assert packets == ["pkt-0"]
