# ADAM OS Dashboard - Dockerfile
# Multi-stage: Python 3.11 slim
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Runtime ----------
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create static directory
RUN mkdir -p /app/static

# Expose port 8080 (CapRover standard)
EXPOSE 8080

# Run with uvicorn on 0.0.0.0:8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
