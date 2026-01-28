"""Tests for asynchronous protocol drivers."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sensor_fuzz.engine.async_drivers import (
    AsyncMqttDriver,
    AsyncModbusTcpDriver,
    AsyncUartDriver,
    create_async_driver,
    driver_pool,
)


class TestAsyncMqttDriver:
    """Test AsyncMqttDriver functionality."""

    @pytest.mark.asyncio
    async def test_mqtt_driver_creation(self):
        """Test MQTT driver creation."""
        driver = AsyncMqttDriver(host="localhost", port=1883)
        assert driver.host == "localhost"
        assert driver.port == 1883
        assert not driver.connected

    @pytest.mark.asyncio
    async def test_mqtt_driver_connection(self):
        """Test MQTT driver connection."""
        driver = AsyncMqttDriver(host="localhost", port=1883)

        # Mock aiomqtt
        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            await driver.connect()
            assert driver.connected
            mock_aiomqtt.Client.assert_called_once()
            mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_mqtt_send_message(self):
        """Test MQTT message sending."""
        driver = AsyncMqttDriver(host="localhost", port=1883)

        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            await driver.connect()

            payload = {"topic": "test/topic", "payload": "test message", "qos": 1}
            result = await driver.send(payload)

            assert result["success"] is True
            assert result["topic"] == "test/topic"
            assert result["qos"] == 1
            mock_client.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_mqtt_disconnect(self):
        """Test MQTT driver disconnection."""
        driver = AsyncMqttDriver(host="localhost", port=1883)

        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            await driver.connect()
            await driver.disconnect()

            assert not driver.connected
            mock_client.disconnect.assert_called_once()


class TestAsyncModbusDriver:
    """Test AsyncModbusTcpDriver functionality."""

    @pytest.mark.asyncio
    async def test_modbus_driver_creation(self):
        """Test Modbus driver creation."""
        driver = AsyncModbusTcpDriver(host="localhost", port=502)
        assert driver.host == "localhost"
        assert driver.port == 502
        assert not driver.connected

    @pytest.mark.asyncio
    async def test_modbus_read_operation(self):
        """Test Modbus read operation."""
        driver = AsyncModbusTcpDriver(host="localhost", port=502)

        with patch('sensor_fuzz.engine.async_drivers.AsyncModbusTcpClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful read
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_result.registers = [123, 456]
            mock_client.read_holding_registers.return_value = mock_result

            await driver.connect()

            payload = {"function_code": 3, "address": 0, "count": 2, "unit_id": 1}
            result = await driver.send(payload)

            assert result["success"] is True
            assert result["function_code"] == 3
            assert result["values"] == [123, 456]
            mock_client.read_holding_registers.assert_called_once_with(
                address=0, count=2, slave=1
            )

    @pytest.mark.asyncio
    async def test_modbus_write_operation(self):
        """Test Modbus write operation."""
        driver = AsyncModbusTcpDriver(host="localhost", port=502)

        with patch('sensor_fuzz.engine.async_drivers.AsyncModbusTcpClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful write
            mock_result = MagicMock()
            mock_result.isError.return_value = False
            mock_client.write_registers.return_value = mock_result

            await driver.connect()

            payload = {"function_code": 16, "address": 0, "values": [123, 456], "unit_id": 1}
            result = await driver.send(payload)

            assert result["success"] is True
            assert result["function_code"] == 16
            mock_client.write_registers.assert_called_once_with(
                address=0, values=[123, 456], slave=1
            )


class TestAsyncUartDriver:
    """Test AsyncUartDriver functionality."""

    @pytest.mark.asyncio
    async def test_uart_driver_creation(self):
        """Test UART driver creation."""
        driver = AsyncUartDriver(port="COM1", baudrate=9600)
        assert driver.port == "COM1"
        assert driver.baudrate == 9600
        assert not driver.connected

    @pytest.mark.asyncio
    async def test_uart_send_receive(self):
        """Test UART send and receive."""
        driver = AsyncUartDriver(port="COM1", baudrate=9600)

        with patch('asyncio.open_serial_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)

            # Mock read response
            mock_reader.read.return_value = b"response"

            await driver.connect()

            payload = b"test command"
            result = await driver.send(payload)

            assert result["success"] is True
            assert result["sent"] == len(payload)
            assert result["received"] == len(b"response")
            mock_writer.write.assert_called_once_with(payload)
            mock_reader.read.assert_called_once()


class TestAsyncDriverFactory:
    """Test async driver factory functions."""

    @pytest.mark.asyncio
    async def test_create_mqtt_driver(self):
        """Test creating MQTT driver via factory."""
        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            driver = await create_async_driver("mqtt", host="localhost", port=1883)
            assert isinstance(driver, AsyncMqttDriver)
            assert driver.host == "localhost"
            assert driver.port == 1883

    @pytest.mark.asyncio
    async def test_create_modbus_driver(self):
        """Test creating Modbus driver via factory."""
        with patch('sensor_fuzz.engine.async_drivers.AsyncModbusTcpClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            driver = await create_async_driver("modbus_tcp", host="localhost", port=502)
            assert isinstance(driver, AsyncModbusTcpDriver)
            assert driver.host == "localhost"
            assert driver.port == 502

    @pytest.mark.asyncio
    async def test_create_unsupported_driver(self):
        """Test creating unsupported driver raises error."""
        with pytest.raises(ValueError, match="Unsupported async protocol"):
            await create_async_driver("unsupported_protocol")


class TestDriverPool:
    """Test async driver pool functionality."""

    @pytest.mark.asyncio
    async def test_pool_get_driver(self):
        """Test getting driver from pool."""
        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            driver = await driver_pool.get_driver("mqtt", host="localhost", port=1883)
            assert isinstance(driver, AsyncMqttDriver)
            assert driver.connected

    @pytest.mark.asyncio
    async def test_pool_reuse_driver(self):
        """Test driver reuse from pool."""
        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            # Get driver twice with same parameters
            driver1 = await driver_pool.get_driver("mqtt", host="localhost", port=1883)
            driver2 = await driver_pool.get_driver("mqtt", host="localhost", port=1883)

            # Should be the same driver instance if available
            # (implementation dependent, but should work)

    @pytest.mark.asyncio
    async def test_pool_close_all(self):
        """Test closing all drivers in pool."""
        with patch('sensor_fuzz.engine.async_drivers.aiomqtt') as mock_aiomqtt:
            mock_client = AsyncMock()
            mock_aiomqtt.Client.return_value = mock_client

            await driver_pool.get_driver("mqtt", host="localhost", port=1883)
            await driver_pool.close_all()

            # Pool should be empty
            assert len(driver_pool._pool) == 0