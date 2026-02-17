# 工业传感器模糊测试框架（V2.0）

## 项目概述

本项目旨在提供一个完整的工业级模糊测试解决方案，覆盖配置管理、数据生成、执行引擎、监控反馈、结果分析、分布式调度与安全防护。

### 核心功能
- 模块化设计：核心模块独立，可扩展
- SIL合规：满足工业安全完整性等级要求
- 实时监控：内置监控面板和指标导出
- 多协议支持：Modbus、OPC UA、MQTT、PROFIBUS等
- AI增强：遗传算法和LSTM预测优化
- 容器化部署：Docker/K8s支持
- 分布式执行：Go语言实现的高性能调度

## 快速开始

### 环境准备

```bash
# 克隆项目
$ git clone https://github.com/pylcreated/-sensor-fuzzing-framework.git
$ cd -sensor-fuzzing-framework

# 创建虚拟环境
$ python -m venv .venv
$ source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# 安装依赖
$ pip install -r requirements.txt
```

### 启动服务

```bash
# 启动核心服务
$ python -m sensor_fuzz

# 访问监控面板: http://localhost:8080
# 查看指标端点: http://localhost:8000/metrics
```
