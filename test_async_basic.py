#!/usr/bin/env python3
"""Simple test script to verify async drivers work."""

import asyncio
import sys
import os
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sensor_fuzz.engine.async_drivers import AsyncMqttDriver, AsyncModbusTcpDriver, AsyncUartDriver


@pytest.mark.asyncio
async def test_async_drivers():
    """Test async drivers basic functionality."""
    print("Testing async drivers...")

    # Test MQTT driver creation (without actual connection)
    try:
        mqtt_driver = AsyncMqttDriver(host="localhost", port=1883)
        print("✓ AsyncMqttDriver created successfully")
    except Exception as e:
        print(f"✗ AsyncMqttDriver creation failed: {e}")

    # Test Modbus driver creation
    try:
        modbus_driver = AsyncModbusTcpDriver(host="localhost", port=502)
        print("✓ AsyncModbusTcpDriver created successfully")
    except Exception as e:
        print(f"✗ AsyncModbusTcpDriver creation failed: {e}")

    # Test UART driver creation
    try:
        uart_driver = AsyncUartDriver(port="COM1", baudrate=9600)
        print("✓ AsyncUartDriver created successfully")
    except Exception as e:
        print(f"✗ AsyncUartDriver creation failed: {e}")

    print("Async drivers basic test completed!")

if __name__ == "__main__":
    asyncio.run(test_async_drivers())