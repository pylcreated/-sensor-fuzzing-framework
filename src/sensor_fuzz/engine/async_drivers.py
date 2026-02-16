"""Asynchronous protocol drivers for true async I/O operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union
import logging

try:
    import aiomqtt
except ImportError:
    aiomqtt = None

try:
    from pymodbus.client import AsyncModbusTcpClient
    from pymodbus.exceptions import ModbusException
except ImportError:
    AsyncModbusTcpClient = None
    ModbusException = None

try:
    import serial
    import aiofiles
except ImportError:
    serial = None
    aiofiles = None

try:
    import serial_asyncio
except ImportError:
    serial_asyncio = None


if not hasattr(asyncio, "open_serial_connection"):
    async def _open_serial_connection_fallback(*args, **kwargs):
        if serial_asyncio is None:
            raise ImportError(
                "async serial support requires pyserial-asyncio or an asyncio backend "
                "providing open_serial_connection"
            )
        return await serial_asyncio.open_serial_connection(*args, **kwargs)

    asyncio.open_serial_connection = _open_serial_connection_fallback

logger = logging.getLogger(__name__)


class AsyncDriver:
    """Base class for asynchronous protocol drivers."""

    def __init__(self, **kwargs):
        """方法说明：执行   init   相关逻辑。"""
        self.connected = False
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection asynchronously."""
        async with self._connection_lock:
            if not self.connected:
                await self._connect_impl()
                self.connected = True

    async def disconnect(self) -> None:
        """Close connection asynchronously."""
        async with self._connection_lock:
            if self.connected:
                await self._disconnect_impl()
                self.connected = False

    async def _connect_impl(self) -> None:
        """Implementation of connection logic."""
        raise NotImplementedError

    async def _disconnect_impl(self) -> None:
        """Implementation of disconnection logic."""
        raise NotImplementedError

    async def send(self, payload: Any) -> Any:
        """Send payload and return response."""
        raise NotImplementedError


@dataclass
class AsyncMqttDriver(AsyncDriver):
    """True asynchronous MQTT driver using aiomqtt."""

    host: str
    port: int = 1883
    client_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    keepalive: int = 60

    _client: Optional[aiomqtt.Client] = field(default=None, init=False)

    def __post_init__(self) -> None:
        super().__init__()

    async def _connect_impl(self) -> None:
        """Connect to MQTT broker asynchronously."""
        if aiomqtt is None:
            raise ImportError("aiomqtt is required for async MQTT support")

        self._client = aiomqtt.Client(
            hostname=self.host,
            port=self.port,
            client_id=self.client_id,
            username=self.username,
            password=self.password,
            keepalive=self.keepalive,
        )

        try:
            await self._client.connect()
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def _disconnect_impl(self) -> None:
        """Disconnect from MQTT broker."""
        if self._client:
            await self._client.disconnect()
            logger.info("Disconnected from MQTT broker")

    async def send(self, payload: Dict[str, Any]) -> Any:
        """Publish message to MQTT topic."""
        if not self.connected or not self._client:
            await self.connect()

        topic = payload.get("topic", "test")
        message = payload.get("payload", b"test")
        qos = payload.get("qos", 0)
        retain = payload.get("retain", False)

        # Ensure message is bytes
        if isinstance(message, str):
            message = message.encode('utf-8')
        elif isinstance(message, dict):
            import json
            message = json.dumps(message).encode('utf-8')

        try:
            await self._client.publish(topic, message, qos=qos, retain=retain)
            logger.debug(f"Published to topic '{topic}': {len(message)} bytes")
            return {"topic": topic, "qos": qos, "retain": retain, "success": True}
        except Exception as e:
            logger.error(f"Failed to publish MQTT message: {e}")
            return {"topic": topic, "error": str(e), "success": False}


@dataclass
class AsyncModbusTcpDriver(AsyncDriver):
    """True asynchronous Modbus TCP driver using pymodbus."""

    host: str
    port: int = 502
    timeout: float = 5.0
    retries: int = 3

    _client: Optional[AsyncModbusTcpClient] = field(default=None, init=False)

    def __post_init__(self) -> None:
        super().__init__()

    async def _connect_impl(self) -> None:
        """Connect to Modbus TCP server asynchronously."""
        if AsyncModbusTcpClient is None:
            raise ImportError("pymodbus is required for async Modbus support")

        self._client = AsyncModbusTcpClient(
            host=self.host,
            port=self.port,
            timeout=self.timeout,
            retries=self.retries,
        )

        try:
            await self._client.connect()
            logger.info(f"Connected to Modbus TCP server at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Modbus TCP server: {e}")
            raise

    async def _disconnect_impl(self) -> None:
        """Disconnect from Modbus TCP server."""
        if self._client:
            self._client.close()
            logger.info("Disconnected from Modbus TCP server")

    async def send(self, payload: Dict[str, Any]) -> Any:
        """Send Modbus request and return response."""
        if not self.connected or not self._client:
            await self.connect()

        function_code = payload.get("function_code", 3)  # Default to read holding registers
        address = payload.get("address", 0)
        count = payload.get("count", 1)
        unit_id = payload.get("unit_id", 1)
        values = payload.get("values")  # For write operations

        try:
            if function_code == 3:  # Read Holding Registers
                result = await self._client.read_holding_registers(
                    address=address,
                    count=count,
                    slave=unit_id
                )
                if result.isError():
                    return {"error": f"Modbus error: {result}", "success": False}
                return {
                    "function_code": function_code,
                    "address": address,
                    "count": count,
                    "values": result.registers,
                    "success": True
                }

            elif function_code == 16:  # Write Multiple Registers
                if values is None:
                    return {"error": "values required for write operation", "success": False}
                result = await self._client.write_registers(
                    address=address,
                    values=values,
                    slave=unit_id
                )
                if result.isError():
                    return {"error": f"Modbus error: {result}", "success": False}
                return {
                    "function_code": function_code,
                    "address": address,
                    "count": len(values),
                    "success": True
                }

            else:
                return {"error": f"Unsupported function code: {function_code}", "success": False}

        except Exception as e:
            logger.error(f"Modbus operation failed: {e}")
            return {"error": str(e), "success": False}


