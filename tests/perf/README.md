# 性能测试指引

- 目标：单节点 >=100 TPS，分布式调度 >=500 TPS；CPU<=30%，内存<=500MB；72h 内存泄漏<=0.01%。
- 工具：JMeter/LoadRunner；Redis+K8s 用于分布式。

## 快速执行（示例）
```bash
jmeter -n -t tests/perf/mqtt_plan.jmx -l results.jtl
```

## 监控
- Prometheus/Grafana 采集 CPU/内存/TPS。
- ELK 收集异常日志。

## 结果记录
- 将吞吐量、响应时间曲线、资源占用写入 PERF_PLAN.md 要求的表格或图表。
