"""Protocol driver interfaces and simple adapters."""

from __future__ import annotations

import asyncio
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
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        self.params.update(params)

    def close(self) -> None:  # pragma: no cover - trivial no-op
        return None

    async def send(self, payload: bytes) -> Any:  # pragma: no cover - placeholder
        # In real use, send payload over hardware interface
        return None


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
            def __init__(self, async_driver: AsyncDriver):
                self.async_driver = async_driver

            async def send(self, payload: Any) -> Any:
                return await self.async_driver.send(payload)

        async def _create_async():
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
    protocol: str = "spi"

    def connect(self) -> None:  # pragma: no cover - placeholder for hardware hook
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        # In real use, open SPI device (bus/device/mode) and apply clock/bit order
        super().apply_params(params)


@dataclass
class I2CDriver(RestartlessDriverBase):
    protocol: str = "i2c"

    def connect(self) -> None:  # pragma: no cover
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        # In real use, configure bus/address/timeout
        super().apply_params(params)


@dataclass
class ProfinetDriver(RestartlessDriverBase):
    protocol: str = "profinet"

    def connect(self) -> None:  # pragma: no cover
        return None

    def apply_params(self, params: Dict[str, Any]) -> None:
        # In real use, set device name/IP and reconnect session
        super().apply_params(params)


@dataclass
class HttpDriver:
    base_url: str

    async def send(self, payload: Dict[str, Any]) -> Any:
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

            def _publish():
                client = mqtt.Client()
                client.connect(self.host, self.port)
                result = client.publish(topic, msg, qos=qos)
                client.disconnect()
                return result

            return await loop.run_in_executor(None, _publish)


@dataclass
class ModbusTcpDriver:
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
            if ModbusClient is None:
                return {"unit_id": unit_id, "address": address, "length": length}

            def _read():
                client = ModbusClient(
                    host=self.host,
                    port=self.port,
                    unit_id=unit_id,
                    auto_open=True,
                    auto_close=True,
                )
                return client.read_holding_registers(address, length)

            return await loop.run_in_executor(None, _read)


@dataclass
class OpcUaDriver:
    endpoint: str

    async def send(self, payload: Dict[str, Any]) -> Any:
        node = payload.get("node")
        value = payload.get("value")
        loop = asyncio.get_event_loop()
        if OpcUaClient is None:
            return {"node": node, "value": value}

        def _write():
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
            if serial is None:
                return payload

            def _write():
                with serial.Serial(self.port, self.baudrate, timeout=2) as ser:
                    ser.write(payload)
                    ser.flush()
                    return ser.read(128)

            return await loop.run_in_executor(None, _write)
