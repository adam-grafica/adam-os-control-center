# ADAM OS Dashboard

Real-time monitoring and orchestration dashboard for the ADAM OS ecosystem. Built with **FastAPI** (backend) and **Svelte 5** (frontend), communicating via **Server-Sent Events (SSE)** and RESTful JSON APIs.

---

## Requirements

| Component | Minimum Version |
|-----------|----------------|
| Python    | 3.9+           |
| Node.js   | 18+            |
| npm       | 9+             |
| SQLite    | 3.x (bundled)  |

## Quick Install

```bash
# 1. Clone the repository
git clone <repo-url> adam-os-system
cd adam-os-system/dashboard

# 2. Install all dependencies
make install

# 3. Start development servers
make dev
```

The frontend will be available at **http://localhost:5173** and the backend at **http://localhost:8000**.

## Development

### Single-command dev mode

```bash
./scripts/dev.sh
```

Or equivalently:

```bash
make dev
```

This starts both the backend (port 8000) and frontend (port 5173) with hot-reload enabled. Press `Ctrl+C` to stop both.

### Run backend only

```bash
./scripts/run_backend.sh
```

### Run frontend only

```bash
cd frontend && npm run dev
```

### Run tests

```bash
make test
```

## Deploy

```bash
./scripts/deploy.sh
```

This script:
1. Builds the frontend for production
2. Outputs a complete systemd service unit for `adam-os-dashboard.service`
3. Provides nginx configuration for serving the static build and proxying the API

