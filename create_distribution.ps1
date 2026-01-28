# Create distribution package for Sensor Fuzzing Framework (Windows)
# Usage: .\create_distribution.ps1

param(
    [string]$OutputDir = "dist",
    [switch]$IncludeTests,
    [switch]$SkipBuild
)

Write-Host "📦 创建项目分发包" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green

# Create timestamp for version
$Timestamp = Get-Date -Format "yyyyMMdd"
$DistName = "sensor-fuzzing-framework-$Timestamp"

Write-Host "📁 创建目录: $DistName" -ForegroundColor Yellow

# Create distribution directory
New-Item -ItemType Directory -Path $DistName -Force | Out-Null

# Copy essential files and directories
Write-Host "📋 复制项目文件..." -ForegroundColor Yellow

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
    Write-Host "🔨 构建Python包..." -ForegroundColor Yellow
    try {
        & python -m pip install --upgrade build
        & python -m build --wheel
        if (Test-Path "dist\*.whl") {
            Copy-Item -Path "dist\*.whl" -Destination "$DistName\" -Force
        }
    } catch {
        Write-Host "⚠️  Wheel构建失败，跳过: $_" -ForegroundColor Yellow
    }
}

# Create usage instructions
$QuickStartContent = @"
# 快速开始指南

## Windows用户
```powershell
# 运行PowerShell脚本
.\setup_and_run.ps1
```

## Linux/macOS用户
```bash
# 运行Bash脚本
chmod +x setup_and_run.sh
./setup_and_run.sh
```

## 手动安装
```bash
# 1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或: .venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行框架
python -m sensor_fuzz
```

## 验证安装
```bash
# 测试导入
python -c "import sensor_fuzz; print('OK')"

# 运行SIL合规测试
python sil_compliance_test.py
```

## 访问界面
- Web界面: http://localhost:8000
- 监控面板: http://localhost:8080

## 故障排除
- 如果遇到权限错误，请以管理员身份运行
- 如果Python版本不兼容，请使用Python 3.10+
- 如果端口被占用，请修改配置文件中的端口设置
"@

$QuickStartContent | Out-File -FilePath "$DistName\QUICK_START.md" -Encoding UTF8

# Create zip archive
Write-Host "📦 创建压缩包..." -ForegroundColor Yellow
Compress-Archive -Path $DistName -DestinationPath "$DistName.zip" -Force

# Get file size
$FileSize = (Get-Item "$DistName.zip").Length / 1MB
$FileSizeFormatted = "{0:N2} MB" -f $FileSize

Write-Host "✅ 分发包创建完成!" -ForegroundColor Green
Write-Host "📁 包位置: $DistName.zip" -ForegroundColor Cyan
Write-Host "📊 包大小: $FileSizeFormatted" -ForegroundColor Cyan

# Cleanup
Remove-Item -Path $DistName -Recurse -Force

Write-Host "" -ForegroundColor White
Write-Host "🎯 分发说明:" -ForegroundColor Green
Write-Host "1. 将 $DistName.zip 发送给其他用户" -ForegroundColor White
Write-Host "2. 用户解压后运行相应平台的setup脚本" -ForegroundColor White
Write-Host "3. 或参考 QUICK_START.md 进行手动安装" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "📧 联系方式: 请将此包通过邮件或文件共享方式分发" -ForegroundColor Yellow</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\create_distribution.ps1