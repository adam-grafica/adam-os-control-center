-- ADAM OS Control Center — Extended Schema
-- Additional tables for agent tracking, tasks, API calls, logs, and config.
-- Executed by StateDB.connect() after the main schema.

-- ── Agent Heartbeats ──
CREATE TABLE IF NOT EXISTS agent_heartbeats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT NOT NULL,
    agent_name  TEXT,
    status      TEXT NOT NULL DEFAULT 'unknown',
    mode        TEXT DEFAULT 'idle',
    last_seen   TEXT NOT NULL DEFAULT (datetime('now')),
    version     TEXT,
    metadata    TEXT,  -- JSON blob
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_agent_heartbeats_agent_id ON agent_heartbeats(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_heartbeats_last_seen ON agent_heartbeats(last_seen);
CREATE INDEX IF NOT EXISTS idx_agent_heartbeats_status ON agent_heartbeats(status);

-- ── Tasks (Kanban) ──
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,  -- UUID
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority    TEXT NOT NULL DEFAULT 'medium',
    column_name TEXT NOT NULL DEFAULT 'backlog',
    status      TEXT NOT NULL DEFAULT 'open',
    assigned_to TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    metadata    TEXT  -- JSON blob for extra fields
);
CREATE INDEX IF NOT EXISTS idx_tasks_column ON tasks(column_name);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- ── API Calls (provider usage log) ──
CREATE TABLE IF NOT EXISTS api_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now')),
    provider_id TEXT NOT NULL,
    model       TEXT DEFAULT '',
    tokens      INTEGER DEFAULT 0,
    latency_ms  REAL DEFAULT 0.0,
    cost        REAL DEFAULT 0.0,
    success     INTEGER DEFAULT 1,
    endpoint    TEXT DEFAULT '',
    metadata    TEXT  -- JSON blob
);
CREATE INDEX IF NOT EXISTS idx_api_calls_provider ON api_calls(provider_id);
CREATE INDEX IF NOT EXISTS idx_api_calls_ts ON api_calls(ts);
CREATE INDEX IF NOT EXISTS idx_api_calls_success ON api_calls(success);

-- ── Logs (console log buffer persisted) ──
CREATE TABLE IF NOT EXISTS logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now')),
    level       TEXT NOT NULL DEFAULT 'info',
    source      TEXT NOT NULL DEFAULT 'system',
    type        TEXT NOT NULL DEFAULT 'log',
    message     TEXT DEFAULT '',
    metadata    TEXT  -- JSON blob for extra fields
);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(type);

-- ── Config (persisted config key-value store) ──
CREATE TABLE IF NOT EXISTS config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,  -- JSON-encoded value
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT DEFAULT ''
);
