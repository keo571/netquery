# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:${PATH}" \
    PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser ./src /app/src
COPY --chown=appuser:appuser ./langgraph.json /app/
COPY --chown=appuser:appuser ./.env.example /app/.env.example

# Create directories for data and configuration
RUN mkdir -p /app/data /app/config /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Update PATH for user
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app'); from src.text_to_sql.tools.database_toolkit import db_toolkit; exit(0 if db_toolkit.test_connection() else 1)"

# Default command - MCP server
CMD ["python", "-m", "src.text_to_sql.mcp_server_standard"]