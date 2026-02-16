#!/usr/bin/env bash
# Create distribution package for Sensor Fuzzing Framework

set -e

echo "Create distribution package"
echo "==========================="

DIST_DIR="sensor-fuzzing-framework-$(date +%Y%m%d)"
echo "Create directory: $DIST_DIR"

mkdir -p "$DIST_DIR"

echo "Copy project files..."
cp -r src "$DIST_DIR/"
cp -r config "$DIST_DIR/"
cp -r docs "$DIST_DIR/"
cp README.md "$DIST_DIR/"
cp CHANGELOG.md "$DIST_DIR/" 2>/dev/null || echo "CHANGELOG.md not found, skipping"
cp requirements*.txt "$DIST_DIR/"
cp pyproject.toml "$DIST_DIR/"
cp -r deploy "$DIST_DIR/"
cp setup_and_run.sh "$DIST_DIR/"
cp setup_and_run.ps1 "$DIST_DIR/"
cp -r tests "$DIST_DIR/"
cp -r .github "$DIST_DIR/" 2>/dev/null || echo ".github not found, skipping"

echo "Build Python package..."
python -m pip install --upgrade build
python -m build --wheel
cp dist/*.whl "$DIST_DIR/" 2>/dev/null || echo "Wheel build failed, skipping"

cat > "$DIST_DIR/QUICK_START.md" << 'EOF'
# Quick Start Guide

## Windows
```powershell
.\setup_and_run.ps1 -ZipFile <path-to-zip>
```

## Linux/macOS
```bash
chmod +x setup_and_run.sh
./setup_and_run.sh <path-to-zip>
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
python sil_compliance_test.py
```

## Access
- Web UI: http://localhost:8000
- Monitoring: http://localhost:8080
EOF

echo "Create zip archive..."
zip -r "${DIST_DIR}.zip" "$DIST_DIR"

echo "Distribution package created."
echo "Archive: ${DIST_DIR}.zip"
echo "Size: $(du -sh "${DIST_DIR}.zip" | cut -f1)"

rm -rf "$DIST_DIR"

echo ""
echo "Notes:"
echo "1. Share ${DIST_DIR}.zip with users"
echo "2. Users unzip and run the platform-specific setup script"
echo "3. Alternatively follow QUICK_START.md for manual install"
