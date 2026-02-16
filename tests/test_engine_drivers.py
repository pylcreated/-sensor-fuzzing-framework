"""模块说明：tests/test_engine_drivers.py 的主要实现与辅助逻辑。"""

import asyncio

import pytest

from sensor_fuzz.engine.drivers import HttpDriver, MqttDriver, ModbusTcpDriver, OpcUaDriver, UartDriver


class _DummyFuture:
    """类说明：封装  DummyFuture 的相关行为。"""
    def __init__(self, value):
        """方法说明：执行   init   相关逻辑。"""
        self.value = value


def test_http_driver_with_requests(monkeypatch):
    """方法说明：执行 test http driver with requests 相关逻辑。"""
    called = {}

    class _Req:
        """类说明：封装 Req 的相关行为。"""
        @staticmethod
        def request(method, url, headers=None, data=None, timeout=None):
            """方法说明：执行 request 相关逻辑。"""
            called["method"] = method
            called["url"] = url
            return {"ok": True}

    monkeypatch.setattr("sensor_fuzz.engine.drivers.requests", _Req)
    driver = HttpDriver(base_url="http://example.com")
    result = asyncio.run(driver.send({"path": "/p", "method": "POST", "data": "x"}))
    assert result == {"ok": True}
    assert called["url"].endswith("/p")


def test_mqtt_driver_with_stub(monkeypatch):
    """方法说明：执行 test mqtt driver with stub 相关逻辑。"""
    class _Client:
        """类说明：封装  Client 的相关行为。"""
        def __init__(self):
            """方法说明：执行   init   相关逻辑。"""
            self.connected = False

        def connect(self, host, port):
            """方法说明：执行 connect 相关逻辑。"""
            self.connected = True

        def publish(self, topic, msg, qos=0):
            """方法说明：执行 publish 相关逻辑。"""
            return {"topic": topic, "payload": msg, "qos": qos}

        def disconnect(self):
            """方法说明：执行 disconnect 相关逻辑。"""
            self.connected = False

    monkeypatch.setattr("sensor_fuzz.engine.drivers.mqtt", type("_MQTT", (), {"Client": _Client}))
    driver = MqttDriver(host="localhost")
    result = asyncio.run(driver.send({"topic": "t", "payload": b"data", "qos": 1}))
    assert result["topic"] == "t"


def test_modbus_driver_with_stub(monkeypatch):
    """方法说明：执行 test modbus driver with stub 相关逻辑。"""
    class _Client:
        """类说明：封装  Client 的相关行为。"""
        def __init__(self, host, port, unit_id, auto_open, auto_close):
            """方法说明：执行   init   相关逻辑。"""
            self.host = host
            self.unit_id = unit_id

        def read_holding_registers(self, address, length):
            """方法说明：执行 read holding registers 相关逻辑。"""
            return [address, length]

    monkeypatch.setattr("sensor_fuzz.engine.drivers.ModbusClient", _Client)
    driver = ModbusTcpDriver(host="localhost")
    result = asyncio.run(driver.send({"address": 10, "length": 2}))
    assert result == [10, 2]


def test_opcua_driver_with_stub(monkeypatch):
    """方法说明：执行 test opcua driver with stub 相关逻辑。"""
    class _Node:
        """类说明：封装  Node 的相关行为。"""
        def __init__(self):
            """方法说明：执行   init   相关逻辑。"""
            self.value = "val"

        def get_value(self):
            """方法说明：执行 get value 相关逻辑。"""
            return self.value

        def set_value(self, v):
            """方法说明：执行 set value 相关逻辑。"""
            self.value = v

    class _Client:
        """类说明：封装  Client 的相关行为。"""
        def __init__(self, endpoint):
            """方法说明：执行   init   相关逻辑。"""
            self.endpoint = endpoint

        def connect(self):
            """方法说明：执行 connect 相关逻辑。"""
            return True

        def disconnect(self):
            """方法说明：执行 disconnect 相关逻辑。"""
            return True

        def get_node(self, node):
            """方法说明：执行 get node 相关逻辑。"""
            return _Node()

    monkeypatch.setattr("sensor_fuzz.engine.drivers.OpcUaClient", _Client)
    driver = OpcUaDriver(endpoint="opc.tcp://localhost:4840")
    result_read = asyncio.run(driver.send({"node": "n1", "value": None}))
    assert result_read == "val"
    result_write = asyncio.run(driver.send({"node": "n1", "value": 123}))
    assert result_write is True


def test_uart_driver_with_stub(monkeypatch):
    """方法说明：执行 test uart driver with stub 相关逻辑。"""
    class _Serial:
        """类说明：封装  Serial 的相关行为。"""
        def __init__(self, port, baudrate, timeout):
            """方法说明：执行   init   相关逻辑。"""
            self.port = port
            self.buffer = b""
            self.timeout = timeout

        def __enter__(self):
            """方法说明：执行   enter   相关逻辑。"""
            return self

        def __exit__(self, exc_type, exc, tb):
            """方法说明：执行   exit   相关逻辑。"""
            return False

        def write(self, payload):
            """方法说明：执行 write 相关逻辑。"""
            self.buffer += payload

        def flush(self):
            """方法说明：执行 flush 相关逻辑。"""
            pass

        def read(self, n):
            """方法说明：执行 read 相关逻辑。"""
            return b"resp"

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
