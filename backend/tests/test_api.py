"""Tests for the ADAM OS Control Center API (D-C4).

Uses FastAPI TestClient with pytest for integration tests covering
all API routers: health, infra, agents, console, files, config, control.

Also includes existing Dashboard API tests (organism health, events, organs)
for full coverage of the combined app.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the backend package is importable
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

# Set env BEFORE importing app modules (conftest.py already sets these,
# so setdefault only fills in if conftest didn't)
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("FILES_WRITE_ENABLED", "true")

from app.main import app


@pytest.fixture(scope="session")
def client():
    """Create a TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════
# Health Endpoints
# ═══════════════════════════════════════════════════════════════════


class TestHealth:
    """Tests for /api/health endpoints."""

    def test_health_check(self, client):
        """GET /api/health returns 200 with status, service, version."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ADAM OS Dashboard API"
        assert data["version"] == "1.0.0"

    def test_organism_health(self, client):
        """GET /api/health/organism returns a DashboardSnapshot."""
        response = client.get("/api/health/organism")
        assert response.status_code == 200
        data = response.json()
        assert "organism_health" in data
        assert "organism_mood" in data
        assert "current_mode" in data
        assert "active_threats" in data
        assert "organs" in data
        assert "recent_events" in data
        assert "snapshot_ts" in data

        organs = data["organs"]
        expected_organs = ["heart", "autonomic", "immune", "proprioception", "reflexes", "dreams", "growth"]
        for organ_name in expected_organs:
            assert organ_name in organs, f"Missing organ: {organ_name}"
            assert "status" in organs[organ_name]
            assert "health_score" in organs[organ_name]

        assert 0 <= data["organism_health"] <= 100
        assert data["organism_mood"] in ("thriving", "stable", "stressed", "critical")
        assert data["current_mode"] in ("normal", "light", "safe", "critical")

    def test_latest_state(self, client):
        """GET /api/health/state returns the latest state snapshot."""
        response = client.get("/api/health/state")
        assert response.status_code == 200
        data = response.json()
        if data and "detail" not in data:
            assert "id" in data or "health" in data


# ═══════════════════════════════════════════════════════════════════
# Events Endpoints
# ═══════════════════════════════════════════════════════════════════


class TestEvents:
    """Tests for /api/events endpoints."""

    def test_events_list(self, client):
        """GET /api/events returns a list of events."""
        response = client.get("/api/events")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        if events:
            event = events[0]
            assert "id" in event
            assert "source" in event

    def test_events_list_with_params(self, client):
        """GET /api/events?limit=5&offset=0 returns ≤5 events."""
        response = client.get("/api/events?limit=5&offset=0")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert len(events) <= 5

    def test_events_by_type(self, client):
        """GET /api/events/type/{type} returns filtered events."""
        response = client.get("/api/events/type/state_change")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)

    def test_events_timeline(self, client):
        """GET /api/events/timeline?hours=24 returns timeline data."""
        response = client.get("/api/events/timeline?hours=24")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════
# Organs Endpoints
# ═══════════════════════════════════════════════════════════════════


class TestOrgans:
    """Tests for /api/organs endpoints."""

    def test_organs_list(self, client):
        """GET /api/organs returns exactly 7 organs."""
        response = client.get("/api/organs")
        assert response.status_code == 200
        organs = response.json()
        assert isinstance(organs, list)
        assert len(organs) == 7
        organ_names = [o["name"] for o in organs]
        for name in ["heart", "autonomic", "immune", "proprioception", "reflexes", "dreams", "growth"]:
            assert name in organ_names, f"Missing organ: {name}"

    def test_organ_detail(self, client):
        """GET /api/organs/heart returns heart organ detail."""
        response = client.get("/api/organs/heart")
        assert response.status_code == 200
        organ = response.json()
        assert organ["name"] == "heart"
        assert "status" in organ
        assert "health_score" in organ
        assert 0 <= organ["health_score"] <= 100

    def test_invalid_organ(self, client):
        """GET /api/organs/invalid returns 404."""
        response = client.get("/api/organs/invalid")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


# ═══════════════════════════════════════════════════════════════════
# Root & Debug
# ═══════════════════════════════════════════════════════════════════


class TestRoot:
    """Tests for root and debug endpoints."""

    def test_root(self, client):
        """GET / returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        assert "html" in response.headers.get("content-type", "")

    def test_debug_config_disabled(self, client):
        """GET /api/debug/config returns 403 when DEBUG is false."""
        response = client.get("/api/debug/config")
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════
# Infrastructure Endpoints (D-C4)
# ═══════════════════════════════════════════════════════════════════


