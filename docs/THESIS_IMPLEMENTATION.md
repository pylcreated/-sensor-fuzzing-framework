# 论文实现与实验设计（可复现说明）

本文系统实现围绕三条主线展开，并通过统一实验流水线生成可复现结果。

## 1. 环境仿真实验（envsim）

实现位置：`src/sensor_fuzz/envsim/simulator.py`

- 提供温度、光照、振动的统一状态建模。
- 支持步骤化场景回放（scenario replay）。
- 支持高斯噪声注入，用于构造更接近真实工况的数据扰动。

核心指标：
- `sample_count`：采样点数量
- `timeline_seconds`：场景总时长
- `temperature_span`：温度波动区间
- `max_vibration_amplitude`：最大振动幅值

## 2. 分布式可靠性实验（distributed）

实现位置：`src/sensor_fuzz/distributed/scheduler_client.py`

- 任务状态机：`queued -> in_progress -> done/failed`
- 支持重试机制与幂等键去重。
- 支持心跳与超时任务回收（stale requeue）。
- 当 Redis 不可用时自动降级为内存后备，保证实验可运行。

核心指标：
- `tasks_total`：总任务数
- `tasks_done`：完成任务数
- `tasks_failed`：失败任务数
- `tasks_recovered`：超时后恢复任务数
- `recovery_rate`：恢复后的总体完成率

## 3. 分析与消融实验（analysis）

实现位置：
- `src/sensor_fuzz/analysis/severity.py`
- `src/sensor_fuzz/analysis/root_cause.py`

- 严重度分类支持规则策略与加权策略。
- 提供特征消融开关（ablation），用于验证特征贡献。
- 根因定位支持首个高危事件与评分策略两种模式。

核心指标：
- `critical_count`：高危样本数量
- `mean_weighted_score`：平均加权严重度分值
- `ablation_score_delta`：消融前后分值差异
- `root_cause`：定位出的根因描述

## 4. 统一实验流水线

实现位置：`src/sensor_fuzz/automation/experiment_pipeline.py`

统一入口：
- 代码调用：`run_research_pipeline("reports/experiments/latest.json")`
- 主流程触发：在配置中设置 `strategy.research_pipeline: true`
- 或环境变量触发：`SENSOR_FUZZ_RESEARCH_PIPELINE=1`

输出文件：
- `reports/experiments/latest.json`
- `reports/experiments/latest.md`

JSON 文件包含时间戳与三组实验结果；Markdown 文件包含综合评分、风险等级、实验明细与结论建议，可直接用于论文附录。

## 5. 复现实验步骤

1. 启动项目主程序：`python -m sensor_fuzz`
2. 启用研究流水线（任选其一）：
   - 配置项：`strategy.research_pipeline: true`
   - 环境变量：`SENSOR_FUZZ_RESEARCH_PIPELINE=1`
3. 运行后查看输出：`reports/experiments/latest.json`
4. 使用该 JSON 中指标绘制论文图表（稳定性、可靠性、消融对比）。

## 6. 与论文章节建议映射

- 系统设计章节：描述三条主线实现结构。
- 实验章节：直接使用 `latest.json` 指标与图表。
- 可复现性章节：给出开关配置、输出路径和测试命令。
