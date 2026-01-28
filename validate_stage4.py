#!/usr/bin/env python3
"""验证第四阶段异步协议驱动优化的完整性。"""

import sys
import os
import asyncio

# 添加src到路径
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_imports():
    """检查所有必要的导入是否成功。"""
    print("🔍 检查导入...")

    try:
        from sensor_fuzz.engine.async_drivers import (
            AsyncMqttDriver,
            AsyncModbusTcpDriver,
            AsyncUartDriver,
            driver_pool
        )
        print("✅ 异步驱动模块导入成功")
    except ImportError as e:
        print(f"❌ 异步驱动模块导入失败: {e}")
        return False

    try:
        from sensor_fuzz.engine.drivers import MqttDriver, ModbusTcpDriver, UartDriver
        print("✅ 同步驱动模块导入成功")
    except ImportError as e:
        print(f"❌ 同步驱动模块导入失败: {e}")
        return False

    try:
        from sensor_fuzz.engine.runner import ExecutionEngine, run_full
        print("✅ 执行引擎导入成功")
    except ImportError as e:
        print(f"❌ 执行引擎导入失败: {e}")
        return False

    return True

def check_config():
    """检查配置文件。"""
    print("\n🔍 检查配置...")

    try:
        import yaml
        with open('config/sensor_protocol_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if 'strategy' in config and 'async_mode' in config['strategy']:
            async_mode = config['strategy']['async_mode']
            print(f"✅ 配置文件包含async_mode: {async_mode}")
            return True
        else:
            print("❌ 配置文件缺少async_mode设置")
            return False
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

async def test_driver_creation():
    """测试驱动创建。"""
    print("\n🔍 测试驱动创建...")

    try:
        # 测试异步驱动创建
        mqtt_driver = AsyncMqttDriver(host="localhost", port=1883)
        modbus_driver = AsyncModbusTcpDriver(host="localhost", port=502)
        uart_driver = AsyncUartDriver(port="COM1", baudrate=9600)
        print("✅ 异步驱动创建成功")
    except Exception as e:
        print(f"❌ 异步驱动创建失败: {e}")
        return False

    try:
        # 测试同步驱动创建
        from sensor_fuzz.engine.drivers import MqttDriver, ModbusTcpDriver, UartDriver
        sync_mqtt = MqttDriver(host="localhost", port=1883, async_mode=False)
        sync_modbus = ModbusTcpDriver(host="localhost", port=502, async_mode=False)
        sync_uart = UartDriver(port="COM1", baudrate=9600, async_mode=False)
        print("✅ 同步驱动创建成功")
    except Exception as e:
        print(f"❌ 同步驱动创建失败: {e}")
        return False

    return True

def check_main_updates():
    """检查主程序更新。"""
    print("\n🔍 检查主程序更新...")

    try:
        with open('src/sensor_fuzz/__main__.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'async_mode = cfg.strategy.get("async_mode", False)' in content:
            print("✅ 主程序支持async_mode配置")
        else:
            print("❌ 主程序缺少async_mode支持")
            return False

        if 'asyncio.run(run_full(engine, "i2c", sensor_config, async_mode))' in content:
            print("✅ 主程序正确传递async_mode参数")
        else:
            print("❌ 主程序未正确传递async_mode参数")
            return False

        return True
    except Exception as e:
        print(f"❌ 主程序检查失败: {e}")
        return False

def check_runner_updates():
    """检查执行引擎更新。"""
    print("\n🔍 检查执行引擎更新...")

    try:
        with open('src/sensor_fuzz/engine/runner.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'async def run_full(' in content and 'async_mode: bool = False' in content:
            print("✅ run_full函数支持async_mode参数")
        else:
            print("❌ run_full函数缺少async_mode支持")
            return False

        if 'await engine.run_suite(protocol, sensor, async_mode)' in content:
            print("✅ run_full正确传递async_mode")
        else:
            print("❌ run_full未正确传递async_mode")
            return False

        if 'async def run_suite(self, protocol: str, sensor: Dict[str, Any], async_mode: bool = False)' in content:
            print("✅ run_suite方法支持async_mode")
        else:
            print("❌ run_suite方法缺少async_mode支持")
            return False

        return True
    except Exception as e:
        print(f"❌ 执行引擎检查失败: {e}")
        return False

async def main():
    """主验证函数。"""
    print("🚀 第四阶段异步协议驱动优化验证")
    print("=" * 60)

    all_passed = True

    # 检查导入
    if not check_imports():
        all_passed = False

    # 检查配置
    if not check_config():
        all_passed = False

    # 测试驱动创建
    if not await test_driver_creation():
        all_passed = False

    # 检查主程序更新
    if not check_main_updates():
        all_passed = False

    # 检查执行引擎更新
    if not check_runner_updates():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 第四阶段异步协议驱动优化验证通过!")
        print("✅ 所有组件正确集成，支持异步I/O操作")
        print("💡 下一步: 运行async_driver_performance_test.py进行性能测试")
    else:
        print("❌ 验证失败，请检查上述错误")
        print("💡 提示: 确保所有依赖项已安装且代码无语法错误")

if __name__ == "__main__":
    asyncio.run(main())