import warnings

# Silence noisy warnings (notably sqlite ResourceWarning) across the test suite
warnings.filterwarnings("ignore")