For production, ensure your `.env` file (see [Configuration](#configuration)) is properly set with production paths.

### Manual systemd service setup

After running `./scripts/deploy.sh`, follow its printed instructions, or do:

```bash
sudo tee /etc/systemd/system/adam-os-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=ADAM OS Dashboard
After=network.target

[Service]
Type=simple
User=adamcloud
WorkingDirectory=/home/adamcloud/adam-os-system/dashboard
EnvironmentFile=/home/adamcloud/adam-os-system/dashboard/.env
ExecStart=/home/adamcloud/adam-os-system/dashboard/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now adam-os-dashboard
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Svelte 5)                     │
│  Port 5173 (dev) / Port 80 (prod via nginx)         │
│                                                      │
│  OrganGraph  HealthRing  Timeline  StatusBar  Metrics │
└───────────────────┬─────────────────────────────────┘
                    │ REST + SSE
┌───────────────────▼─────────────────────────────────┐
│              Backend (FastAPI)                       │
│  Port 8000                                           │
│                                                      │
│  app/main.py      (entry point)                      │
│  app/api/         (REST endpoints)                   │
│  app/sse/         (Server-Sent Events)               │
│  app/models.py    (SQLAlchemy models)                │
│  app/database.py  (SQLite connection)                │
│  app/services/    (business logic)                   │
└───────────────────┬─────────────────────────────────┘
                    │ SQLAlchemy + aiosqlite
┌───────────────────▼─────────────────────────────────┐
│              SQLite Database                         │
│  Path: ${ADAM_OS_DATA_DIR}/adam-os.db                │
└─────────────────────────────────────────────────────┘
```

### Data flow

1. **System agents** and **orchestration services** write state to the SQLite database
2. **FastAPI backend** reads this state and exposes it via REST endpoints and SSE streams
3. **Svelte 5 frontend** subscribes to SSE for real-time updates and polls REST for initial state
4. **Visual components** render the system state: OrganGraph (topology), HealthRing (status), Timeline (events), StatusBar (summary), MetricBadge (KPIs)

## API Endpoints

### System Status

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/health`         | Health check (returns `{"status":"ok"}`) |
| GET    | `/api/v1/status`         | Overall system status summary        |

### Organ Graph (System Topology)

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/organ-graph`    | Full system topology graph           |
| GET    | `/api/v1/organ-graph/{node_id}` | Single node details           |

### Health & Metrics

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/health-ring`    | Health ring data (all components)    |
| GET    | `/api/v1/metrics`        | Current system metrics               |
| GET    | `/api/v1/metrics/{metric_name}` | Single metric value           |

### Timeline (Events)

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/timeline`       | Recent events timeline               |
| GET    | `/api/v1/timeline?since={timestamp}` | Events since a timestamp     |

### Agent Management

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/agents`         | List all registered agents           |
| GET    | `/api/v1/agents/{agent_id}` | Single agent details             |

### Real-time (SSE)

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/events/stream`  | SSE event stream for live updates    |
| GET    | `/api/v1/events/stream?channels=health,metrics,agents` | Filtered SSE stream |

### Configuration

| Method | Path                     | Description                          |
|--------|--------------------------|--------------------------------------|
| GET    | `/api/v1/config`         | Dashboard configuration              |
| POST   | `/api/v1/config`         | Update configuration                 |

## Components

### OrganGraph
Interactive system topology graph showing all ADAM OS agents and their connections. Nodes represent agents/services; edges represent communication channels or dependencies. Supports zoom, pan, and click-to-inspect.

### HealthRing
Radial/circular health indicator displaying the overall system health and per-component status. Color-coded segments (green=healthy, yellow=degraded, red=critical). Animates on state changes.

### Timeline
Scrollable event timeline showing system events, agent actions, and state transitions. Supports filtering by event type and severity. Auto-scrolls for new events in real-time via SSE.

### StatusBar
Persistent top-level status bar showing system state: overall health, active alerts count, uptime, and current mode (standby/active/maintenance). Displays at the top of the dashboard.

### MetricBadge
Compact KPI indicator badges for key system metrics (CPU, memory, active agents, queue depth, error rate). Used throughout the dashboard for at-a-glance monitoring.

## Configuration

Configuration is managed through the `.env` file located at the project root.

| Variable               | Default                        | Description                        |
|------------------------|--------------------------------|------------------------------------|
| `ADAM_OS_DATA_DIR`     | `/home/adamcloud/adam-os-data` | Path to ADAM OS data directory     |
| `DATABASE_URL`         | `sqlite:///{ADAM_OS_DATA_DIR}/adam-os.db` | SQLite database path |
| `DASHBOARD_HOST`       | `0.0.0.0`                     | Bind address for the backend       |
| `DASHBOARD_PORT`       | `8000`                         | Port for the backend               |
| `LOG_LEVEL`            | `INFO`                         | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `SSE_RETRY_INTERVAL`   | `3000`                         | SSE reconnect interval (ms)        |
| `ALLOWED_ORIGINS`      | `*`                            | CORS allowed origins               |

## Troubleshooting

### Backend won't start

- **Check Python version:** `python3 --version` must be 3.9+
- **Virtual environment missing:** Run `python3 -m venv venv && source venv/bin/activate && pip install -e .`
- **Port already in use:** `lsof -i :8000` to find the process, `kill -9 <PID>` to stop it
- **Database path error:** Ensure the directory set in `ADAM_OS_DATA_DIR` exists and is writable

### Frontend won't build

- **Node version too old:** `node --version` → need 18+. Use `nvm` to switch versions.
- **Missing dependencies:** `cd frontend && rm -rf node_modules && npm install`
- **Build errors:** Check `npm run build` output for specific error messages

### SSE / Real-time updates not working

- Open browser dev tools → Network tab, look for `/api/v1/events/stream`
- Ensure the backend is running on port 8000
- Check for CORS errors in the browser console
- Verify `ALLOWED_ORIGINS` includes your frontend URL in `.env`

### Database issues

- **Migration required:** Run `cd backend && python -m alembic upgrade head` if using Alembic
- **Read-only error:** Check permissions on the SQLite file and its parent directory
- **Lock errors:** SQLite can handle concurrent reads but concurrent writes from multiple processes may cause lock errors. Ensure exclusive access.

### Logs

To view backend logs in production:

```bash
sudo journalctl -u adam-os-dashboard -f
```

To increase log verbosity, set `LOG_LEVEL=DEBUG` in `.env` and restart.
