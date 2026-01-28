# 部署手册

> 工业传感器模糊测试框架部署配置说明

项目主页: [https://github.com/pylcreated/-sensor-fuzzing-framework](https://github.com/pylcreated/-sensor-fuzzing-framework)

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
