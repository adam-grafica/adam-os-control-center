"""ADAM OS Control Center — Agents API Endpoints

Provides access to Hermes agent status, active tasks, and tools
via the AgentTracker service.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.agent_tracker import agent_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("/status")
async def agent_status() -> List[Dict[str, Any]]:
    """Return all known agents from the Hermes registry.

    Reads channel_directory.json and session data for agent listing.
    Returns empty list if no registry data exists.
    """
    return agent_tracker.get_all_agents()


@router.get("/tasks")
async def active_tasks() -> List[Dict[str, Any]]:
    """Return active tasks from Hermes session files.

    Scans the sessions directory for active session files.
    """
    return agent_tracker.get_active_tasks()


@router.get("/tools")
async def available_tools() -> List[Dict[str, Any]]:
    """Return tools available through Hermes agents.

    Reads from auth.json and cron job definitions.
    """
    return agent_tracker.get_tools()
