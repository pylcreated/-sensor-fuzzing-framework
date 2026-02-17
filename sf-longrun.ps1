param(
    [double]$Hours = 48,
    [int]$IntervalMinutes = 60,
    [switch]$SkipTests,
    [switch]$UseMirror
)

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$env:SENSOR_FUZZ_LONGRUN_ENABLED = "1"
$env:SENSOR_FUZZ_LONGRUN_HOURS = [string]$Hours
$env:SENSOR_FUZZ_LONGRUN_INTERVAL_MINUTES = [string]$IntervalMinutes

Write-Host "Long-run mode enabled" -ForegroundColor Green
Write-Host "Hours=$Hours, IntervalMinutes=$IntervalMinutes" -ForegroundColor Cyan

if ($UseMirror) {
    .\sf-start.ps1 -SkipTests:$SkipTests -UseMirror
}
else {
    .\sf-start.ps1 -SkipTests:$SkipTests
}