@dataclass
class AsyncUartDriver(AsyncDriver):
    """True asynchronous UART driver using asyncio and aiofiles."""

    port: str
    baudrate: int = 9600
    bytesize: int = serial.EIGHTBITS if serial else 8
    parity: str = serial.PARITY_NONE if serial else 'N'
    stopbits: int = serial.STOPBITS_ONE if serial else 1
    timeout: float = 1.0
    write_timeout: Optional[float] = None

    _reader: Optional[asyncio.StreamReader] = field(default=None, init=False)
    _writer: Optional[asyncio.StreamWriter] = field(default=None, init=False)

    def __post_init__(self) -> None:
        super().__init__()

    async def _connect_impl(self) -> None:
        """Open UART connection asynchronously."""
        if serial is None and not hasattr(asyncio, "open_serial_connection"):
            raise ImportError("pyserial is required for UART support")

        try:
            # Use asyncio's serial support (available in Python 3.7+)
            self._reader, self._writer = await asyncio.open_serial_connection(
                url=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
            )
            logger.info(f"Opened UART connection on {self.port} at {self.baudrate} baud")
        except Exception as e:
            logger.error(f"Failed to open UART connection: {e}")
            raise

    async def _disconnect_impl(self) -> None:
        """Close UART connection."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
            logger.info("Closed UART connection")

    async def send(self, payload: Union[bytes, str]) -> Any:
        """Send data over UART and read response."""
        if not self.connected or not self._writer or not self._reader:
            await self.connect()

        # Convert payload to bytes
        if isinstance(payload, str):
            data = payload.encode('utf-8')
        elif isinstance(payload, dict):
            import json
            data = json.dumps(payload).encode('utf-8')
        else:
            data = payload

        try:
            # Write data
            write_result = self._writer.write(data)
            if asyncio.iscoroutine(write_result):
                await write_result
            await self._writer.drain()

            # Read response with timeout
            response_data = b""
            try:
                response_data = await asyncio.wait_for(
                    self._reader.read(1024),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.debug("UART read timeout")

            logger.debug(f"UART sent {len(data)} bytes, received {len(response_data)} bytes")
            return {
                "sent": len(data),
                "received": len(response_data),
                "response": response_data,
                "success": True
            }

        except Exception as e:
            logger.error(f"UART operation failed: {e}")
            return {"error": str(e), "success": False}


# Factory function to create async drivers
async def create_async_driver(protocol: str, **kwargs) -> AsyncDriver:
    """Factory function to create appropriate async driver."""
    protocol = protocol.lower()

    if protocol == "mqtt":
        return AsyncMqttDriver(**kwargs)
    elif protocol in ("modbus", "modbus_tcp", "modbustcp"):
        return AsyncModbusTcpDriver(**kwargs)
    elif protocol in ("uart", "serial"):
        return AsyncUartDriver(**kwargs)
    else:
        raise ValueError(f"Unsupported async protocol: {protocol}")


# Connection pool for managing multiple connections
class AsyncDriverPool:
    """Connection pool for async drivers to reuse connections."""

    def __init__(self, max_connections: int = 10):
        """方法说明：执行   init   相关逻辑。"""
        self.max_connections = max_connections
        self._pool: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def get_driver(self, protocol: str, **kwargs) -> AsyncDriver:
        """Get a driver from pool or create new one."""
        key = f"{protocol}:{hash(frozenset(kwargs.items()))}"

        async with self._lock:
            if key not in self._pool:
                self._pool[key] = []

            # Try to find available driver
            for driver in self._pool[key]:
                if not driver.connected:
                    await driver.connect()
                    return driver

            # Create new driver if pool not full
            if len(self._pool[key]) < self.max_connections:
                driver = await create_async_driver(protocol, **kwargs)
                await driver.connect()
                self._pool[key].append(driver)
                return driver

            # Wait for available driver (simple implementation)
            while True:
                for driver in self._pool[key]:
                    if not driver.connected:
                        await driver.connect()
                        return driver
                await asyncio.sleep(0.1)  # Small delay before retry

    async def close_all(self):
        """Close all connections in pool."""
        async with self._lock:
            for drivers in self._pool.values():
                for driver in drivers:
                    await driver.disconnect()
            self._pool.clear()


# Global driver pool instance
driver_pool = AsyncDriverPool()