"""模块说明：tests/test_monitoring.py 的主要实现与辅助逻辑。"""

# 导入监控模块中的相关类和函数
from sensor_fuzz.monitoring.collector import collect_once, SYSTEM_CPU
from sensor_fuzz.monitoring.exporter import start_exporter
from sensor_fuzz.monitoring.log_sink import ElkSink
from sensor_fuzz.monitoring.peripherals import GpioMonitor, EnvMonitor
from sensor_fuzz.monitoring.packet_capture import capture


# 测试收集器设置指标的函数
def test_collect_sets_metrics():
    """测试收集器是否正确设置指标。"""
    # 调用一次数据收集
    collect_once()

    # 验证系统CPU指标是否被正确设置
    assert SYSTEM_CPU._value.get() >= 0  # type: ignore


# 测试导出器启动的函数
def test_exporter_starts():
    """测试导出器是否能够启动。"""
    # 启动导出器并验证其行为
    exporter = start_exporter(port=9010)
    exporter.stop()


# 测试收集器在缺少psutil模块时的行为
def test_collect_handles_missing_psutil(monkeypatch):
    """测试收集器在缺少psutil模块时的行为。"""
    import sensor_fuzz.monitoring.collector as collector

    # 模拟psutil模块不可用
    monkeypatch.setattr(collector, "psutil", None)
    collect_once()

    # 验证收集器是否正确处理缺少psutil的情况
    val = getattr(collector.SYSTEM_CPU, "_value", 0)
    assert hasattr(collector.SYSTEM_CPU, "set")
    if hasattr(val, "_value"):
        assert val._value == 0  # type: ignore
    else:
        assert val == 0


# 测试外设监控的模拟功能
def test_peripheral_mock():
    """测试外设监控的模拟功能。"""
    # 创建GPIO和环境监控实例
    gm = GpioMonitor()
    em = EnvMonitor()

    # 验证监控实例是否包含预期的状态
    assert "led" in gm.read_state()
    assert "temperature" in em.read_env()


# 测试日志接收器在ES不可用时的行为
def test_log_sink_optional_es(monkeypatch):
    """测试日志接收器在ES不可用时的行为。"""
    sink = ElkSink()

    # 模拟ES路径不可用
    monkeypatch.setattr(sink, "_available", False)
    sink.write_logs([{"msg": "ok"}])


# 测试日志接收器的批量写入功能
def test_log_sink_bulk(monkeypatch):
    """测试日志接收器的批量写入功能。"""
    sink = ElkSink()

    class _ES:
        """模拟ES的行为。"""
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


# 测试数据包捕获在缺少pyshark模块时的行为
def test_packet_capture_optional_pyshark(monkeypatch):
    """测试数据包捕获在缺少pyshark模块时的行为。"""
    import sensor_fuzz.monitoring.packet_capture as pc

    # 模拟pyshark模块不可用
    monkeypatch.setattr(pc, "pyshark", None)
    assert capture() == []


# 测试数据包捕获的模拟功能
def test_packet_capture_with_stub(monkeypatch):
    """测试数据包捕获的模拟功能。"""
    import sensor_fuzz.monitoring.packet_capture as pc

    class _Cap:
        """模拟数据包捕获器的行为。"""
        def __init__(self, interface=None, bpf_filter=None):
            self.closed = False

        def sniff_continuously(self, packet_count=None):
            for i in range(min(packet_count or 1, 2)):
                yield f"pkt-{i}"

        def close(self):
            self.closed = True

    class _Pyshark:
        """模拟Pyshark的行为。"""
        def __init__(self):
            self.capture = _Cap

    monkeypatch.setattr(pc, "pyshark", _Pyshark())
    packets = capture()
    assert len(packets) > 0
