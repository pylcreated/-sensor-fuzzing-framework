# 配置手册

> 工业传感器模糊测试框架配置参数详解

项目主页: [https://github.com/pylcreated/-sensor-fuzzing-framework](https://github.com/pylcreated/-sensor-fuzzing-framework)

## 环境准备
- Python 3.10+
- 安装依赖：`pip install -r requirements.txt`
- 配置文件路径：`config/config.yaml`

## 配置结构
- protocols: MQTT/HTTP/Modbus/OPCUA/UART 等参数
- sensors: 量程、精度、signal_type、protocol
- strategy: anomaly_types、concurrency、duration_hours
- sil_mapping: SIL1-SIL4 覆盖率/时长/误报率

## 示例
```yaml
protocols:
  mqtt:
    host: localhost
    port: 1883
sensors:
  temperature:
    range: [0, 100]
    precision: 0.1
    signal_type: digital
strategy:
  anomaly_types: [boundary, protocol_error]
  concurrency: 10
sil_mapping:
  SIL4:
    coverage: 0.99
    max_false_positive: 0.01
```

## 常见错误
- 覆盖率未在 [0.9,1]: 修正 sil_mapping.coverage
- 缺少必填字段：range/precision/signal_type
