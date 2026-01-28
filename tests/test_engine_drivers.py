import asyncio

import pytest

from sensor_fuzz.engine.drivers import HttpDriver, MqttDriver, ModbusTcpDriver, OpcUaDriver, UartDriver


class _DummyFuture:
    def __init__(self, value):
        self.value = value


def test_http_driver_with_requests(monkeypatch):
    called = {}

    class _Req:
        @staticmethod
        def request(method, url, headers=None, data=None, timeout=None):
            called["method"] = method
            called["url"] = url
            return {"ok": True}

    monkeypatch.setattr("sensor_fuzz.engine.drivers.requests", _Req)
    driver = HttpDriver(base_url="http://example.com")
    result = asyncio.run(driver.send({"path": "/p", "method": "POST", "data": "x"}))
    assert result == {"ok": True}
    assert called["url"].endswith("/p")


def test_mqtt_driver_with_stub(monkeypatch):
    class _Client:
        def __init__(self):
            self.connected = False

        def connect(self, host, port):
            self.connected = True

        def publish(self, topic, msg, qos=0):
            return {"topic": topic, "payload": msg, "qos": qos}

        def disconnect(self):
            self.connected = False

    monkeypatch.setattr("sensor_fuzz.engine.drivers.mqtt", type("_MQTT", (), {"Client": _Client}))
    driver = MqttDriver(host="localhost")
    result = asyncio.run(driver.send({"topic": "t", "payload": b"data", "qos": 1}))
    assert result["topic"] == "t"


def test_modbus_driver_with_stub(monkeypatch):
    class _Client:
        def __init__(self, host, port, unit_id, auto_open, auto_close):
            self.host = host
            self.unit_id = unit_id

        def read_holding_registers(self, address, length):
            return [address, length]

    monkeypatch.setattr("sensor_fuzz.engine.drivers.ModbusClient", _Client)
    driver = ModbusTcpDriver(host="localhost")
    result = asyncio.run(driver.send({"address": 10, "length": 2}))
    assert result == [10, 2]


def test_opcua_driver_with_stub(monkeypatch):
    class _Node:
        def __init__(self):
            self.value = "val"

        def get_value(self):
            return self.value

        def set_value(self, v):
            self.value = v

    class _Client:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def connect(self):
            return True

        def disconnect(self):
            return True

        def get_node(self, node):
            return _Node()

    monkeypatch.setattr("sensor_fuzz.engine.drivers.OpcUaClient", _Client)
    driver = OpcUaDriver(endpoint="opc.tcp://localhost:4840")
    result_read = asyncio.run(driver.send({"node": "n1", "value": None}))
    assert result_read == "val"
    result_write = asyncio.run(driver.send({"node": "n1", "value": 123}))
    assert result_write is True


def test_uart_driver_with_stub(monkeypatch):
    class _Serial:
        def __init__(self, port, baudrate, timeout):
            self.port = port
            self.buffer = b""
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, payload):
            self.buffer += payload

        def flush(self):
            pass

        def read(self, n):
            return b"resp"

    monkeypatch.setattr("sensor_fuzz.engine.drivers.serial", type("_S", (), {"Serial": _Serial}))
    driver = UartDriver(port="COM1")
    result = asyncio.run(driver.send(b"hello"))
    assert result == b"resp"


@pytest.mark.parametrize("proto", ["mqtt", "http", "modbus", "opcua", "uart"])
def test_drivers_graceful_when_missing_libs(monkeypatch, proto):
    # Force libraries to None to hit graceful path
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
