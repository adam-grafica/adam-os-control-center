# ADAM OS Dashboard v0.001 — Svelte 5 + FastAPI
# Multi-stage: Python 3.11 slim
FROM python:3.11-slim AS builder

ARG BUILD_TIME
RUN echo "Build: ${BUILD_TIME:-unknown}" > /tmp/build.info

WORKDIR /app

# Install backend dependencies
RUN pip install --no-cache-dir \
    fastapi uvicorn[standard] aiosqlite sse-starlette \
    pydantic "pydantic-settings>=2.2.0" python-dotenv python-multipart psutil httpx

# ---------- Runtime ----------
FROM python:3.11-slim

# Install curl for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy all application code
COPY . .

# Ensure PYTHONPATH includes /app/backend so 'from app.x import y' resolves
ENV PYTHONPATH=/app/backend

# Create non-root user for security (D-C6)
RUN adduser --disabled-password --gecos '' appuser

# Ensure state.db path exists
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Health check for container orchestration (D-C6)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Switch to non-root user (D-C6)
USER appuser

# Expose port 8080 (CapRover standard)
EXPOSE 8080

# Run FastAPI on 0.0.0.0:8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
