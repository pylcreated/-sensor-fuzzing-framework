# 在项目根目录执行，避免 compose 相对路径解析错误
Set-Location $PSScriptRoot

# 先输出容器状态，再进行 HTTP 健康检查
docker compose -f deploy/docker-compose.yml ps
$maxAttempts = 3
$delaySeconds = 2
$lastDashboardError = $null
$lastMetricsError = $null

# 健康检查重试：避免容器刚启动时的瞬时连接失败
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $dashboardOk = $false
    $metricsOk = $false

    try {
        $dashboardResp = Invoke-WebRequest -UseBasicParsing http://localhost:8080/api/health -TimeoutSec 10
        if ($dashboardResp.StatusCode -eq 200) {
            $dashboardOk = $true
        }
    }
    catch {
        $lastDashboardError = $_.Exception.Message
    }

    try {
        $metricsResp = Invoke-WebRequest -UseBasicParsing http://localhost:8000/metrics -TimeoutSec 10
        if ($metricsResp.StatusCode -eq 200) {
            $metricsOk = $true
        }
    }
    catch {
        $lastMetricsError = $_.Exception.Message
    }

    if ($dashboardOk -and $metricsOk) {
        Write-Host "DASHBOARD_STATUS=200 (http://localhost:8080)"
        Write-Host "METRICS_STATUS=200 (http://localhost:8000/metrics)"
        exit 0
    }

    if ($attempt -lt $maxAttempts) {
        Start-Sleep -Seconds $delaySeconds
    }
}

Write-Host "HTTP_CHECK_FAILED"
if ($lastDashboardError) {
    Write-Host "Dashboard check failed: $lastDashboardError"
}
if ($lastMetricsError) {
    Write-Host "Metrics check failed: $lastMetricsError"
}
exit 1
