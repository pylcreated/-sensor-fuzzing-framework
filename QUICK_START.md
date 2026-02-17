# 快速开始指南

## 环境准备

### Windows 用户
```powershell
# 方法1：运行自动化脚本（推荐）
.\setup_and_run.ps1

# 方法2：手动安装
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m sensor_fuzz
```

### Linux/macOS 用户
```bash
# 方法1：运行自动化脚本（推荐）
chmod +x setup_and_run.sh
./setup_and_run.sh

# 方法2：手动安装
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m sensor_fuzz
```

## 系统要求
- Python: 3.10 或更高版本
- 内存: 至少 4GB RAM
- 磁盘: 至少 10GB 可用空间
- 操作系统: Windows 10+/Ubuntu 20.04+/CentOS 7+

## 核心功能
- 多协议支持: UART, MQTT, Modbus, OPC UA, Profinet, I2C, SPI
- 安全合规: IEC 61508 SIL1-SIL4 完整支持
- 智能测试: AI异常检测 + 遗传算法优化
- 监控告警: Prometheus + Grafana 实时监控
- 分布式调度: Redis队列 + Kubernetes支持