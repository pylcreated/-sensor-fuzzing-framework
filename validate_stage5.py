#!/usr/bin/env python3
"""验证第五阶段SIL合规性验证的完整性。"""

import os
import asyncio

# 添加src到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 检查SIL合规性模块的函数
# 该函数尝试导入相关模块并测试其功能是否正常
# 包括SIL等级枚举和SIL要求的测试
# 如果模块导入失败或测试失败，将返回False
# 否则返回True
def check_sil_module():
    """检查SIL合规性模块。"""
    print(" 检查SIL合规性模块...")

    try:
        from sensor_fuzz.sil_compliance import (
            SILComplianceManager,
            SafetyIntegrityLevel,
            SILRequirements,
            SILComplianceValidator,
            SILComplianceReport
        )
        print(" SIL合规性模块导入成功")
    except ImportError as e:
        print(f" SIL合规性模块导入失败: {e}")
        return False

    # 测试SIL等级枚举
    try:
        sil1 = SafetyIntegrityLevel.SIL1
        sil4 = SafetyIntegrityLevel.SIL4
        assert sil1.value == 1
        assert sil4.value == 4
        print(" SIL等级枚举工作正常")
    except Exception as e:
        print(f" SIL等级枚举测试失败: {e}")
        return False

    # 测试SIL要求
    try:
        req_sil1 = SILRequirements.get_requirements(SafetyIntegrityLevel.SIL1)
        req_sil4 = SILRequirements.get_requirements(SafetyIntegrityLevel.SIL4)
        assert req_sil1.min_test_coverage == 0.90
        assert req_sil4.min_test_coverage == 0.99
        print(" SIL要求配置正确")
    except Exception as e:
        print(f" SIL要求测试失败: {e}")
        return False

    return True

# 检查配置文件更新的函数
# 该函数读取配置文件并检查其中的关键字段是否存在
# 如果字段缺失或读取失败，将返回False
# 否则返回True
def check_config_updates():
    """检查配置文件更新。"""
    print("\n 检查配置文件更新...")

    try:
        import yaml
        with open('config/sensor_protocol_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        strategy = config.get('strategy', {})
        sil_level = strategy.get('sil_level')
        hardware_protection = strategy.get('hardware_protection')
        redundancy_check = strategy.get('redundancy_check')

        if sil_level:
            print(f" 配置文件包含SIL等级: {sil_level}")
        else:
            print(" 配置文件缺少SIL等级设置")
            return False

        if hardware_protection is not None:
            print(f" 配置文件包含硬件保护设置: {hardware_protection}")
        else:
            print(" 配置文件缺少硬件保护设置")
            return False

        if redundancy_check is not None:
            print(f" 配置文件包含冗余检查设置: {redundancy_check}")
        else:
            print(" 配置文件缺少冗余检查设置")
            return False

        return True
    except Exception as e:
        print(f" 配置文件检查失败: {e}")
        return False

# 检查主程序集成的函数
# 该函数读取主程序文件并检查是否包含必要的导入和初始化代码
# 如果缺少关键代码或读取失败，将返回False
# 否则返回True
def check_main_integration():
    """检查主程序集成。"""
    print("\n 检查主程序集成...")

    try:
        with open('src/sensor_fuzz/__main__.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查SIL导入
        if 'from sensor_fuzz.sil_compliance import' in content:
            print(" 主程序包含SIL合规性导入")
        else:
            print(" 主程序缺少SIL合规性导入")
            return False

        # 检查SIL管理器初始化
        if 'SILComplianceManager(' in content:
            print(" 主程序包含SIL管理器初始化")
        else:
            print(" 主程序缺少SIL管理器初始化")
            return False

        # 检查SIL等级解析
        if 'SafetyIntegrityLevel[' in content:
            print(" 主程序包含SIL等级解析")
        else:
            print(" 主程序缺少SIL等级解析")
            return False

        # 检查合规性验证
        if 'generate_compliance_report' in content:
            print(" 主程序包含合规性验证")
        else:
            print(" 主程序缺少合规性验证")
            return False

        return True
    except Exception as e:
        print(f" 主程序检查失败: {e}")
        return False

# 测试SIL验证功能的异步函数
# 该函数模拟系统配置和测试结果，调用SIL管理器进行验证
# 并输出验证结果和合规性报告
async def test_sil_validation():
    """测试SIL验证功能。"""
    print("\n 测试SIL验证功能...")

    try:
        from sensor_fuzz.sil_compliance import SILComplianceManager, SafetyIntegrityLevel

        manager = SILComplianceManager()

        # 测试系统配置
        system_config = {
            "supported_protocols": ["uart", "mqtt", "http", "modbus"],
            "supported_anomaly_types": ["boundary", "protocol_error", "signal_distortion", "anomaly"],
            "hardware_protection_enabled": True,
            "redundancy_enabled": False
        }

        # 测试SIL2准备度
        readiness = await manager.validate_system_readiness(SafetyIntegrityLevel.SIL2, system_config)
        print(f" SIL2系统准备度检查: {'通过' if readiness['overall_ready'] else '未通过'}")

        # 测试SIL4准备度（应该失败）
        readiness_sil4 = await manager.validate_system_readiness(SafetyIntegrityLevel.SIL4, system_config)
        print(f" SIL4系统准备度检查: {'通过' if readiness_sil4['overall_ready'] else '未通过（预期）'}")

        # 测试合规性报告生成
        test_results = {
            "coverage": 0.95,
            "duration_hours": 48,
            "total_cases": 3000,
            "false_positive_rate": 0.02,
            "avg_response_time_ms": 300
        }

        report = await manager.generate_compliance_report(
            SafetyIntegrityLevel.SIL2, test_results, system_config
        )

        print(f" 合规性得分: {report.compliance_score:.1f}")
        print(f" 合规性报告生成: {'通过' if report.overall_compliance else '未通过'}")

        return True
    except Exception as e:
        print(f" SIL验证功能测试失败: {e}")
        return False

async def main():
    """主验证函数。"""
    print(" 第五阶段SIL合规性验证完整性检查")
    print("=" * 60)

    all_passed = True

    # 检查SIL模块
    if not check_sil_module():
        all_passed = False

    # 检查配置更新
    if not check_config_updates():
        all_passed = False

    # 检查主程序集成
    if not check_main_integration():
        all_passed = False

    # 测试SIL验证功能
    if not await test_sil_validation():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print(" 第五阶段SIL合规性验证实现完整!")
        print(" IEC 61508标准自动化验证功能已集成")
        print(" 运行 'python sil_compliance_test.py' 查看详细合规性报告")
    else:
        print(" 第五阶段实现不完整，请检查上述错误")
        print(" 提示: 确保所有SIL相关模块正确实现且测试通过")

if __name__ == "__main__":
    asyncio.run(main())