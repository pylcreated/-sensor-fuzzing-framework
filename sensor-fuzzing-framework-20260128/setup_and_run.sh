#!/usr/bin/env bash
# Sensor Fuzzing Framework - Quick Setup Script (Linux/macOS)
# Usage: ./setup_and_run.sh [zip_file_path]

set -e

echo "🚀 Sensor Fuzzing Framework - Quick Setup"
echo "=========================================="

# Check if zip file is provided
if [ $# -eq 0 ]; then
    echo "❌ 请提供项目zip文件路径"
    echo "用法: $0 <sensor-fuzzing-framework.zip>"
    exit 1
fi

ZIP_FILE="$1"

# Check if file exists
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ 文件不存在: $ZIP_FILE"
    exit 1
fi

echo "📦 解压项目文件..."
unzip -q "$ZIP_FILE"
PROJECT_DIR=$(basename "$ZIP_FILE" .zip)
cd "$PROJECT_DIR"

echo "🐍 创建虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

echo "📦 安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ 验证安装..."
python -c "import sensor_fuzz; print('✅ 模块导入成功')"

echo "🚀 启动框架..."
python -m sensor_fuzz</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\setup_and_run.sh