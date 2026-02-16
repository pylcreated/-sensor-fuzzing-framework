# 工业传感器模糊测试框架（V2.0）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://github.com/pylcreated/-sensor-fuzzing-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/pylcreated/-sensor-fuzzing-framework/actions)

> 从 0 到 1 的工业级模糊测试框架骨架，覆盖配置管理、数据生成、执行引擎、监控反馈、结果分析、分布式调度与安全防护。

特性

模块化设计：核心模块独立，可扩展
SIL合规：满足工业安全完整性等级要求
实时监控：内置监控面板和指标导出
多协议支持：Modbus、OPC UA、MQTT、PROFIBUS等
AI增强：遗传算法和LSTM预测优化
容器化部署：Docker/K8s支持
分布式执行：Go语言实现的高性能调度

获取方式

快速开始（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/pylcreated/-sensor-fuzzing-framework.git
cd -sensor-fuzzing-framework

# 2. 创建虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行验证
python -m sensor_fuzz
```

Docker部署

```bash
# 使用Docker Compose一键部署
docker-compose -f deploy/docker-compose.yml up -d

# 访问Web界面: http://localhost:8000
# 监控面板: http://localhost:8080
```

Python包安装

```bash
# 从源码安装（当前适用）
pip install -e .

# 或从wheel文件安装
pip install sensor_fuzz_framework-0.1.0-py3-none-any.whl
```

文件包分发

```bash
# 使用快速部署脚本（推荐）
# Linux/macOS
./setup_and_run.sh sensor-fuzzing-framework.zip

# Windows PowerShell
.\setup_and_run.ps1 -ZipFile "sensor-fuzzing-framework.zip"

# 或下载最新分发包: https://github.com/pylcreated/-sensor-fuzzing-framework/releases
```

详细文档

- [用户手册](docs/USER.md) - 功能使用指南
- [开发手册](docs/DEV.md) - 代码开发规范
- [部署手册](docs/DEPLOY.md) - 部署配置说明
- [分发指南](docs/DISTRIBUTION.md) - 文件获取方式
- [配置参考](docs/CONFIG.md) - 配置参数详解

目录结构（初始骨架）

- src/  Python 主框架代码（核心与辅助模块）
- go/   分布式调度与集群协作（Go 实现）
- deploy/ Docker 镜像与 Kubernetes 清单、一键脚本
- docs/ 需求与技术文档（本仓库包含 V2.0 需求）
- tests/ 单元与集成测试

快速开始（骨架阶段）

1) 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

2) 运行基础自检（待后续补充测试用例）：

```bash
pytest -q
```

3) 运行SIL合规测试：

```bash
python sil_compliance_test.py
```

4) 访问Web界面验证：
- 主界面: http://localhost:8000
- 监控面板: http://localhost:8080

开发节奏

- 优先完成核心模块（配置管理、数据生成、执行引擎、监控反馈、结果分析），随后补齐辅助模块与智能化扩展。
- 保持单元测试覆盖率≥80%，按需添加性能与安全测试脚本。
- CI/CD、Docker、K8s 清单将在模块稳定后补充。

兼容性与约束

- Python 3.10+
- 支持 Windows 10/11、Ubuntu 20.04/22.04、CentOS 7/8、OpenWrt 21.02、麒麟 OS / 统信 UOS
- CPU 架构：x86_64 / ARMv7 / ARMv8

贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

开发规范

- 遵循 PEP 8 代码风格
- 添加单元测试，保持覆盖率 ≥80%
- 更新相关文档
- 提交前运行 `pytest` 和 `sil_compliance_test.py`

许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

联系方式

- 项目维护者: [pylcreated](https://github.com/pylcreated)
- 问题反馈: [GitHub Issues](https://github.com/pylcreated/-sensor-fuzzing-framework/issues)
- 邮箱: pylcreated@example.com

常见问题

**Q: 如何配置传感器协议？**
A: 编辑 `config/sensor_protocol_config.yaml` 文件，参考 `docs/CONFIG.md`。

**Q: 支持哪些操作系统？**
A: Windows 10/11、Ubuntu 20.04+、CentOS 7/8、麒麟OS等。

**Q: 如何扩展新协议？**
A: 在 `src/sensor_fuzz/engine/drivers/` 中添加驱动，参考现有实现。

**Q: 遇到权限错误怎么办？**
A: 以管理员身份运行，或检查文件权限设置。

更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新详情。

致谢

感谢所有贡献者和测试人员的支持！
