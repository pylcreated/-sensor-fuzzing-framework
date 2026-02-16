# Multi-stage build for optimized image
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE} AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Keep base image lean to avoid OOM during package manager operations

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=pypi.org

# Install Python dependencies
COPY consolidated_requirements.txt ./
RUN pip install --no-cache-dir --retries 8 --timeout 120 \
    -i ${PIP_INDEX_URL} --trusted-host ${PIP_TRUSTED_HOST} \
    -r consolidated_requirements.txt

# Production stage
FROM base AS production

# Create non-root user
RUN groupadd -r sensorfuzz && useradd -r -g sensorfuzz sensorfuzz

# Copy application code
COPY --chown=sensorfuzz:sensorfuzz src/ ./src/
COPY --chown=sensorfuzz:sensorfuzz config/ ./config/

# Set proper permissions
RUN mkdir -p /tmp/prometheus && \
    chmod -R 755 /app /tmp/prometheus && \
    chown -R sensorfuzz:sensorfuzz /app /tmp/prometheus

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

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY tests/ ./tests/

# Set development command
CMD ["python", "-m", "pytest", "tests/", "-v"]
