# Multi-stage build for optimized image
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt requirements-optional-*.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-optional-ai.txt || true

# Production stage
FROM base AS production

# Create non-root user
RUN groupadd -r sensorfuzz && useradd -r -g sensorfuzz sensorfuzz

# Copy application code
COPY --chown=sensorfuzz:sensorfuzz src/ ./src/
COPY --chown=sensorfuzz:sensorfuzz config/ ./config/

# Set proper permissions
RUN chmod -R 755 /app && \
    chown -R sensorfuzz:sensorfuzz /app

# Switch to non-root user
USER sensorfuzz

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, 'src'); from sensor_fuzz.monitoring.collector import get_system_stats; print('OK')" || exit 1

# Expose ports
EXPOSE 8000 8080

# Set the default command
CMD ["python", "-m", "sensor_fuzz"]

# Development stage
FROM base AS development

# Install development dependencies
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY tests/ ./tests/

# Set development command
CMD ["python", "-m", "pytest", "tests/", "-v"]
