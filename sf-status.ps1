Set-Location $PSScriptRoot

docker compose -f deploy/docker-compose.yml ps
$maxAttempts = 3
$delaySeconds = 2
$lastError = $null

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
