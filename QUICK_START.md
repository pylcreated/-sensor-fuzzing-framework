# 快速开始指南

欢迎使用工业传感器模糊测试框架

本框架是一个完整的工业级模糊测试解决方案，支持IEC 61508 SIL安全标准合规验证。

项目地址: [https://github.com/pylcreated/-sensor-fuzzing-framework](https://github.com/pylcreated/-sensor-fuzzing-framework)

快速启动（推荐）

Windows用户
```powershell
# 方法1：运行自动化脚本（推荐）
.\setup_and_run.ps1

# 方法2：手动安装
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m sensor_fuzz
```

Linux/macOS用户
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

系统要求

Python: 3.10 或更高版本
内存: 至少 4GB RAM
磁盘: 至少 10GB 可用空间
操作系统: Windows 10+/Ubuntu 20.04+/CentOS 7+

核心功能

多协议支持: UART, MQTT, Modbus, OPC UA, Profinet, I2C, SPI
安全合规: IEC 61508 SIL1-SIL4 完整支持
智能测试: AI异常检测 + 遗传算法优化
监控告警: Prometheus + Grafana 实时监控
分布式调度: Redis队列 + Kubernetes支持

访问界面

安装完成后，访问以下地址：

- **Web管理界面**: http://localhost:8000
- **监控仪表板**: http://localhost:8080
- **Prometheus指标**: http://localhost:9090
- **Grafana面板**: http://localhost:3000

验证安装

```bash
# 1. 测试模块导入
python -c "import sensor_fuzz; print(' 模块导入成功')"

# 2. 运行SIL合规测试
python sil_compliance_test.py

# 3. 查看帮助信息
python -m sensor_fuzz --help
```

详细文档

- [用户手册](docs/USER.md) - 功能使用指南
- [配置参考](docs/CONFIG.md) - 配置参数详解
- [部署手册](docs/DEPLOY.md) - 高级部署选项
- [分发指南](docs/DISTRIBUTION.md) - 获取和分发说明

故障排除

常见问题

**Q: 安装时提示权限错误？**
A: 请以管理员身份运行，或使用虚拟环境

**Q: Python版本不兼容？**
A: 请使用Python 3.10 或更高版本

**Q: 端口被占用？**
A: 修改 `config/sensor_protocol_config.yaml` 中的端口配置

**Q: 内存不足？**
A: 增加系统内存，或调整 `config/memory_config.yaml` 中的池大小

获取帮助

- 查看 [故障排除文档](docs/TROUBLESHOOTING.md)
- 联系项目维护者
- 查看GitHub Issues（如果有仓库）

开始使用

1. **配置传感器**: 编辑 `config/sensor_protocol_config.yaml`
2. **选择协议**: 配置所需的工业协议参数
3. **设置SIL等级**: 选择目标安全完整性等级
4. **启动测试**: 运行 `python -m sensor_fuzz`
5. **监控结果**: 通过Web界面查看测试进度和结果

祝您使用愉快！</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\QUICK_START.md