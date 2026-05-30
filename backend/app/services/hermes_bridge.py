"""ADAM OS Control Center — Hermes Bridge Service

Reads the Hermes Agent registry filesystem to provide status and control
of Hermes agents. If files don't exist, returns empty structures — no errors.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_HERMES_ROOT = os.path.expanduser("~/.hermes")


class HermesBridge:
    """Bridge to the Hermes Agent ecosystem.

    Reads Hermes Agent registry files to determine agent status,
    active subagents, and running tasks. Does NOT make direct API calls
    to agents — it's a read-only filesystem probe.
    """

    def __init__(self, hermes_root: str = DEFAULT_HERMES_ROOT):
        self._hermes_root = Path(hermes_root)
        self._axon_profile = self._hermes_root / "profiles" / "axon"
        logger.debug("HermesBridge root: %s", self._hermes_root)

    # ── Public API ──

    def get_axon_status(self) -> Dict[str, Any]:
        """Return overall Hermes Axon profile status.

        Reads channel directory, auth config, and recent session data
        to build a composite status object.
        """
        status: Dict[str, Any] = {
            "profile": "axon",
            "hermes_root": str(self._hermes_root),
            "online": False,
            "sessions_active": 0,
            "agents": [],
            "cron_jobs": 0,
            "last_activity": None,
            "version": "unknown",
        }

        # Check if profile directory exists at all
        if not self._axon_profile.is_dir():
            return status

        status["online"] = True

        # Read channel directory for agent listing
        channel_file = self._hermes_root / "channel_directory.json"
        if channel_file.is_file():
            try:
                data = json.loads(channel_file.read_text())
                agents = []
                if isinstance(data, list):
                    for entry in data:
                        agents.append(entry.get("name", entry.get("id", "unknown")))
                elif isinstance(data, dict):
                    for key, val in data.items():
                        agents.append(val.get("name", key))
                status["agents"] = agents
            except (json.JSONDecodeError, OSError):
                pass

        # Count active sessions
        sessions_file = self._axon_profile / "sessions" / "sessions.json"
        if sessions_file.is_file():
            try:
                data = json.loads(sessions_file.read_text())
                if isinstance(data, dict):
                    status["sessions_active"] = len(data.get("active", []))
            except (json.JSONDecodeError, OSError):
                pass

        # Count cron jobs
        cron_file = self._axon_profile / "cron" / "jobs.json"
        if cron_file.is_file():
            try:
                data = json.loads(cron_file.read_text())
                if isinstance(data, list):
                    status["cron_jobs"] = len(data)
            except (json.JSONDecodeError, OSError):
                pass

        return status

    def get_subagents(self) -> List[Dict[str, Any]]:
        """Return sub-agents from the channel directory.

        Sub-agents are channels registered in channel_directory.json.
        """
        subagents: List[Dict[str, Any]] = []
        channel_file = self._hermes_root / "channel_directory.json"
        if not channel_file.is_file():
            return subagents

        try:
            data = json.loads(channel_file.read_text())
            if isinstance(data, list):
                for entry in data:
                    subagents.append(
                        {
                            "id": entry.get("id", entry.get("name", "unknown")),
                            "name": entry.get("name", "unknown"),
                            "type": entry.get("type", "channel"),
                            "status": entry.get("status", "unknown"),
                        }
                    )
            elif isinstance(data, dict):
                for key, val in data.items():
                    subagents.append(
                        {
                            "id": key,
                            "name": val.get("name", key),
                            "type": val.get("type", "channel"),
                            "status": val.get("status", "unknown"),
                        }
                    )
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Could not read channel_directory: %s", exc)

        return subagents

    def get_active_task_ids(self) -> List[str]:
        """Return task IDs currently being worked on.

        Reads session files from the axon profile sessions directory.
        """
        task_ids: List[str] = []
        sessions_dir = self._axon_profile / "sessions"
        if not sessions_dir.is_dir():
            return task_ids

        try:
            for entry in sorted(sessions_dir.iterdir(), reverse=True)[:30]:
                if entry.suffix in (".json", ".jsonl"):
                    task_ids.append(entry.stem)
        except OSError:
            pass

        return task_ids

    def send_command_to_agent(
        self, agent_id: str, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a command to a Hermes agent.

        NOTE: This is a stub — actual inter-agent communication is not
        yet implemented. This method logs the command and returns a
        "not implemented" response.
        """
        logger.info(
            "Command to agent %s: %s %s (stub — not implemented)",
            agent_id,
            command,
            params or {},
        )
        return {
            "success": False,
            "detail": (
                "Hermes inter-agent command dispatch is not yet implemented. "
                "This will be wired through Hermes gateway REST API in a future release."
            ),
            "agent_id": agent_id,
            "command": command,
        }


# ── Module-level singleton ──

hermes_bridge = HermesBridge()
