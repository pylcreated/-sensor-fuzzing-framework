#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional stacks (uncomment as needed)
# pip install -r requirements-optional-ai.txt
# pip install -r requirements-optional-capture.txt
# pip install -r requirements-optional-report.txt

echo "Base dependencies installed. Activate with: source .venv/bin/activate"
