#!/usr/bin/env bash
# Create distribution package for Sensor Fuzzing Framework

set -e

echo "📦 创建项目分发包"
echo "==================="

# Create distribution directory
DIST_DIR="sensor-fuzzing-framework-$(date +%Y%m%d)"
echo "📁 创建目录: $DIST_DIR"

mkdir -p "$DIST_DIR"

# Copy essential files and directories
echo "📋 复制项目文件..."

# Core source code
cp -r src "$DIST_DIR/"
cp -r config "$DIST_DIR/"

# Documentation
cp -r docs "$DIST_DIR/"
cp README.md "$DIST_DIR/"
cp CHANGELOG.md "$DIST_DIR/" 2>/dev/null || echo "CHANGELOG.md not found, skipping"

# Dependencies
cp requirements*.txt "$DIST_DIR/"
cp pyproject.toml "$DIST_DIR/"

# Deployment files
cp -r deploy "$DIST_DIR/"

# Scripts
cp setup_and_run.sh "$DIST_DIR/"
cp setup_and_run.ps1 "$DIST_DIR/"

# Tests (optional, for development)
cp -r tests "$DIST_DIR/"

# CI/CD config
cp -r .github "$DIST_DIR/" 2>/dev/null || echo ".github not found, skipping"

# Create wheel package
echo "🔨 构建Python包..."
python -m pip install --upgrade build
python -m build --wheel
cp dist/*.whl "$DIST_DIR/" 2>/dev/null || echo "Wheel build failed, skipping"

# Create usage instructions
cat > "$DIST_DIR/QUICK_START.md" << 'EOF'
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
EOF

# Create zip archive
echo "📦 创建压缩包..."
zip -r "${DIST_DIR}.zip" "$DIST_DIR"

echo "✅ 分发包创建完成!"
echo "📁 包位置: ${DIST_DIR}.zip"
echo "📊 包大小: $(du -sh "${DIST_DIR}.zip" | cut -f1)"

# Cleanup
rm -rf "$DIST_DIR"

echo ""
echo "🎯 分发说明:"
echo "1. 将 ${DIST_DIR}.zip 发送给其他用户"
echo "2. 用户解压后运行相应平台的setup脚本"
echo "3. 或参考 QUICK_START.md 进行手动安装"</content>
<parameter name="filePath">C:\Users\31601\Desktop\学年论文2\create_distribution.sh