# Alternative Dockerfile using AWS Linux 2 with Python
# This completely avoids Docker Hub by using AWS Linux base image

# Use AWS Linux 2 as base (no Docker Hub authentication needed)
FROM public.ecr.aws/amazonlinux/amazonlinux:2

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install Python 3.11 and development tools
RUN yum update -y && \
    yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget tar gzip && \
    cd /opt && \
    wget https://www.python.org/ftp/python/3.11.5/Python-3.11.5.tgz && \
    tar xzf Python-3.11.5.tgz && \
    cd Python-3.11.5 && \
    ./configure --enable-optimizations && \
    make altinstall && \
    ln -s /usr/local/bin/python3.11 /usr/bin/python3 && \
    ln -s /usr/local/bin/pip3.11 /usr/bin/pip3 && \
    cd /opt && \
    rm -rf Python-3.11.5* && \
    yum clean all

# Create virtual environment
RUN python3 -m venv /opt/venv

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create app directory
WORKDIR /app

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
