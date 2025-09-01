# Alternative Dockerfile using AWS CodeBuild managed image
# This avoids Docker Hub rate limits by using AWS managed base images

# Use AWS CodeBuild managed Python image
FROM public.ecr.aws/codebuild/amazonlinux2-x86_64-base:3.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install Python and system dependencies
RUN yum update -y && \
    yum install -y python3 python3-pip python3-devel gcc && \
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
