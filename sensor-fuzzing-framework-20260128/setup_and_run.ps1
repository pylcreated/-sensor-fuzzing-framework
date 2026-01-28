# Sensor Fuzzing Framework - Quick Setup Script (Windows)
# Usage: .\setup_and_run.ps1 [-ZipFile "path\to\sensor-fuzzing-framework.zip"]

param(
    [Parameter(Mandatory=$true)]
    [string]$ZipFile,

    [switch]$SkipValidation
)

Write-Host "🚀 Sensor Fuzzing Framework - Quick Setup" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Check if zip file exists
if (-not (Test-Path $ZipFile)) {
    Write-Host "❌ 文件不存在: $ZipFile" -ForegroundColor Red
    exit 1
}

Write-Host "📦 解压项目文件..." -ForegroundColor Yellow
$ProjectDir = [System.IO.Path]::GetFileNameWithoutExtension($ZipFile)
Expand-Archive -Path $ZipFile -DestinationPath $ProjectDir -Force
Set-Location $ProjectDir

Write-Host "🐍 创建虚拟环境..." -ForegroundColor Yellow
python -m venv .venv
.venv\Scripts\activate

Write-Host "📦 安装依赖..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not $SkipValidation) {
    Write-Host "✅ 验证安装..." -ForegroundColor Yellow
    try {
        python -c "import sensor_fuzz; print('✅ 模块导入成功')"
        Write-Host "✅ 验证通过!" -ForegroundColor Green
    } catch {
        Write-Host "❌ 验证失败: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🚀 启动框架..." -ForegroundColor Green
Write-Host "提示: 按 Ctrl+C 停止框架" -ForegroundColor Cyan
python -m sensor_fuzz</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\setup_and_run.ps1