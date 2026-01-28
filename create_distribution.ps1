# Create distribution package for Sensor Fuzzing Framework (Windows)
# Usage: .\create_distribution.ps1

param(
    [string]$OutputDir = "dist",
    [switch]$IncludeTests,
    [switch]$SkipBuild
)

Write-Host "Create distribution package" -ForegroundColor Green
Write-Host "===========================" -ForegroundColor Green

# Create timestamp for version
$Timestamp = Get-Date -Format "yyyyMMdd"
$DistName = "sensor-fuzzing-framework-$Timestamp"

Write-Host "Create directory: $DistName" -ForegroundColor Yellow

# Create distribution directory
New-Item -ItemType Directory -Path $DistName -Force | Out-Null

# Copy essential files and directories
Write-Host "Copy project files..." -ForegroundColor Yellow

# Core source code
Copy-Item -Path "src" -Destination "$DistName\" -Recurse -Force
Copy-Item -Path "config" -Destination "$DistName\" -Recurse -Force

# Documentation
Copy-Item -Path "docs" -Destination "$DistName\" -Recurse -Force
Copy-Item -Path "README.md" -Destination "$DistName\" -Force
if (Test-Path "CHANGELOG.md") {
    Copy-Item -Path "CHANGELOG.md" -Destination "$DistName\" -Force
}

# Dependencies
Get-ChildItem "requirements*.txt" | Copy-Item -Destination "$DistName\" -Force
Copy-Item -Path "pyproject.toml" -Destination "$DistName\" -Force

# Deployment files
Copy-Item -Path "deploy" -Destination "$DistName\" -Recurse -Force

# Scripts
Copy-Item -Path "setup_and_run.sh" -Destination "$DistName\" -Force
Copy-Item -Path "setup_and_run.ps1" -Destination "$DistName\" -Force

# Tests (optional)
if ($IncludeTests) {
    Copy-Item -Path "tests" -Destination "$DistName\" -Recurse -Force
}

# CI/CD config
if (Test-Path ".github") {
    Copy-Item -Path ".github" -Destination "$DistName\" -Recurse -Force
}

# Build wheel package
if (-not $SkipBuild) {
    Write-Host "Build Python wheel..." -ForegroundColor Yellow
    try {
        & python -m pip install --upgrade build
        & python -m build --wheel
        if (Test-Path "dist\*.whl") {
            Copy-Item -Path "dist\*.whl" -Destination "$DistName\" -Force
        }
    } catch {
        Write-Host "Wheel build failed, skipping: $_" -ForegroundColor Yellow
    }
}

# Create usage instructions
$QuickStartContent = @"
# Quick Start Guide

## Windows
```powershell
./setup_and_run.ps1 -ZipFile <path-to-zip>
```

## Linux/macOS
```bash
chmod +x setup_and_run.sh
./setup_and_run.sh -z <path-to-zip>
```

## Manual install
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m sensor_fuzz
```

## Validate install
```bash
python -c "import sensor_fuzz; print('OK')"
```

## Access
- Web UI: http://localhost:8000
- Monitoring: http://localhost:8080

## Troubleshooting
- Run as administrator if permission errors occur
- Use Python 3.10+ if version issues appear
- Change ports in config if already in use
"@

$QuickStartContent | Out-File -FilePath "$DistName\QUICK_START.md" -Encoding UTF8

# Create zip archive
Write-Host "Create zip archive..." -ForegroundColor Yellow
Compress-Archive -Path $DistName -DestinationPath "$DistName.zip" -Force

# Get file size
$FileSize = (Get-Item "$DistName.zip").Length / 1MB
$FileSizeFormatted = "{0:N2} MB" -f $FileSize

Write-Host "Distribution package created." -ForegroundColor Green
Write-Host "Archive: $DistName.zip" -ForegroundColor Cyan
Write-Host "Size: $FileSizeFormatted" -ForegroundColor Cyan

# Cleanup
Remove-Item -Path $DistName -Recurse -Force

Write-Host "" -ForegroundColor White
Write-Host "Notes:" -ForegroundColor Green
Write-Host "1. Share $DistName.zip with users" -ForegroundColor White
Write-Host "2. Users unzip and run the platform-specific setup script" -ForegroundColor White
Write-Host "3. Alternatively follow QUICK_START.md for manual install" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Distribute via email or file sharing as needed" -ForegroundColor Yellow
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\create_distribution.ps1