class TestInfraEndpoints:
    """Tests for /api/infra/* endpoints — real-time server metrics."""

    def test_snapshot(self, client):
        """GET /api/infra/snapshot returns 200 with cpu, memory, disk, network, uptime, processes."""
        response = client.get("/api/infra/snapshot")
        assert response.status_code == 200
        data = response.json()
        for key in ("cpu", "memory", "disk", "network", "uptime", "processes", "ts"):
            assert key in data, f"Missing key: {key}"
        assert isinstance(data["cpu"], dict)
        assert isinstance(data["memory"], dict)
        assert isinstance(data["disk"], list)
        assert isinstance(data["network"], dict)
        assert isinstance(data["processes"], list)

    def test_cpu(self, client):
        """GET /api/infra/cpu returns 200 with cpu data."""
        response = client.get("/api/infra/cpu")
        assert response.status_code == 200
        data = response.json()
        assert "percent" in data
        assert "cores" in data
        assert "load_avg" in data
        assert "status" in data

    def test_memory(self, client):
        """GET /api/infra/memory returns 200 with memory data."""
        response = client.get("/api/infra/memory")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "available" in data
        assert "used" in data
        assert "percent" in data
        assert "status" in data

    def test_disk(self, client):
        """GET /api/infra/disk returns 200 with disk data."""
        response = client.get("/api/infra/disk")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_network(self, client):
        """GET /api/infra/network returns 200 with network data."""
        response = client.get("/api/infra/network")
        assert response.status_code == 200
        data = response.json()
        assert "bytes_sent" in data
        assert "bytes_recv" in data
        assert "packets_sent" in data
        assert "packets_recv" in data

    def test_processes(self, client):
        """GET /api/infra/processes returns 200 with top N processes."""
        response = client.get("/api/infra/processes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            proc = data[0]
            assert "pid" in proc
            assert "name" in proc
            assert "cpu_percent" in proc
            assert "memory_percent" in proc


# ═══════════════════════════════════════════════════════════════════
# Agents Endpoints (D-C4)
# ═══════════════════════════════════════════════════════════════════


class TestAgentsEndpoints:
    """Tests for /api/agents/* endpoints — Hermes agent status."""

    def test_agent_status(self, client):
        """GET /api/agents/status returns 200 with agents list."""
        response = client.get("/api/agents/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_agent_tasks(self, client):
        """GET /api/agents/tasks returns 200 with tasks list."""
        response = client.get("/api/agents/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_agent_tools(self, client):
        """GET /api/agents/tools returns 200 with tools list."""
        response = client.get("/api/agents/tools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════════
# Console Endpoints (D-C4)
# ═══════════════════════════════════════════════════════════════════


class TestConsoleEndpoints:
    """Tests for /api/console/* endpoints — log streaming."""

    def test_recent_logs(self, client):
        """GET /api/console/logs returns 200 with log entries."""
        response = client.get("/api/console/logs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_recent_logs_with_limit(self, client):
        """GET /api/console/logs?limit=5 respects limit parameter."""
        response = client.get("/api/console/logs?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_recent_logs_invalid_limit(self, client):
        """GET /api/console/logs with invalid limit returns 422."""
        response = client.get("/api/console/logs?limit=-1")
        assert response.status_code == 422

    @pytest.mark.skip(reason="SSE is long-lived stream; tested manually via curl")
    def test_stream_endpoint_returns_media_type(self, client):
        """GET /api/console/stream SSE content type — verified via route registration."""
        # SSE endpoints can't be tested via TestClient (long-lived stream)
        # Verify the route exists by checking the app's route table
        routes = [r.path for r in client.app.routes]
        assert "/api/console/stream" in routes
        assert "/api/stream/master" in routes


# ═══════════════════════════════════════════════════════════════════
# Files Endpoints (D-C4)
# ═══════════════════════════════════════════════════════════════════


class TestFilesEndpoints:
    """Tests for /api/files/* endpoints — file system operations."""

    def test_file_tree(self, client):
        """GET /api/files/tree returns 200 with file structure."""
        response = client.get("/api/files/tree")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "type" in data
        assert data["type"] == "directory"
        assert "children" in data

    def test_file_tree_with_path(self, client):
        """GET /api/files/tree?path=heart returns tree for specific path."""
        response = client.get("/api/files/tree?path=heart")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["type"] == "directory"

    def test_file_tree_nonexistent_path(self, client):
        """GET /api/files/tree?path=nonexistent returns error dict (not 500)."""
        response = client.get("/api/files/tree?path=nonexistent_xyz")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_read_file(self, client):
        """GET /api/files/read?file_path=xxx returns 200 with content for existing file."""
        # Use a known text file in the ADAM OS root
        response = client.get("/api/files/read?file_path=proprioception/state.md")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "lines" in data
        assert data["lines"] > 0
        assert "extension" in data
        assert data["extension"] == ".md"

    def test_read_file_not_found(self, client):
        """GET /api/files/read?file_path=nonexistent returns 404."""
        response = client.get("/api/files/read?file_path=nonexistent_xyz.txt")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_path_traversal_blocked(self, client):
        """GET /api/files/read?file_path=../../../etc/passwd returns 400 (path traversal blocked)."""
        response = client.get("/api/files/read?file_path=../../../etc/passwd")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_search_files(self, client):
        """GET /api/files/search?query=heart returns matching files."""
        response = client.get("/api/files/search?query=heart")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_write_file(self, client):
        """POST /api/files/write writes content to a file (FILES_WRITE_ENABLED=true)."""
        response = client.post(
            "/api/files/write",
            json={"file_path": "_test_write_api.txt", "content": "api test content"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Cleanup
        import os as _os
        from app.services.file_tree import file_tree
        test_path = file_tree._root / "_test_write_api.txt"
        if test_path.exists():
            test_path.unlink()


# ═══════════════════════════════════════════════════════════════════
# Config Endpoints (D-C4)
# ═══════════════════════════════════════════════════════════════════


class TestConfigEndpoints:
    """Tests for /api/config endpoints — application configuration."""

    def test_get_config(self, client):
        """GET /api/config returns 200 with settings dict."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "refresh_interval_ms" in data
        assert "thresholds" in data
        assert "ui" in data
        assert "security" in data
        assert "streaming" in data
        assert data["refresh_interval_ms"] == 2000
        assert data["thresholds"]["ram_warning"] == 80

    def test_update_config(self, client):
        """POST /api/config/update merges and returns updated config."""
        response = client.post(
            "/api/config/update",
            json={"thresholds": {"ram_warning": 80}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["thresholds"]["ram_warning"] == 80
        # Other keys preserved
        assert data["thresholds"]["ram_critical"] == 90


# ═══════════════════════════════════════════════════════════════════
# Control Endpoints (D-C4)
# ═══════════════════════════════════════════════════════════════════


class TestControlEndpoints:
    """Tests for /api/control/* endpoints — kanban task board."""

    def test_get_kanban(self, client):
        """GET /api/control/kanban returns 200 with all kanban columns."""
        response = client.get("/api/control/kanban")
        assert response.status_code == 200
        data = response.json()
        for col in ("backlog", "ready", "running", "blocked", "review", "done"):
            assert col in data, f"Missing column: {col}"
            assert isinstance(data[col], list)

    def test_create_task(self, client):
        """POST /api/control/task creates a new task."""
        response = client.post(
            "/api/control/task",
            json={"title": "Test task", "priority": "high", "description": "Integration test task"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test task"
        assert data["priority"] == "high"
        assert data["column"] == "backlog"
        assert "id" in data

        # Store the task ID for subsequent tests
        return data

    def test_create_task_missing_title(self, client):
        """POST /api/control/task without title returns 400."""
        response = client.post(
            "/api/control/task",
            json={"priority": "high"},
        )
        assert response.status_code == 400
        data = response.json()
        assert "title" in data["detail"].lower()

    def test_move_task(self, client):
        """POST /api/control/task/{id}/move moves a task between columns."""
        # Create a task first
        create_resp = client.post(
            "/api/control/task",
            json={"title": "Move test task", "column": "backlog"},
        )
        assert create_resp.status_code == 200
        task = create_resp.json()
        task_id = task["id"]

        # Move it
        move_resp = client.post(
            f"/api/control/task/{task_id}/move",
            json={"from_column": "backlog", "to_column": "ready"},
        )
        assert move_resp.status_code == 200
        moved = move_resp.json()
        assert moved["column"] == "ready"

    def test_move_task_invalid(self, client):
        """POST /api/control/task/{id}/move with invalid transition returns 404."""
        create_resp = client.post(
            "/api/control/task",
            json={"title": "Invalid move task"},
        )
        task_id = create_resp.json()["id"]

        move_resp = client.post(
            f"/api/control/task/{task_id}/move",
            json={"from_column": "backlog", "to_column": "running"},
        )
        assert move_resp.status_code == 404

    def test_move_task_missing_params(self, client):
        """POST /api/control/task/{id}/move without from/to returns 400."""
        create_resp = client.post(
            "/api/control/task",
            json={"title": "Missing params"},
        )
        task_id = create_resp.json()["id"]

        move_resp = client.post(
            f"/api/control/task/{task_id}/move",
            json={},
        )
        assert move_resp.status_code == 400

    def test_assign_task(self, client):
        """POST /api/control/task/{id}/assign assigns a task to an agent."""
        create_resp = client.post(
            "/api/control/task",
            json={"title": "Assign test"},
        )
        task_id = create_resp.json()["id"]

        assign_resp = client.post(
            f"/api/control/task/{task_id}/assign",
            json={"agent_id": "midisoft"},
        )
        assert assign_resp.status_code == 200
        data = assign_resp.json()
        assert data["assigned_to"] == "midisoft"

    def test_assign_task_missing_agent(self, client):
        """POST /api/control/task/{id}/assign without agent_id returns 400."""
        create_resp = client.post(
            "/api/control/task",
            json={"title": "Assign no agent"},
        )
        task_id = create_resp.json()["id"]

        assign_resp = client.post(
            f"/api/control/task/{task_id}/assign",
            json={},
        )
        assert assign_resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# Providers Endpoints (bonus: /api/providers)
# ═══════════════════════════════════════════════════════════════════


class TestProvidersEndpoints:
    """Tests for /api/providers endpoints — API provider registry."""

    def test_list_providers(self, client):
        """GET /api/providers returns 200 with provider list."""
        response = client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        ids = [p["id"] for p in data]
        assert "openai" in ids
        assert "anthropic" in ids

    def test_get_provider(self, client):
        """GET /api/providers/{id} returns 200 with provider detail."""
        response = client.get("/api/providers/openai")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "openai"
        assert data["name"] == "OpenAI"

    def test_get_provider_not_found(self, client):
        """GET /api/providers/{id} returns 404 for unknown provider."""
        response = client.get("/api/providers/nonexistent")
        assert response.status_code == 404

    def test_update_provider_status(self, client):
        """POST /api/providers/{id}/status updates provider status."""
        response = client.post(
            "/api/providers/openai/status",
            json={"status": "online"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"

    def test_update_provider_status_missing(self, client):
        """POST /api/providers/{id}/status without status field returns 400."""
        response = client.post(
            "/api/providers/openai/status",
            json={},
        )
        assert response.status_code == 400

    def test_update_provider_status_not_found(self, client):
        """POST /api/providers/{id}/status for unknown provider returns 404."""
        response = client.post(
            "/api/providers/nonexistent/status",
            json={"status": "online"},
        )
        assert response.status_code == 404
