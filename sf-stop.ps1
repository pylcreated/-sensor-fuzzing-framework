# 切换到项目目录，确保 compose 文件路径正确
Set-Location $PSScriptRoot

# 停止并清理当前编排服务（不删除镜像）
docker compose -f deploy/docker-compose.yml down
