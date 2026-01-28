# 部署手册

## Docker 本地
```bash
bash deploy/scripts/deploy_linux.sh  # Windows 用 PowerShell 运行 deploy_windows.ps1
```

## K8s 部署
```bash
bash deploy/scripts/deploy_k8s.sh
```

## 多架构建议
- 使用 buildx 构建：`docker buildx build --platform linux/amd64,linux/arm64 -t sensor-fuzz:latest .`

## 依赖
- Redis（分布式调度）
- Prometheus/Grafana（监控）
- ELK（日志）
