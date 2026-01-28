# 性能与安全测试计划

## 性能
- 单节点 2100 并发：使用 JMeter/LoadRunner 驱动 MQTT/HTTP，指标：TPS>=100，CPU<=30%，内存<=500MB。
- 分布式：Redis + K8s 横向扩展，目标吞吐>=500 TPS（Go 调度）。
- 72h 长稳：监控内存泄漏率<=0.01%。

## 安全
- POC 覆盖率>=90%，记录使用审计。
- 硬件保护：电压>=阈值即切断，准确率>=99.9%。

## 数据完整性
- Prometheus/Grafana 持续观测资源；ELK 记录异常日志。

## 执行示例
- `jmeter -n -t plans/mqtt.jmx -l results.jtl`
- `go test ./go/...` （需 Redis）
