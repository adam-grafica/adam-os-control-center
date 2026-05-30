#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

# Trap SIGINT (Ctrl+C) to kill both backend and frontend
cleanup() {
    echo ""
    echo "[dev.sh] Shutting down ADAM OS Dashboard..."
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend in background
echo "[dev.sh] Starting backend..."
cd "$REPO_ROOT"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -e . 2>/dev/null || pip install . 2>/dev/null || pip install fastapi uvicorn sqlalchemy aiosqlite python-dotenv pydantic 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend in foreground (so Ctrl+C reaches us)
echo "[dev.sh] Starting frontend..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        ADAM OS Dashboard — Dev Mode         ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Frontend → http://localhost:5173            ║"
echo "║  Backend  → http://localhost:8000            ║"
echo "║  API Docs → http://localhost:8000/docs       ║"
echo "╚══════════════════════════════════════════════╝"
echo "Press Ctrl+C to stop both servers."
echo ""

# Wait for both to finish (they run in background)
wait
