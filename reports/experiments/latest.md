# 研究实验自动化报告

- 生成时间：2026-02-18T06:45:16.208496+00:00
- 综合评分：0.6787
- 风险等级：medium

## 分项评分

- 可靠性（调度恢复）：1.0
- 稳定性（环境波动）：0.2691
- 分析质量（消融与加权）：0.66

## 实验明细

| 实验名称 | 关键指标 |
|---|---|
| envsim_stability | sample_count=3; timeline_seconds=4.5; temperature_span=2.7161; max_vibration_amplitude=0.9052 |
| distributed_reliability | tasks_total=8; tasks_done=8; tasks_failed=0; tasks_recovered=6; recovery_rate=1.0 |
| analysis_ablation | sample_count=3; critical_count=1; mean_weighted_score=0.5333; ablation_score_delta=0.85; root_cause=critical deadlock in i2c driver |

## 结论与建议

- 当前流水线已形成环境仿真、分布式可靠性、分析消融三条证据链。
- 当综合评分低于 0.65 时，建议优先提升调度恢复率和异常分析特征质量。
- 建议将本报告与原始 JSON 一同作为论文附录，保证可复现性。
