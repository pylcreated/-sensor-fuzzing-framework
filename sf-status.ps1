# 在项目根目录执行，避免 compose 相对路径解析错误
Set-Location $PSScriptRoot

# 先输出容器状态，再进行 HTTP 健康检查
docker compose -f deploy/docker-compose.yml ps
$maxAttempts = 3
$delaySeconds = 2
$lastError = $null

# 健康检查重试：避免容器刚启动时的瞬时连接失败
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    try {
        $resp = Invoke-WebRequest -UseBasicParsing http://localhost:8000 -TimeoutSec 10
        Write-Host "HTTP_STATUS=$($resp.StatusCode)"
        exit 0
    }
    catch {
        $lastError = $_.Exception.Message
        if ($attempt -lt $maxAttempts) {
            Start-Sleep -Seconds $delaySeconds
        }
    }
}

Write-Host "HTTP_CHECK_FAILED"
Write-Host $lastError
exit 1
