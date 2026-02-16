"""模块说明：tests/conftest.py 的主要实现与辅助逻辑。"""

import warnings

# Silence noisy warnings (notably sqlite ResourceWarning) across the test suite
warnings.filterwarnings("ignore")
