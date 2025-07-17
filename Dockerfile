# ──────────────────────────────────────────────────────────
# Event Analytics Platform - Docker Image
# ──────────────────────────────────────────────────────────
# Multi-stage build for optimized analytics platform deployment
# Supports both API service and background worker modes

FROM python:3.12-alpine as base

# Install system dependencies for analytics platform
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    && rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 1001 -S analytics && \
    adduser -S analytics -u 1001 -G analytics

# Set working directory and ownership
WORKDIR /app
RUN chown analytics:analytics /app

# Switch to non-root user for package installation
USER analytics

# Install Python dependencies as non-root user
COPY --chown=analytics:analytics requirements.txt .
RUN pip install --user --no-cache-dir --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt

# Update PATH to include user-installed packages
ENV PATH="/home/analytics/.local/bin:${PATH}"

# Copy application code
COPY --chown=analytics:analytics . .

# Environment variables for analytics platform
ENV FLASK_ENV=development \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    REDIS_MAX_CONNECTIONS=20 \
    ANALYTICS_DEFAULT_RETENTION_DAYS=30

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Expose application port
EXPOSE 5000

# Default command (can be overridden for worker mode)
CMD ["python", "run.py"]