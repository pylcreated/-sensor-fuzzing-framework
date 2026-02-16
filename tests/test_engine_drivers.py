"""模块说明：tests/test_engine_drivers.py 的主要实现与辅助逻辑。"""

import asyncio

import pytest

# 导入驱动模块中的相关类
from sensor_fuzz.engine.drivers import HttpDriver, MqttDriver, ModbusTcpDriver, OpcUaDriver, UartDriver

# 定义一个模拟异步操作结果的类
class _DummyFuture:
    """模拟异步操作结果的类。"""
    def __init__(self, value):
        """初始化模拟结果。"""
        self.value = value

# 测试HTTP驱动的功能
def test_http_driver_with_requests(monkeypatch):
    """测试HTTP驱动的功能。"""
    called = {}

    # 定义一个模拟的请求类
    class _Req:
        """模拟HTTP请求的类。"""
        @staticmethod
        def request(method, url, headers=None, data=None, timeout=None):
            """模拟发送HTTP请求。"""
            called["method"] = method
            called["url"] = url
            return {"ok": True}

    # 替换requests模块为模拟类
    monkeypatch.setattr("sensor_fuzz.engine.drivers.requests", _Req)
    driver = HttpDriver(base_url="http://example.com")
    result = asyncio.run(driver.send({"path": "/p", "method": "POST", "data": "x"}))

    # 验证请求是否正确发送
    assert result == {"ok": True}
    assert called["url"].endswith("/p")

# 测试MQTT驱动的功能
def test_mqtt_driver_with_stub(monkeypatch):
    """测试MQTT驱动的功能。"""
    # 定义一个模拟的MQTT客户端类
    class _Client:
        """模拟MQTT客户端的类。"""
        def __init__(self):
            """初始化MQTT客户端。"""
            self.connected = False

        def connect(self, host, port):
            """模拟连接到MQTT服务器。"""
            self.connected = True

        def publish(self, topic, msg, qos=0):
            """模拟发布消息。"""
            return {"topic": topic, "payload": msg, "qos": qos}

        def disconnect(self):
            """模拟断开连接。"""
            self.connected = False

    # 替换MQTT客户端为模拟类
    monkeypatch.setattr("sensor_fuzz.engine.drivers.mqtt", type("_MQTT", (), {"Client": _Client}))
    driver = MqttDriver(host="localhost")
    result = asyncio.run(driver.send({"topic": "t", "payload": b"data", "qos": 1}))

    # 验证消息是否正确发布
    assert result["topic"] == "t"

# 测试Modbus驱动的功能
def test_modbus_driver_with_stub(monkeypatch):
    """测试Modbus驱动的功能。"""
    # 定义一个模拟的Modbus客户端类
    class _Client:
        """模拟Modbus客户端的类。"""
        def __init__(self, host, port, unit_id, auto_open, auto_close):
            """初始化Modbus客户端。"""
            self.host = host
            self.unit_id = unit_id

        def read_holding_registers(self, address, length):
            """模拟读取保持寄存器。"""
            return [address, length]

    # 替换Modbus客户端为模拟类
    monkeypatch.setattr("sensor_fuzz.engine.drivers.ModbusClient", _Client)
    driver = ModbusTcpDriver(host="localhost")
    result = asyncio.run(driver.send({"address": 10, "length": 2}))

    # 验证读取结果是否正确
    assert result == [10, 2]

# 测试OPC UA驱动的功能
def test_opcua_driver_with_stub(monkeypatch):
    """测试OPC UA驱动的功能。"""
    # 定义一个模拟的OPC UA节点类
    class _Node:
        """模拟OPC UA节点的类。"""
        def __init__(self):
            """初始化节点。"""
            self.value = "val"

        def get_value(self):
            """获取节点值。"""
            return self.value

        def set_value(self, v):
            """设置节点值。"""
            self.value = v

    # 定义一个模拟的OPC UA客户端类
    class _Client:
        """模拟OPC UA客户端的类。"""
        def __init__(self, endpoint):
            """初始化客户端。"""
            self.endpoint = endpoint

        def connect(self):
            """模拟连接到OPC UA服务器。"""
            return True

        def disconnect(self):
            """模拟断开连接。"""
            return True

        def get_node(self, node):
            """获取节点。"""
            return _Node()

    # 替换OPC UA客户端为模拟类
    monkeypatch.setattr("sensor_fuzz.engine.drivers.OpcUaClient", _Client)
    driver = OpcUaDriver(endpoint="opc.tcp://localhost:4840")
    node = driver.get_node("ns=2;i=2")

    # 验证节点值是否正确
    assert node.get_value() == "val"

# 测试UART驱动的功能
def test_uart_driver_with_stub(monkeypatch):
    """测试UART驱动的功能。"""
    # 定义一个模拟的UART串行设备类
    class _Serial:
        """模拟UART串行设备的类。"""
        def __init__(self, port, baudrate, timeout):
            """初始化UART设备。"""
            self.port = port
            self.buffer = b""
            self.timeout = timeout

        def __enter__(self):
            """执行   enter   相关逻辑。"""
            return self

        def __exit__(self, exc_type, exc, tb):
            """执行   exit   相关逻辑。"""
            return False

        def write(self, payload):
            """执行 write 相关逻辑。"""
            self.buffer += payload

        def flush(self):
            """执行 flush 相关逻辑。"""
            pass

        def read(self, n):
            """执行 read 相关逻辑。"""
            return b"resp"

    # 替换UART设备为模拟类
    monkeypatch.setattr("sensor_fuzz.engine.drivers.serial", type("_S", (), {"Serial": _Serial}))
    driver = UartDriver(port="COM1")
    result = asyncio.run(driver.send(b"hello"))
    assert result == b"resp"


@pytest.mark.parametrize("proto", ["mqtt", "http", "modbus", "opcua", "uart"])
def test_drivers_graceful_when_missing_libs(monkeypatch, proto):
    # Force libraries to None to hit graceful path
    """方法说明：执行 test drivers graceful when missing libs 相关逻辑。"""
    monkeypatch.setattr("sensor_fuzz.engine.drivers.requests", None)
    monkeypatch.setattr("sensor_fuzz.engine.drivers.mqtt", None)
    monkeypatch.setattr("sensor_fuzz.engine.drivers.ModbusClient", None)
    monkeypatch.setattr("sensor_fuzz.engine.drivers.OpcUaClient", None)
    monkeypatch.setattr("sensor_fuzz.engine.drivers.serial", None)

    if proto == "mqtt":
        driver = MqttDriver(host="localhost")
        result = asyncio.run(driver.send({"topic": "t", "payload": b"x"}))
        assert result["topic"] == "t"
    elif proto == "http":
        driver = HttpDriver(base_url="http://x")
        result = asyncio.run(driver.send({"path": "/"}))
        assert result["url"].endswith("/")
    elif proto == "modbus":
        driver = ModbusTcpDriver(host="localhost")
        result = asyncio.run(driver.send({"address": 1, "length": 1}))
        assert result["address"] == 1
    elif proto == "opcua":
        driver = OpcUaDriver(endpoint="opc")
        result = asyncio.run(driver.send({"node": "n", "value": None}))
        assert result["node"] == "n"
    else:
        driver = UartDriver(port="COM1")
        result = asyncio.run(driver.send(b"hi"))
        assert result == b"hi"
