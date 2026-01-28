# 开发手册

## 代码规范
- flake8 / pylint 配置见仓库根目录。
- 测试：`pytest -q`，覆盖率配置在 pytest.ini/.coveragerc。

## 模块概览
- config: 配置加载、SIL 校验、热重载、版本存储。
- data_gen: 边界/异常/协议错误/信号失真/POC、自适应变异、预校验。
- engine: 驱动适配、并发调度、断点续测、指标计数。
- monitoring: Prometheus、pyshark 抓包、ELK sink、外设/环境监控。
- analysis: 聚类、根因定位占位、严重度、报告生成。
- security: AES-256、权限、审计、硬件阈值守护。
- ai: LSTM 异常预测、遗传/RL 用例生成。
- go/scheduler: Redis 队列、K8s 客户端占位、Worker。

## 扩展 SDK
- 在 data_gen 中添加新的 mutation 函数并在 engine._build_cases 聚合。
- 在 security/access_control 中添加新角色/权限。
