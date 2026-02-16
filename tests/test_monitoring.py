"""模块说明：tests/test_monitoring.py 的主要实现与辅助逻辑。"""

from sensor_fuzz.monitoring.collector import collect_once, SYSTEM_CPU
from sensor_fuzz.monitoring.exporter import start_exporter
from sensor_fuzz.monitoring.log_sink import ElkSink
from sensor_fuzz.monitoring.peripherals import GpioMonitor, EnvMonitor
from sensor_fuzz.monitoring.packet_capture import capture


def test_collect_sets_metrics():
    """方法说明：执行 test collect sets metrics 相关逻辑。"""
    collect_once()
    assert SYSTEM_CPU._value.get() >= 0  # type: ignore


def test_exporter_starts():
    """方法说明：执行 test exporter starts 相关逻辑。"""
    exporter = start_exporter(port=9010)
    exporter.stop()


def test_collect_handles_missing_psutil(monkeypatch):
    """方法说明：执行 test collect handles missing psutil 相关逻辑。"""
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
    """方法说明：执行 test peripheral mock 相关逻辑。"""
    gm = GpioMonitor()
    em = EnvMonitor()
    assert "led" in gm.read_state()
    assert "temperature" in em.read_env()


def test_log_sink_optional_es(monkeypatch):
    """方法说明：执行 test log sink optional es 相关逻辑。"""
    sink = ElkSink()
    # Force unavailable path
    monkeypatch.setattr(sink, "_available", False)
    sink.write_logs([{"msg": "ok"}])


def test_log_sink_bulk(monkeypatch):
    """方法说明：执行 test log sink bulk 相关逻辑。"""
    sink = ElkSink()

    class _ES:
        """类说明：封装  ES 的相关行为。"""
        def __init__(self):
            """方法说明：执行   init   相关逻辑。"""
            self.called = False

        def bulk(self, operations=None, refresh=None):
            """方法说明：执行 bulk 相关逻辑。"""
            self.called = True
            self.ops = operations

    fake_es = _ES()
    sink._available = True
    sink.es = fake_es
    sink.write_logs([{"msg": "ok"}])
    assert fake_es.called


def test_packet_capture_optional_pyshark(monkeypatch):
    """方法说明：执行 test packet capture optional pyshark 相关逻辑。"""
    import sensor_fuzz.monitoring.packet_capture as pc

    monkeypatch.setattr(pc, "pyshark", None)
    assert capture() == []


def test_packet_capture_with_stub(monkeypatch):
    """方法说明：执行 test packet capture with stub 相关逻辑。"""
    import sensor_fuzz.monitoring.packet_capture as pc

    class _Cap:
        """类说明：封装  Cap 的相关行为。"""
        def __init__(self, interface=None, bpf_filter=None):
            """方法说明：执行   init   相关逻辑。"""
            self.closed = False

        def sniff_continuously(self, packet_count=None):
            """方法说明：执行 sniff continuously 相关逻辑。"""
            for i in range(min(packet_count or 1, 2)):
                yield f"pkt-{i}"

        def close(self):
            """方法说明：执行 close 相关逻辑。"""
            self.closed = True

    class _Pyshark:
        """类说明：封装  Pyshark 的相关行为。"""
        def __init__(self):
            """方法说明：执行   init   相关逻辑。"""
            self.closed = False

        LiveCapture = _Cap

    monkeypatch.setattr(pc, "pyshark", _Pyshark)
    packets = capture(interface="eth0", limit=1)
    assert packets == ["pkt-0"]
