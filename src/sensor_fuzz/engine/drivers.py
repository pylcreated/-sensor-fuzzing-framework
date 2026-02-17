"""Protocol driver interfaces and simple adapters."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Protocol, Optional, Union

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    from opcua import Client as OpcUaClient
except Exception:  # pragma: no cover
    OpcUaClient = None

try:
    from paho.mqtt import client as mqtt
except Exception:  # pragma: no cover
    mqtt = None

try:
    from pyModbusTCP.client import ModbusClient
except Exception:  # pragma: no cover
    ModbusClient = None

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None

# Import async drivers
from .async_drivers import (
    AsyncDriver,
    AsyncMqttDriver,
    AsyncModbusTcpDriver,
    AsyncUartDriver,
    create_async_driver,
    driver_pool,
)


class Driver(Protocol):
    """类说明：封装 Driver 的相关行为。"""
    async def send(self, payload: Any) -> Any: ...


class SyncDriver(Protocol):
    """Synchronous driver protocol for backward compatibility."""
    def send(self, payload: Any) -> Any: ...


class RestartlessDriver(Protocol):
    """Protocol for drivers that can apply params without restart."""

    def connect(self) -> None: ...

    def apply_params(self, params: Dict[str, Any]) -> None: ...

    def close(self) -> None: ...


@dataclass
class RestartlessDriverBase:
    """No-op restartless driver base; concrete drivers override connect/apply/close."""

    protocol: str
    params: Dict[str, Any] = field(default_factory=dict)

    def connect(self) -> None:  # pragma: no cover - trivial no-op
        """方法说明：执行 connect 相关逻辑。"""
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        """方法说明：执行 apply params 相关逻辑。"""
        self.params.update(params)

    def close(self) -> None:  # pragma: no cover - trivial no-op
        """方法说明：执行 close 相关逻辑。"""
        return None

    async def send(self, payload: bytes) -> Any:  # pragma: no cover - placeholder
        # In real use, send payload over hardware interface
        """异步方法说明：执行 send 相关流程。"""
        return {
            "protocol": self.protocol,
            "success": True,
            "simulated": True,
            "payload": payload,
        }


def get_restartless_driver(protocol: str, params: Dict[str, Any]) -> RestartlessDriver:
    """Return restartless-capable driver wrapper; falls back to no-op if unavailable."""
    p = protocol.lower()
    if p == "spi":
        return SPIDriver(params=params)
    if p == "i2c":
        return I2CDriver(params=params)
    if p == "profinet":
        return ProfinetDriver(params=params)
    return RestartlessDriverBase(protocol=p, params=params)


async def get_async_driver(protocol: str, **kwargs) -> AsyncDriver:
    """Get an asynchronous driver for the specified protocol."""
    return await create_async_driver(protocol, **kwargs)


def get_driver(protocol: str, async_mode: bool = False, **kwargs) -> Union[Driver, SyncDriver]:
    """Factory function to get appropriate driver (sync or async)."""
    protocol = protocol.lower()

    if async_mode:
        # Return async driver wrapped for compatibility
        class AsyncDriverWrapper:
            """类说明：封装 AsyncDriverWrapper 的相关行为。"""
            def __init__(self, async_driver: AsyncDriver):
                """方法说明：执行   init   相关逻辑。"""
                self.async_driver = async_driver

            async def send(self, payload: Any) -> Any:
                """异步方法说明：执行 send 相关流程。"""
                return await self.async_driver.send(payload)

        async def _create_async():
            """异步方法说明：执行  create async 相关流程。"""
            driver = await create_async_driver(protocol, **kwargs)
            return AsyncDriverWrapper(driver)

        # For async mode, return a coroutine that creates the driver
        return _create_async()
    else:
        # Return synchronous driver
        if protocol == "http":
            return HttpDriver(**kwargs)
        elif protocol == "mqtt":
            return MqttDriver(**kwargs)
        elif protocol in ("modbus", "modbus_tcp", "modbustcp"):
            return ModbusTcpDriver(**kwargs)
        elif protocol == "opcua":
            return OpcUaDriver(**kwargs)
        elif protocol in ("uart", "serial"):
            return UartDriver(**kwargs)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")


@dataclass
class SPIDriver(RestartlessDriverBase):
    """类说明：封装 SPIDriver 的相关行为。"""
    protocol: str = "spi"

    def connect(self) -> None:  # pragma: no cover - placeholder for hardware hook
        """方法说明：执行 connect 相关逻辑。"""
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        # In real use, open SPI device (bus/device/mode) and apply clock/bit order
        """方法说明：执行 apply params 相关逻辑。"""
        super().apply_params(params)


@dataclass
class I2CDriver(RestartlessDriverBase):
    """类说明：封装 I2CDriver 的相关行为。"""
    protocol: str = "i2c"

    def connect(self) -> None:  # pragma: no cover
        """方法说明：执行 connect 相关逻辑。"""
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        # In real use, configure bus/address/timeout
        """方法说明：执行 apply params 相关逻辑。"""
        super().apply_params(params)


@dataclass
class ProfinetDriver(RestartlessDriverBase):
    """类说明：封装 ProfinetDriver 的相关行为。"""
    protocol: str = "profinet"

    def connect(self) -> None:  # pragma: no cover
        """方法说明：执行 connect 相关逻辑。"""
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        # In real use, set device name/IP and reconnect session
        """方法说明：执行 apply params 相关逻辑。"""
        super().apply_params(params)


@dataclass
class HttpDriver:
    """类说明：封装 HttpDriver 的相关行为。"""
    base_url: str

    async def send(self, payload: Dict[str, Any]) -> Any:
        """异步方法说明：执行 send 相关流程。"""
        method = payload.get("method", "GET")
        path = payload.get("path", "/")
        data = payload.get("data")
        headers = payload.get("headers", {})
        url = f"{self.base_url}{path}"
        loop = asyncio.get_event_loop()
        if requests is None:
            return {"url": url, "method": method, "headers": headers, "data": data}
        return await loop.run_in_executor(
            None,
            lambda: requests.request(
                method, url, headers=headers, data=data, timeout=5
            ),
        )


@dataclass
class MqttDriver:
    """类说明：封装 MqttDriver 的相关行为。"""
    host: str
    port: int = 1883
    async_mode: bool = False

    async def send(self, payload: Dict[str, Any]) -> Any:
        """Send MQTT message - supports both sync and async modes."""
        if self.async_mode:
            # Use true async driver
            driver = await create_async_driver("mqtt", host=self.host, port=self.port)
            try:
                return await driver.send(payload)
            finally:
                await driver.disconnect()
        else:
            # Legacy sync mode
            topic = payload.get("topic", "test")
            msg = payload.get("payload", b"test")
            qos = payload.get("qos", 0)
            loop = asyncio.get_event_loop()
            if mqtt is None:
                return {"topic": topic, "payload": msg, "qos": qos}

            if isinstance(msg, dict):
                import json

                msg = json.dumps(msg, ensure_ascii=False).encode("utf-8")
            elif isinstance(msg, str):
                msg = msg.encode("utf-8")
            elif not isinstance(msg, (bytes, bytearray, int, float, type(None))):
                msg = str(msg).encode("utf-8")

            def _publish():
                """方法说明：执行  publish 相关逻辑。"""
                try:
                    client = mqtt.Client()
                    client.connect(self.host, self.port)
                    result = client.publish(topic, msg, qos=qos)
                    client.disconnect()
                    return {"topic": topic, "qos": qos, "success": True, "result": str(result)}
                except Exception as e:
                    return {"topic": topic, "qos": qos, "success": False, "error": str(e)}

            return await loop.run_in_executor(None, _publish)


@dataclass
class ModbusTcpDriver:
    """类说明：封装 ModbusTcpDriver 的相关行为。"""
    host: str
    port: int = 502
    async_mode: bool = False

    async def send(self, payload: Dict[str, Any]) -> Any:
        """Send Modbus request - supports both sync and async modes."""
        if self.async_mode:
            # Use true async driver
            driver = await create_async_driver("modbus_tcp", host=self.host, port=self.port)
            try:
                return await driver.send(payload)
            finally:
                await driver.disconnect()
        else:
            # Legacy sync mode
            unit_id = payload.get("unit_id", 1)
            address = payload.get("address", 0)
            length = payload.get("length", 1)
            loop = asyncio.get_event_loop()
            modbus_simulate = os.getenv("SENSOR_FUZZ_MODBUS_SIMULATE", "0") == "1"
            if ModbusClient is None:
                return {
                    "unit_id": unit_id,
                    "address": address,
                    "length": length,
                    "success": True,
                    "simulated": True,
                }

            def _read():
                """方法说明：执行  read 相关逻辑。"""
                try:
                    client = ModbusClient(
                        host=self.host,
                        port=self.port,
                        unit_id=unit_id,
                        auto_open=True,
                        auto_close=True,
                    )
                    values = client.read_holding_registers(address, length)
                    if values is None and modbus_simulate:
                        values = [0 for _ in range(max(int(length), 1))]
                        return {
                            "unit_id": unit_id,
                            "address": address,
                            "length": length,
                            "values": values,
                            "success": True,
                            "simulated": True,
                        }
                    return {
                        "unit_id": unit_id,
                        "address": address,
                        "length": length,
                        "values": values,
                        "success": values is not None,
                    }
                except Exception as e:
                    if modbus_simulate:
                        values = [0 for _ in range(max(int(length), 1))]
                        return {
                            "unit_id": unit_id,
                            "address": address,
                            "length": length,
                            "values": values,
                            "success": True,
                            "simulated": True,
                            "fallback_reason": str(e),
                        }
                    return {"error": str(e), "success": False}

            return await loop.run_in_executor(None, _read)


@dataclass
class OpcUaDriver:
    """类说明：封装 OpcUaDriver 的相关行为。"""
    endpoint: str

    def get_node(self, node_id: str):
        """同步获取 OPC UA 节点对象；库缺失时返回最小兼容桩。"""
        if OpcUaClient is None:
            class _FallbackNode:
                """类说明：封装  FallbackNode 的相关行为。"""
                def __init__(self):
                    """方法说明：执行   init   相关逻辑。"""
                    self.value = None

                def get_value(self):
                    """方法说明：执行 get value 相关逻辑。"""
                    return self.value

                def set_value(self, value):
                    """方法说明：执行 set value 相关逻辑。"""
                    self.value = value

            return _FallbackNode()

        client = OpcUaClient(self.endpoint)
        client.connect()
        try:
            return client.get_node(node_id)
        finally:
            client.disconnect()

    async def send(self, payload: Dict[str, Any]) -> Any:
        """异步方法说明：执行 send 相关流程。"""
        node = payload.get("node")
        value = payload.get("value")
        loop = asyncio.get_event_loop()
        if OpcUaClient is None:
            return {"node": node, "value": value}

        def _write():
            """方法说明：执行  write 相关逻辑。"""
            client = OpcUaClient(self.endpoint)
            client.connect()
            try:
                if value is None:
                    return client.get_node(node).get_value()
                client.get_node(node).set_value(value)
                return True
            finally:
                client.disconnect()

        return await loop.run_in_executor(None, _write)


@dataclass
class UartDriver:
    """类说明：封装 UartDriver 的相关行为。"""
    port: str
    baudrate: int = 9600
    async_mode: bool = False

    async def send(self, payload: bytes) -> Any:
        """Send UART data - supports both sync and async modes."""
        if self.async_mode:
            # Use true async driver
            driver = await create_async_driver("uart", port=self.port, baudrate=self.baudrate)
            try:
                return await driver.send(payload)
            finally:
                await driver.disconnect()
        else:
            # Legacy sync mode
            loop = asyncio.get_event_loop()

            if isinstance(payload, dict):
                import json

                payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            elif isinstance(payload, str):
                payload_bytes = payload.encode("utf-8")
            elif isinstance(payload, bytes):
                payload_bytes = payload
            else:
                payload_bytes = str(payload).encode("utf-8")

            uart_simulate = os.getenv("SENSOR_FUZZ_UART_SIMULATE", "0") == "1"
            if serial is None or uart_simulate:
                return {
                    "sent": len(payload_bytes),
                    "received": len(payload_bytes),
                    "response": payload_bytes,
                    "success": True,
                    "simulated": True,
                }

            def _write():
                """方法说明：执行  write 相关逻辑。"""
                try:
                    with serial.Serial(self.port, self.baudrate, timeout=2) as ser:
                        ser.write(payload_bytes)
                        ser.flush()
                        response = ser.read(128)
                        return {
                            "sent": len(payload_bytes),
                            "received": len(response),
                            "response": response,
                            "success": True,
                        }
                except Exception as e:
                    if uart_simulate:
                        return {
                            "sent": len(payload_bytes),
                            "received": len(payload_bytes),
                            "response": payload_bytes,
                            "success": True,
                            "simulated": True,
                            "fallback_reason": str(e),
                        }
                    return {"error": str(e), "success": False}

            return await loop.run_in_executor(None, _write)
