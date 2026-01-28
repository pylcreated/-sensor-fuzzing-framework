# 用户手册

> 工业传感器模糊测试框架使用指南

项目主页: [https://github.com/pylcreated/-sensor-fuzzing-framework](https://github.com/pylcreated/-sensor-fuzzing-framework)

## 内存优化配置

框架采用对象池技术优化内存使用，支持以下配置参数：

### 对象池配置
```yaml
memory:
  case_pool_size: 200        # 用例对象池大小
  connection_pool_size: 50   # 连接对象池大小
  log_pool_size: 500         # 日志对象池大小
  pool_timeout: 300          # 池对象超时时间(秒)
  cleanup_interval: 60       # 清理间隔(秒)
```

### 池大小调整规则
- **用例对象池**: 根据测试用例复杂度调整，复杂传感器建议 200-500
- **连接对象池**: 根据并发连接数调整，建议为最大并发数的 2-3 倍
- **日志对象池**: 根据日志频率调整，高频日志建议 500-1000

### 内存监控
运行内存测试脚本验证优化效果：
```bash
# 基本内存测试
python memory_test.py

# 72小时稳定性测试
python memory_stability_test.py

# 快速测试(1小时)
python memory_stability_test.py --quick
```

### 预期指标
- 单节点内存占用: ≤ 350 MB
- 内存泄漏率: ≤ 0.005% (72小时连续运行)
- 对象复用率: ≥ 80%

## 启动
```bash
python -m sensor_fuzz
```
默认加载 `config/config.yaml`，启动热重载与基础执行。

## 测试流程
1. 准备配置文件（协议、传感器、策略、SIL）。
2. 启动 Prometheus 导出（内置 9000 端口）。
3. 运行执行引擎或通过分布式调度入队任务。

## 故障排查
- 无法连接 MQTT：检查 host/port 与防火墙。
- pyshark 抓包失败：确认本机安装 tshark 并有权限。
- 报告生成失败：确认已安装 WeasyPrint 运行时依赖。
- 内存占用过高：检查对象池配置，运行内存测试脚本诊断。
