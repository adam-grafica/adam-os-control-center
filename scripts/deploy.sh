#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "[deploy.sh] Building frontend for production..."
bash "$SCRIPT_DIR/build_frontend.sh"

# Create systemd service unit
SERVICE_NAME="adam-os-dashboard"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

cat << SERVICEEOF
[deploy.sh] To install as a systemd service, run:

  sudo tee ${SERVICE_FILE} > /dev/null << 'EOF'
[Unit]
Description=ADAM OS Dashboard
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${REPO_ROOT}
EnvironmentFile=${REPO_ROOT}/.env
ExecStart=${REPO_ROOT}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable ${SERVICE_NAME}
  sudo systemctl start ${SERVICE_NAME}

Then check status with:
  sudo systemctl status ${SERVICE_NAME}

To serve the static frontend build, configure nginx or Caddy to point to:
  ${REPO_ROOT}/frontend/build/

Example nginx config snippet:
  server {
      listen 80;
      server_name adam-os.local;

      root ${REPO_ROOT}/frontend/build;
      index index.html;

      location /api {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host \$host;
          proxy_set_header X-Real-IP \$remote_addr;
      }
  }
SERVICEEOF

echo "[deploy.sh] ✓ Deployment instructions generated."
