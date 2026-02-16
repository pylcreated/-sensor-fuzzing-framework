#!/usr/bin/env python3
"""SIL合规性验证单元测试"""

import pytest
import asyncio
from unittest.mock import Mock, patch

# 导入SIL合规性相关模块
from sensor_fuzz.sil_compliance import (
    SILComplianceManager,
    SafetyIntegrityLevel,
    SILRequirements,
    SILComplianceValidator,
    SILComplianceReport
)


# 定义测试SIL要求的测试类
class TestSILRequirements:
    """测试SIL要求"""

    def test_get_sil1_requirements(self):
        """测试SIL1要求"""
        # 获取SIL1的要求并验证其属性
        req = SILRequirements.get_requirements(SafetyIntegrityLevel.SIL1)

        assert req.sil_level == SafetyIntegrityLevel.SIL1
        assert req.min_test_coverage == 0.90
        assert req.min_test_duration_hours == 24
        assert req.min_test_cases == 1000
        assert req.max_false_positive_rate == 0.05
        assert req.hardware_protection_required is False
        assert req.redundancy_required is False

    def test_get_sil4_requirements(self):
        """测试SIL4要求"""
        # 获取SIL4的要求并验证其属性
        req = SILRequirements.get_requirements(SafetyIntegrityLevel.SIL4)

        assert req.sil_level == SafetyIntegrityLevel.SIL4
        assert req.min_test_coverage == 0.99
        assert req.min_test_duration_hours == 168  # 7天
        assert req.min_test_cases == 10000
        assert req.max_false_positive_rate == 0.005
        assert req.hardware_protection_required is True
        assert req.redundancy_required is True


# 定义测试SIL合规性验证器的测试类
class TestSILComplianceValidator:
    """测试SIL合规性验证器"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return SILComplianceValidator()

    @pytest.mark.asyncio
    async def test_validate_sil1_compliance_success(self, validator):
        """测试SIL1合规性验证成功"""
        # 定义测试结果和系统配置
        test_results = {
            "coverage": 0.95,
            "duration_hours": 30,
            "total_cases": 1500,
            "false_positive_rate": 0.03,
            "avg_response_time_ms": 800
        }

        system_config = {
            "supported_protocols": ["uart", "mqtt", "http"],
            "supported_anomaly_types": ["boundary", "protocol_error", "signal_distortion"],
            "hardware_protection_enabled": False,
            "redundancy_enabled": False
        }

        # 验证SIL1合规性
        report = await validator.validate_sil_compliance(
            SafetyIntegrityLevel.SIL1, test_results, system_config
        )

        # 验证报告的属性
        assert isinstance(report, SILComplianceReport)
        assert report.sil_level == SafetyIntegrityLevel.SIL1
        assert report.overall_compliance is True
        assert report.compliance_score >= 95.0

    @pytest.mark.asyncio
    async def test_validate_sil4_compliance_failure(self, validator):
        """测试SIL4合规性验证失败"""
        # 定义测试结果和系统配置（不满足SIL4要求）
        test_results = {
            "coverage": 0.90,  # SIL4需要0.99
            "duration_hours": 100,  # SIL4需要168
            "total_cases": 5000,  # SIL4需要10000
            "false_positive_rate": 0.01,  # SIL4需要0.005
            "avg_response_time_ms": 200
        }

        system_config = {
            "supported_protocols": ["uart", "mqtt", "http"],  # SIL4需要更多协议
            "supported_anomaly_types": ["boundary"],  # SIL4需要更多异常类型
            "hardware_protection_enabled": False,  # SIL4需要硬件保护
            "redundancy_enabled": False  # SIL4需要冗余
        }

        # 验证SIL4合规性
        report = await validator.validate_sil_compliance(
            SafetyIntegrityLevel.SIL4, test_results, system_config
        )

        # 验证报告的属性
        assert isinstance(report, SILComplianceReport)
        assert report.sil_level == SafetyIntegrityLevel.SIL4
        assert report.overall_compliance is False
        assert report.compliance_score < 95.0
        assert len(report.critical_issues) > 0


# 定义测试SIL合规性管理器的测试类
class TestSILComplianceManager:
    """测试SIL合规性管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return SILComplianceManager()

    def test_get_sil_requirements_summary(self, manager):
        """测试获取SIL要求摘要"""
        summary = manager.get_sil_requirements_summary(SafetyIntegrityLevel.SIL2)

        assert summary["sil_level"] == 2
        assert "95.0%" in summary["test_coverage_required"]
        assert "48小时" in summary["test_duration_required"]
        assert summary["min_test_cases"] == 2500

    @pytest.mark.asyncio
    async def test_validate_system_readiness_sil1(self, manager):
        """测试SIL1系统准备度验证"""
        config = {
            "supported_protocols": ["uart", "mqtt", "http"],
            "supported_anomaly_types": ["boundary", "protocol_error", "signal_distortion"],
            "hardware_protection_enabled": False,
            "redundancy_enabled": False
        }

        readiness = await manager.validate_system_readiness(SafetyIntegrityLevel.SIL1, config)

        assert readiness["target_sil_level"] == 1
        assert readiness["overall_ready"] is True
        assert readiness["protocols_ready"]["ready"] is True
        assert readiness["anomaly_types_ready"]["ready"] is True

    @pytest.mark.asyncio
    async def test_validate_system_readiness_sil4_incomplete(self, manager):
        """测试SIL4系统准备度验证（不完整）"""
        config = {
            "supported_protocols": ["uart", "mqtt"],  # 缺少必需协议
            "supported_anomaly_types": ["boundary"],  # 缺少异常类型
            "hardware_protection_enabled": False,  # 需要硬件保护
            "redundancy_enabled": False  # 需要冗余
        }

        readiness = await manager.validate_system_readiness(SafetyIntegrityLevel.SIL4, config)

        assert readiness["target_sil_level"] == 4
        assert readiness["overall_ready"] is False
        assert readiness["protocols_ready"]["ready"] is False
        assert readiness["anomaly_types_ready"]["ready"] is False
        assert readiness["hardware_protection_ready"] is False
        assert readiness["redundancy_ready"] is False

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, manager):
        """测试生成合规性报告"""
        test_results = {
            "coverage": 0.96,
            "duration_hours": 72,
            "total_cases": 5000,
            "false_positive_rate": 0.008,
            "avg_response_time_ms": 150
        }

        system_config = {
            "supported_protocols": ["uart", "mqtt", "http", "modbus", "opcua"],
            "supported_anomaly_types": ["boundary", "protocol_error", "signal_distortion", "anomaly", "poc"],
            "hardware_protection_enabled": True,
            "redundancy_enabled": False
        }

        report = await manager.generate_compliance_report(
            SafetyIntegrityLevel.SIL3, test_results, system_config
        )

        assert isinstance(report, SILComplianceReport)
        assert report.sil_level == SafetyIntegrityLevel.SIL3
        assert hasattr(report, 'compliance_score')
        assert hasattr(report, 'overall_compliance')
        assert hasattr(report, 'recommendations')
        assert hasattr(report, 'critical_issues')


