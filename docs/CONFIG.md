# 配置手册

> 工业传感器模糊测试框架配置参数详解

项目主页: [https://github.com/pylcreated/-sensor-fuzzing-framework](https://github.com/pylcreated/-sensor-fuzzing-framework)

## 环境准备
- Python 3.10+
- 安装依赖：`pip install -r requirements.txt`
- 配置文件路径：`config/config.yaml`

## 配置加载优先级

程序启动时按以下顺序寻找配置：

1. `SENSOR_FUZZ_CONFIG_FILE`（显式文件路径，最高优先级）
2. `SF_CONFIG`（显式文件路径，兼容部署场景）
3. `SENSOR_FUZZ_CONFIG_PATH`
   - 若为目录，自动拼接 `config.yaml`
   - 若为文件路径，直接使用
4. 默认路径：`config/config.yaml`
5. 兼容回退：`config/sensor_protocol_config.yaml`

若以上路径都不可用，程序会在启动阶段报错退出。

## 环境变量示例

### 本地开发（PowerShell）
```powershell
$env:SENSOR_FUZZ_CONFIG_FILE = "config/config.yaml"
python -m sensor_fuzz
```

### Kubernetes（已在部署清单中使用）
```yaml
env:
  - name: SF_CONFIG
    value: /app/config/config.yaml
```

## 配置结构
- protocols: MQTT/HTTP/Modbus/OPCUA/UART 等参数
- sensors: 量程、精度、signal_type、protocol
- strategy: anomaly_types、concurrency、duration_hours、fault_injection_rate
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
  fault_injection_rate: 0.0
sil_mapping:
  SIL4:
    coverage: 0.99
    max_false_positive: 0.01
```

## 常见错误
- 覆盖率未在 [0.9,1]: 修正 sil_mapping.coverage
- 缺少必填字段：range/precision/signal_type

## 异常注入（联调看板推荐）
- 配置方式：`strategy.fault_injection_rate: 0.2`（表示约 20% 用例被标记为异常）
- 环境变量覆盖：`SENSOR_FUZZ_FAULT_INJECTION_RATE=0.2`
- 默认值为 `0.0`，即不注入，保持真实结果统计。
