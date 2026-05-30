"""ADAM OS Control Center — Agent Tracker Service

Tracks Hermes agents, their active tasks, and available tools.
Reads from the Hermes Agent registry on disk. If files don't exist,
returns empty structures (no mock data, no errors).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Default paths to check ──

DEFAULT_HERMES_ROOT = os.path.expanduser("~/.hermes")
DEFAULT_AXON_PROFILE = "axon"


class AgentTracker:
    """Read Hermes agent registry data from disk.

    Explores the Hermes Agent filesystem for status information,
    channel directories, and active sessions. Returns empty structures
    when files are missing — never mocks data.
    """

    def __init__(self, hermes_root: str | None = None, profile: str | None = None):
        self._hermes_root = Path(hermes_root or DEFAULT_HERMES_ROOT)
        self._profile_dir = self._hermes_root / "profiles" / (profile or DEFAULT_AXON_PROFILE)

    # ── Agent Status ──

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Return a list of known agents from the Hermes registry.

        Checks channel_directory.json and active session files.
        """
        agents: List[Dict[str, Any]] = []

        # Read channel directory for agent listing
        channel_file = self._hermes_root / "channel_directory.json"
        if channel_file.is_file():
            try:
                data = json.loads(channel_file.read_text())
                if isinstance(data, list):
                    for entry in data:
                        agents.append(
                            {
                                "id": entry.get("id", entry.get("name", "unknown")),
                                "name": entry.get("name", "unknown"),
                                "type": entry.get("type", "channel"),
                                "status": entry.get("status", "unknown"),
                                "last_seen": entry.get("last_seen"),
                            }
                        )
                elif isinstance(data, dict):
                    for key, val in data.items():
                        agents.append(
                            {
                                "id": key,
                                "name": val.get("name", key),
                                "type": val.get("type", "channel"),
                                "status": val.get("status", "unknown"),
                                "last_seen": val.get("last_seen"),
                            }
                        )
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not read channel_directory.json: %s", exc)
        else:
            logger.debug("No channel_directory.json found at %s", channel_file)

        return agents

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Return status for a specific agent by ID."""
        agents = self.get_all_agents()
        for agent in agents:
            if agent["id"] == agent_id:
                return agent
        return {"id": agent_id, "status": "unknown", "detail": "Agent not found in registry"}

    # ── Active Tasks ──

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Return active tasks from session files and task tracking."""
        tasks: List[Dict[str, Any]] = []

        # Read session files for active tasks
        sessions_dir = self._profile_dir / "sessions"
        if sessions_dir.is_dir():
            try:
                for session_file in sorted(sessions_dir.iterdir(), reverse=True)[:20]:
                    if session_file.suffix in (".json", ".jsonl"):
                        try:
                            raw = session_file.read_text()
                            if session_file.suffix == ".jsonl":
                                lines = raw.strip().split("\n")
                                if lines:
                                    first = json.loads(lines[0])
                                    tasks.append(
                                        {
                                            "session_id": session_file.stem,
                                            "type": "session",
                                            "source": first.get("agent_id", "unknown"),
                                            "status": "active",
                                            "file": session_file.name,
                                        }
                                    )
                            else:
                                data = json.loads(raw)
                                tasks.append(
                                    {
                                        "session_id": session_file.stem,
                                        "type": "session",
                                        "source": data.get("agent_id", data.get("name", "unknown")),
                                        "status": data.get("status", "active"),
                                        "file": session_file.name,
                                    }
                                )
                        except (json.JSONDecodeError, OSError):
                            continue
            except OSError as exc:
                logger.debug("Could not read sessions directory: %s", exc)

        return tasks

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return available tools from Hermes agent config.

        Reads the agent's auth.json and state.db for tool definitions.
        """
        tools: List[Dict[str, Any]] = []

        # Try reading auth.json for available integrations
        auth_file = self._profile_dir / "auth.json"
        if auth_file.is_file():
            try:
                data = json.loads(auth_file.read_text())
                if isinstance(data, dict):
                    for key in data:
                        tools.append(
                            {
                                "name": key,
                                "enabled": data[key].get("enabled", True),
                                "source": "auth",
                            }
                        )
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not read auth.json: %s", exc)

        # Try cron jobs as another tool source
        cron_file = self._profile_dir / "cron" / "jobs.json"
        if cron_file.is_file():
            try:
                data = json.loads(cron_file.read_text())
                if isinstance(data, list):
                    for job in data:
                        tools.append(
                            {
                                "name": f"cron:{job.get('name', job.get('id', 'unknown'))}",
                                "enabled": job.get("enabled", True),
                                "source": "cron",
                                "schedule": job.get("schedule", ""),
                            }
                        )
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not read cron jobs: %s", exc)

        return tools


# ── Module-level singleton ──

agent_tracker = AgentTracker()
