# Alternative Dockerfile using Python slim image with Docker Hub auth
# This uses the original approach but with Docker Hub authentication

# Use Python 3.11 slim image (requires Docker Hub authentication)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install system dependencies for building
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get update --allow-releaseinfo-change \
    && apt-get install -y --no-install-recommends --allow-unauthenticated \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get update --allow-releaseinfo-change \
    && apt-get install -y --no-install-recommends --allow-unauthenticated \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /opt/venv \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
