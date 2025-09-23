# Dockerfile for Netquery Backend (FastAPI)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create data directory
RUN mkdir -p /app/data /app/outputs

# Generate sample data on build (optional - can be removed if you want to mount existing data)
RUN python scripts/create_sample_data.py || true

# Expose the port
EXPOSE 8000

# Start the FastAPI server
CMD ["python", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]