# 定义测试SIL合规性报告的测试类
class TestSILComplianceReport:
    """测试SIL合规性报告"""

    def test_report_creation_and_compliance_calculation(self):
        """测试报告创建和合规性计算"""
        # 创建一个完全合规的报告
        report = SILComplianceReport(
            sil_level=SafetyIntegrityLevel.SIL2,
            overall_compliance=False,  # 将被__post_init__覆盖
            compliance_score=0.0,  # 将被__post_init__覆盖

            test_coverage_compliant=True,
            test_duration_compliant=True,
            test_cases_compliant=True,
            false_positive_rate_compliant=True,
            response_time_compliant=True,
            protocols_compliant=True,
            anomaly_types_compliant=True,
            hardware_protection_compliant=True,
            redundancy_compliant=True,

            actual_test_coverage=0.96,
            actual_test_duration_hours=50,
            actual_test_cases=3000,
            actual_false_positive_rate=0.02,
            actual_avg_response_time_ms=300,
            supported_protocols=["uart", "mqtt", "http", "modbus"],
            supported_anomaly_types=["boundary", "protocol_error", "signal_distortion", "anomaly"],
            hardware_protection_enabled=True,
            redundancy_enabled=False,

            recommendations=[],
            critical_issues=[],
            improvement_suggestions=[]
        )

        # 验证合规性计算
        assert report.compliance_score == 100.0  # 9/9 项合规
        assert report.overall_compliance is True  # >= 95%

    def test_report_partial_compliance(self):
        """测试部分合规的报告"""
        report = SILComplianceReport(
            sil_level=SafetyIntegrityLevel.SIL3,
            overall_compliance=False,
            compliance_score=0.0,

            test_coverage_compliant=True,
            test_duration_compliant=True,
            test_cases_compliant=False,  # 不合规
            false_positive_rate_compliant=True,
            response_time_compliant=False,  # 不合规
            protocols_compliant=True,
            anomaly_types_compliant=True,
            hardware_protection_compliant=True,
            redundancy_compliant=False,  # 不合规

            actual_test_coverage=0.97,
            actual_test_duration_hours=72,
            actual_test_cases=4000,  # SIL3需要5000
            actual_false_positive_rate=0.008,
            actual_avg_response_time_ms=250,  # SIL3需要<=200
            supported_protocols=["uart", "mqtt", "http", "modbus", "opcua"],
            supported_anomaly_types=["boundary", "protocol_error", "signal_distortion", "anomaly", "poc"],
            hardware_protection_enabled=True,
            redundancy_enabled=False,  # SIL3需要冗余

            recommendations=["实施冗余设计以满足SIL3可靠性要求"],
            critical_issues=["测试用例数量不足，需要达到5000"],
            improvement_suggestions=["增加测试用例数量", "优化响应时间"]
        )

        # 验证合规性计算：6/9 项合规 = 66.7%
        assert abs(report.compliance_score - 66.7) < 0.1
        assert report.overall_compliance is False  # < 95%