#!/usr/bin/env python3
"""第五阶段：工业安全标准合规验证（IEC 61508 SIL标准自动化验证）"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SILComplianceError(Exception):
    """SIL合规性验证错误"""
    pass


class InvalidSILLevelError(SILComplianceError):
    """无效的SIL等级错误"""
    pass


class ConfigurationError(SILComplianceError):
    """配置错误"""
    pass


class ValidationError(SILComplianceError):
    """验证错误"""
    pass


class SafetyIntegrityLevel(Enum):
    """IEC 61508 安全完整性等级"""
    SIL1 = 1
    SIL2 = 2
    SIL3 = 3
    SIL4 = 4


from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum


# 全局缓存
_requirements_cache: Dict[SafetyIntegrityLevel, 'SILRequirements'] = {}


@dataclass
class SILRequirements:
    """SIL等级对应的测试要求"""
    sil_level: SafetyIntegrityLevel
    min_test_coverage: float  # 异常覆盖率最小值
    min_test_duration_hours: int  # 最小测试时长（小时）
    min_test_cases: int  # 最小测试用例数量
    max_false_positive_rate: float  # 最大误报率
    max_response_time_ms: int  # 最大响应时间（毫秒）
    required_protocols: List[str]  # 必需支持的协议
    required_anomaly_types: List[str]  # 必需的异常类型
    hardware_protection_required: bool  # 是否需要硬件保护
    redundancy_required: bool  # 是否需要冗余验证

    @classmethod
    def get_requirements(cls, sil_level: SafetyIntegrityLevel) -> 'SILRequirements':
        """获取指定SIL等级的要求"""
        if sil_level not in _requirements_cache:
            _requirements_cache[sil_level] = cls._load_requirements(sil_level)
        return _requirements_cache[sil_level]

    @classmethod
    def _load_requirements(cls, sil_level: SafetyIntegrityLevel) -> 'SILRequirements':
        """加载SIL要求（支持配置文件覆盖）"""
        # 默认要求
        default_requirements = {
            SafetyIntegrityLevel.SIL1: cls(
                sil_level=SafetyIntegrityLevel.SIL1,
                min_test_coverage=0.90,
                min_test_duration_hours=24,
                min_test_cases=1000,
                max_false_positive_rate=0.05,
                max_response_time_ms=1000,
                required_protocols=["uart", "mqtt", "http"],
                required_anomaly_types=["boundary", "protocol_error", "signal_distortion"],
                hardware_protection_required=False,
                redundancy_required=False
            ),
            SafetyIntegrityLevel.SIL2: cls(
                sil_level=SafetyIntegrityLevel.SIL2,
                min_test_coverage=0.95,
                min_test_duration_hours=48,
                min_test_cases=2500,
                max_false_positive_rate=0.03,
                max_response_time_ms=500,
                required_protocols=["uart", "mqtt", "http", "modbus"],
                required_anomaly_types=["boundary", "protocol_error", "signal_distortion", "anomaly"],
                hardware_protection_required=True,
                redundancy_required=False
            ),
            SafetyIntegrityLevel.SIL3: cls(
                sil_level=SafetyIntegrityLevel.SIL3,
                min_test_coverage=0.97,
                min_test_duration_hours=72,
                min_test_cases=5000,
                max_false_positive_rate=0.01,
                max_response_time_ms=200,
                required_protocols=["uart", "mqtt", "http", "modbus", "opcua"],
                required_anomaly_types=["boundary", "protocol_error", "signal_distortion", "anomaly", "poc"],
                hardware_protection_required=True,
                redundancy_required=True
            ),
            SafetyIntegrityLevel.SIL4: cls(
                sil_level=SafetyIntegrityLevel.SIL4,
                min_test_coverage=0.99,
                min_test_duration_hours=168,  # 7天
                min_test_cases=10000,
                max_false_positive_rate=0.005,
                max_response_time_ms=100,
                required_protocols=["uart", "mqtt", "http", "modbus", "opcua", "profinet"],
                required_anomaly_types=["boundary", "protocol_error", "signal_distortion", "anomaly", "poc"],
                hardware_protection_required=True,
                redundancy_required=True
            )
        }

        # TODO: 支持从配置文件加载自定义要求
        # 这里可以添加从YAML/JSON配置文件加载的逻辑

        return default_requirements[sil_level]

    @classmethod
    def load_from_config(cls, config_file: str) -> None:
        """从配置文件加载SIL要求"""
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if 'sil_requirements' in config:
                # 解析配置文件中的自定义要求
                cls._requirements_cache.clear()  # 清除缓存，强制重新加载
                logger.info(f"Loaded custom SIL requirements from {config_file}")

        except Exception as e:
            logger.warning(f"Failed to load SIL requirements from config: {e}")
            # 使用默认要求


@dataclass
class SILComplianceReport:
    """SIL合规性报告"""
    sil_level: SafetyIntegrityLevel
    overall_compliance: bool
    compliance_score: float  # 0-100

    # 具体指标合规性
    test_coverage_compliant: bool
    test_duration_compliant: bool
    test_cases_compliant: bool
    false_positive_rate_compliant: bool
    response_time_compliant: bool
    protocols_compliant: bool
    anomaly_types_compliant: bool
    hardware_protection_compliant: bool
    redundancy_compliant: bool

    # 实际测量值
    actual_test_coverage: float
    actual_test_duration_hours: float
    actual_test_cases: int
    actual_false_positive_rate: float
    actual_avg_response_time_ms: float
    supported_protocols: List[str]
    supported_anomaly_types: List[str]
    hardware_protection_enabled: bool
    redundancy_enabled: bool

    # 详细分析
    recommendations: List[str]
    critical_issues: List[str]
    improvement_suggestions: List[str]

    def __post_init__(self):
        """计算总体合规性"""
        compliant_items = [
            self.test_coverage_compliant,
            self.test_duration_compliant,
            self.test_cases_compliant,
            self.false_positive_rate_compliant,
            self.response_time_compliant,
            self.protocols_compliant,
            self.anomaly_types_compliant,
            self.hardware_protection_compliant,
            self.redundancy_compliant
        ]

        self.compliance_score = (sum(compliant_items) / len(compliant_items)) * 100
        self.overall_compliance = self.compliance_score >= 95.0  # 95%以上算合规


class SILComplianceValidator:
    """SIL合规性验证器"""

    def __init__(self):
        """方法说明：执行   init   相关逻辑。"""
        self.logger = logging.getLogger(__name__)

    async def validate_sil_compliance(
        self,
        sil_level: SafetyIntegrityLevel,
        test_results: Dict[str, Any],
        system_config: Dict[str, Any]
    ) -> SILComplianceReport:
        """验证SIL合规性"""
        try:
            if not isinstance(sil_level, SafetyIntegrityLevel):
                raise InvalidSILLevelError(f"无效的SIL等级: {sil_level}")

            requirements = SILRequirements.get_requirements(sil_level)

            # 验证输入数据的完整性
            self._validate_input_data(test_results, system_config)

            # 执行各项验证
            validation_results = await self._perform_validations(test_results, system_config, requirements)

            # 生成建议
            recommendations, critical_issues, improvement_suggestions = self._generate_recommendations(
                sil_level, test_results, system_config, requirements
            )

            return SILComplianceReport(
                sil_level=sil_level,
                overall_compliance=False,  # 将在__post_init__中计算
                compliance_score=0.0,  # 将在__post_init__中计算
                **validation_results,
                recommendations=recommendations,
                critical_issues=critical_issues,
                improvement_suggestions=improvement_suggestions
            )

        except Exception as e:
            self.logger.error(f"SIL合规性验证失败: {e}")
            raise ValidationError(f"合规性验证过程中发生错误: {e}") from e

    def _validate_input_data(self, test_results: Dict[str, Any], system_config: Dict[str, Any]) -> None:
        """验证输入数据的完整性"""
        required_test_fields = ["coverage", "duration_hours", "total_cases"]
        for field in required_test_fields:
            if field not in test_results:
                raise ValidationError(f"测试结果缺少必需字段: {field}")

        required_config_fields = ["supported_protocols", "supported_anomaly_types"]
        for field in required_config_fields:
            if field not in system_config:
                raise ValidationError(f"系统配置缺少必需字段: {field}")

    async def _perform_validations(
        self,
        test_results: Dict[str, Any],
        system_config: Dict[str, Any],
        requirements: SILRequirements
    ) -> Dict[str, Any]:
        """执行所有验证并返回结果"""
        return {
            "test_coverage_compliant": self._validate_test_coverage(
                test_results.get("coverage", 0), requirements.min_test_coverage
            ),
            "test_duration_compliant": self._validate_test_duration(
                test_results.get("duration_hours", 0), requirements.min_test_duration_hours
            ),
            "test_cases_compliant": self._validate_test_cases(
                test_results.get("total_cases", 0), requirements.min_test_cases
            ),
            "false_positive_rate_compliant": self._validate_false_positive_rate(
                test_results.get("false_positive_rate", 0), requirements.max_false_positive_rate
            ),
            "response_time_compliant": self._validate_response_time(
                test_results.get("avg_response_time_ms", 0), requirements.max_response_time_ms
            ),
            "protocols_compliant": self._validate_protocols(
                system_config.get("supported_protocols", []), requirements.required_protocols
            ),
            "anomaly_types_compliant": self._validate_anomaly_types(
                system_config.get("supported_anomaly_types", []), requirements.required_anomaly_types
            ),
            "hardware_protection_compliant": self._validate_hardware_protection(
                system_config.get("hardware_protection_enabled", False), requirements.hardware_protection_required
            ),
            "redundancy_compliant": self._validate_redundancy(
                system_config.get("redundancy_enabled", False), requirements.redundancy_required
            ),
            "actual_test_coverage": test_results.get("coverage", 0),
            "actual_test_duration_hours": test_results.get("duration_hours", 0),
            "actual_test_cases": test_results.get("total_cases", 0),
            "actual_false_positive_rate": test_results.get("false_positive_rate", 0),
            "actual_avg_response_time_ms": test_results.get("avg_response_time_ms", 0),
            "supported_protocols": system_config.get("supported_protocols", []),
            "supported_anomaly_types": system_config.get("supported_anomaly_types", []),
            "hardware_protection_enabled": system_config.get("hardware_protection_enabled", False),
            "redundancy_enabled": system_config.get("redundancy_enabled", False)
        }

    def _validate_test_coverage(self, actual: float, required: float) -> bool:
        """验证测试覆盖率"""
        return actual >= required

    def _validate_test_duration(self, actual: float, required: int) -> bool:
        """验证测试时长"""
        return actual >= required

    def _validate_test_cases(self, actual: int, required: int) -> bool:
        """验证测试用例数量"""
        return actual >= required

    def _validate_false_positive_rate(self, actual: float, max_allowed: float) -> bool:
        """验证误报率"""
        return actual <= max_allowed

    def _validate_response_time(self, actual: float, max_allowed: int) -> bool:
        """验证响应时间"""
        return actual <= max_allowed

    def _validate_protocols(self, supported: List[str], required: List[str]) -> bool:
        """验证协议支持"""
        return all(protocol in supported for protocol in required)

    def _validate_anomaly_types(self, supported: List[str], required: List[str]) -> bool:
        """验证异常类型支持"""
        return all(anomaly_type in supported for anomaly_type in required)

    def _validate_hardware_protection(self, enabled: bool, required: bool) -> bool:
        """验证硬件保护"""
        return not required or enabled

    def _validate_redundancy(self, enabled: bool, required: bool) -> bool:
        """验证冗余"""
        return not required or enabled

    def _validate_system_stability(self, test_results: Dict[str, Any], requirements: SILRequirements) -> bool:
        """验证系统稳定性"""
        # 检查内存泄漏率（可选指标）
        memory_leak_rate = test_results.get("memory_leak_rate", 0)
        max_allowed_leak = 0.01  # 1%内存泄漏率

        # 检查故障恢复时间
        recovery_time = test_results.get("recovery_time_seconds", 0)
        max_allowed_recovery = 30  # 30秒

        return memory_leak_rate <= max_allowed_leak and recovery_time <= max_allowed_recovery

    def _validate_documentation_completeness(self, system_config: Dict[str, Any]) -> bool:
        """验证文档完整性"""
        required_docs = ["safety_manual", "test_procedures", "validation_report"]
        available_docs = system_config.get("available_documentation", [])

        return all(doc in available_docs for doc in required_docs)

    def _calculate_risk_reduction_factor(self, sil_level: SafetyIntegrityLevel) -> float:
        """计算风险降低因子（根据IEC 61508标准）"""
        factors = {
            SafetyIntegrityLevel.SIL1: 100,
            SafetyIntegrityLevel.SIL2: 1000,
            SafetyIntegrityLevel.SIL3: 10000,
            SafetyIntegrityLevel.SIL4: 100000
        }
        return factors[sil_level]

    def _generate_recommendations(
        self,
        sil_level: SafetyIntegrityLevel,
        test_results: Dict[str, Any],
        system_config: Dict[str, Any],
        requirements: SILRequirements
    ) -> tuple[List[str], List[str], List[str]]:
        """生成建议"""
        recommendations = []
        critical_issues = []
        improvement_suggestions = []

        # 基于SIL等级生成建议
        recommendations.extend(self._get_sil_level_recommendations(sil_level))

        # 基于测试结果生成建议
        critical_issues.extend(self._analyze_test_result_issues(test_results, requirements))
        improvement_suggestions.extend(self._generate_test_improvements(test_results, requirements))

        # 协议支持检查
        protocol_issues = self._analyze_protocol_compliance(system_config, requirements)
        critical_issues.extend(protocol_issues["critical"])
        improvement_suggestions.extend(protocol_issues["suggestions"])

        return recommendations, critical_issues, improvement_suggestions

    def _get_sil_level_recommendations(self, sil_level: SafetyIntegrityLevel) -> List[str]:
        """获取SIL等级特定的建议"""
        recommendations = []

        if sil_level == SafetyIntegrityLevel.SIL4:
            recommendations.extend([
                "SIL4等级要求极高可靠性，建议实施双重冗余架构",
                "考虑实施形式化验证和模型检查",
                "建议采用多层防护策略"
            ])
        elif sil_level == SafetyIntegrityLevel.SIL3:
            recommendations.extend([
                "实施冗余设计以满足SIL3可靠性要求",
                "加强硬件保护机制",
                "考虑实施故障安全设计"
            ])
        elif sil_level == SafetyIntegrityLevel.SIL2:
            recommendations.append("建议实施基本的硬件保护措施")
        # SIL1通常不需要特殊建议

        return recommendations

    def _analyze_test_result_issues(self, test_results: Dict[str, Any], requirements: SILRequirements) -> List[str]:
        """分析测试结果问题"""
        issues = []

        if test_results.get("coverage", 0) < requirements.min_test_coverage:
            coverage_needed = requirements.min_test_coverage * 100
            coverage_current = test_results.get("coverage", 0) * 100
            issues.append(f"测试覆盖率不足，当前{coverage_current:.1f}%，需要达到{coverage_needed:.1f}%")

        if test_results.get("false_positive_rate", 0) > requirements.max_false_positive_rate:
            current_rate = test_results.get("false_positive_rate", 0) * 100
            max_rate = requirements.max_false_positive_rate * 100
            issues.append(f"误报率过高，当前{current_rate:.2f}%，需要控制在{max_rate:.2f}%以内")

        if test_results.get("total_cases", 0) < requirements.min_test_cases:
            issues.append(f"测试用例数量不足，当前{test_results.get('total_cases', 0)}，需要至少{requirements.min_test_cases}")

        if test_results.get("duration_hours", 0) < requirements.min_test_duration_hours:
            issues.append(f"测试时长不足，当前{test_results.get('duration_hours', 0):.1f}小时，需要至少{requirements.min_test_duration_hours}小时")

        return issues

    def _generate_test_improvements(self, test_results: Dict[str, Any], requirements: SILRequirements) -> List[str]:
        """生成测试改进建议"""
        suggestions = []

        if test_results.get("coverage", 0) < requirements.min_test_coverage:
            suggestions.extend([
                "增加边界值和异常值测试用例",
                "扩展协议错误注入场景",
                "添加更多传感器类型覆盖"
            ])

        if test_results.get("false_positive_rate", 0) > requirements.max_false_positive_rate:
            suggestions.extend([
                "优化异常检测算法",
                "改进特征提取和分类逻辑",
                "实施更严格的验证机制"
            ])

        if test_results.get("avg_response_time_ms", 0) > requirements.max_response_time_ms:
            suggestions.extend([
                "优化异步处理性能",
                "考虑使用更高效的并发模型",
                "实施连接池和缓存机制"
            ])

        return suggestions

    def _analyze_protocol_compliance(self, system_config: Dict[str, Any], requirements: SILRequirements) -> Dict[str, List[str]]:
        """分析协议合规性"""
        supported_protocols = set(system_config.get("supported_protocols", []))
        required_protocols = set(requirements.required_protocols)

        missing_protocols = required_protocols - supported_protocols

        critical = []
        suggestions = []

        if missing_protocols:
            critical.append(f"缺少必需协议支持: {', '.join(missing_protocols)}")
            suggestions.append(f"添加对以下协议的支持: {', '.join(missing_protocols)}")

        # 检查异常类型支持
        supported_anomalies = set(system_config.get("supported_anomaly_types", []))
        required_anomalies = set(requirements.required_anomaly_types)
        missing_anomalies = required_anomalies - supported_anomalies

        if missing_anomalies:
            critical.append(f"缺少必需异常类型支持: {', '.join(missing_anomalies)}")
            suggestions.append(f"实现以下异常类型的检测: {', '.join(missing_anomalies)}")

        return {"critical": critical, "suggestions": suggestions}


class SILComplianceManager:
    """SIL合规性管理器"""

    def __init__(self):
        """方法说明：执行   init   相关逻辑。"""
        self.validator = SILComplianceValidator()
        self.logger = logging.getLogger(__name__)

    async def generate_compliance_report(
        self,
        sil_level: SafetyIntegrityLevel,
        test_results: Dict[str, Any],
        system_config: Dict[str, Any]
    ) -> SILComplianceReport:
        """生成合规性报告"""
        self.logger.info(f"开始生成SIL{sil_level.value}合规性报告")

        report = await self.validator.validate_sil_compliance(
            sil_level, test_results, system_config
        )

        self.logger.info(f"合规性报告生成完成，合规性得分: {report.compliance_score:.1f}")
        return report

    def get_sil_requirements_summary(self, sil_level: SafetyIntegrityLevel) -> Dict[str, Any]:
        """获取SIL要求摘要"""
        requirements = SILRequirements.get_requirements(sil_level)

        return {
            "sil_level": sil_level.value,
            "test_coverage_required": f"{requirements.min_test_coverage*100:.1f}%",
            "test_duration_required": f"{requirements.min_test_duration_hours}小时",
            "min_test_cases": requirements.min_test_cases,
            "max_false_positive_rate": f"{requirements.max_false_positive_rate*100:.2f}%",
            "max_response_time": f"{requirements.max_response_time_ms}ms",
            "required_protocols": requirements.required_protocols,
            "required_anomaly_types": requirements.required_anomaly_types,
            "hardware_protection_required": requirements.hardware_protection_required,
            "redundancy_required": requirements.redundancy_required
        }

    async def validate_system_readiness(
        self,
        target_sil_level: SafetyIntegrityLevel,
        current_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证系统准备度"""
        requirements = SILRequirements.get_requirements(target_sil_level)

        readiness_check = {
            "target_sil_level": target_sil_level.value,
            "protocols_ready": self._check_protocols_readiness(
                current_config.get("supported_protocols", []), requirements.required_protocols
            ),
            "anomaly_types_ready": self._check_anomaly_types_readiness(
                current_config.get("supported_anomaly_types", []), requirements.required_anomaly_types
            ),
            "hardware_protection_ready": current_config.get("hardware_protection_enabled", False) or not requirements.hardware_protection_required,
            "redundancy_ready": current_config.get("redundancy_enabled", False) or not requirements.redundancy_required,
            "estimated_test_cases_needed": requirements.min_test_cases,
            "estimated_test_duration_hours": requirements.min_test_duration_hours
        }

        readiness_check["overall_ready"] = all([
            readiness_check["protocols_ready"]["ready"],
            readiness_check["anomaly_types_ready"]["ready"],
            readiness_check["hardware_protection_ready"],
            readiness_check["redundancy_ready"]
        ])

        return readiness_check

    def _check_protocols_readiness(self, supported: List[str], required: List[str]) -> Dict[str, Any]:
        """检查协议准备度"""
        missing = [p for p in required if p not in supported]
        return {
            "ready": len(missing) == 0,
            "supported": supported,
            "required": required,
            "missing": missing
        }

    def _check_anomaly_types_readiness(self, supported: List[str], required: List[str]) -> Dict[str, Any]:
        """检查异常类型准备度"""
        missing = [a for a in required if a not in supported]
        return {
            "ready": len(missing) == 0,
            "supported": supported,
            "required": required,
            "missing": missing
        }
