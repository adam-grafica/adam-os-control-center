#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Create virtual environment if missing
if [ ! -d "venv" ]; then
    echo "[run_backend] Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies from pyproject.toml
echo "[run_backend] Installing Python dependencies..."
pip install -e . 2>/dev/null || pip install . 2>/dev/null || {
    echo "[run_backend] No pyproject.toml setup yet; installing core deps directly..."
    pip install fastapi uvicorn sqlalchemy aiosqlite python-dotenv pydantic
}

echo "[run_backend] Starting backend on http://0.0.0.0:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
