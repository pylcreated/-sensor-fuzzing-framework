# 最终交付与验收清单

## 代码与配置
- Python 主框架：src/
- Go 调度：go/
- 配置示例：config/config.yaml
- 依赖：requirements.txt, pyproject.toml

## 部署
- Dockerfile（含 Go 调度多阶段）
- K8s 清单：deploy/k8s/*.yaml
- 一键脚本：deploy/scripts/*.sh, deploy/scripts/deploy_windows.ps1

## 文档
- CONFIG.md, USER.md, DEV.md, DEPLOY.md
- REPORT_TEMPLATE.tex, DIAGRAMS.mmd, PERF_PLAN.md
- PERF_REPORT_SAMPLE.md, SECURITY_REPORT_SAMPLE.md
- DELIVERY.md（总体清单）

## 测试
- pytest 用例：tests/*.py
- 性能/安全指引与样例：tests/perf, tests/security
- 覆盖率配置：pytest.ini, .coveragerc

## 验收建议
- 按 PERF_PLAN 执行并填充 PERF_REPORT_SAMPLE/SECURITY_REPORT_SAMPLE。
- 验证 Prometheus/Grafana、ELK、Redis、K8s 集群可用。
- 生成 HTML/PDF 报告（analysis/report.py）。
