#!/usr/bin/env python3
"""Simple test script to verify async drivers work."""

import asyncio
import sys
import os
import pytest

# 将src目录添加到Python路径中
# 这样可以导入src目录下的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入异步驱动模块
from sensor_fuzz.engine.async_drivers import AsyncMqttDriver, AsyncModbusTcpDriver, AsyncUartDriver

# 使用pytest标记异步测试
# 测试异步驱动的基本功能
@pytest.mark.asyncio
async def test_async_drivers():
    """测试异步驱动的基本功能。"""
    # 创建异步驱动实例并测试其行为
    mqtt_driver = AsyncMqttDriver(host="localhost", port=1883)
    modbus_driver = AsyncModbusTcpDriver(host="localhost", port=502)
    uart_driver = AsyncUartDriver(port="COM1", baudrate=9600)

    # 验证驱动是否正确初始化
    assert mqtt_driver.host == "localhost"
    assert modbus_driver.port == 502
    assert uart_driver.baudrate == 9600

    print("Async drivers basic test completed!")

if __name__ == "__main__":
    asyncio.run(test_async_drivers())