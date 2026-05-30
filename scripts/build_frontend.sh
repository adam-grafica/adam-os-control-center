#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

cd "$FRONTEND_DIR"

# Install dependencies if node_modules does not exist
if [ ! -d "node_modules" ]; then
    echo "[build_frontend] Installing npm dependencies..."
    npm install
fi

echo "[build_frontend] Building frontend..."
npm run build

echo "[build_frontend] ✓ Frontend build complete. Output in $FRONTEND_DIR/build/"
