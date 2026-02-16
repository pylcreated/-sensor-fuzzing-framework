# Sensor Fuzzing Framework - Quick Setup Script (Windows)
# Usage: .\setup_and_run.ps1 -ZipFile "path\to\sensor-fuzzing-framework.zip"

param(
    [Parameter(Mandatory=$true)]
    [string]$ZipFile,

    [switch]$SkipValidation
)

Write-Host "Sensor Fuzzing Framework - Quick Setup" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

if (-not (Test-Path $ZipFile)) {
    Write-Host "File not found: $ZipFile" -ForegroundColor Red
    exit 1
}

Write-Host "Extracting project archive..." -ForegroundColor Yellow
$ProjectDir = [System.IO.Path]::GetFileNameWithoutExtension($ZipFile)
Expand-Archive -Path $ZipFile -DestinationPath $ProjectDir -Force
Set-Location $ProjectDir

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv
.venv\Scripts\activate

Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not $SkipValidation) {
    Write-Host "Validating installation..." -ForegroundColor Yellow
    try {
        python -c "import sensor_fuzz; print('Import ok')"
        Write-Host "Validation succeeded." -ForegroundColor Green
    } catch {
        Write-Host "Validation failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Starting framework..." -ForegroundColor Green
Write-Host "Tip: press Ctrl+C to stop" -ForegroundColor Cyan
python -m sensor_fuzz
