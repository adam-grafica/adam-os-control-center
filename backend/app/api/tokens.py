"""ADAM OS Dashboard — Token Tracker API Endpoints

REST API for querying token consumption metrics from Hermes Agent's
session database. All data is read-only — no writes to the Hermes DB.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from app.services.token_tracker import (
    get_all_time_totals,
    get_daily_summary,
    get_live_session,
    get_provider_summary,
    get_recent_sessions,
    get_session_tokens,
    get_weekly_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tokens", tags=["Token Tracker"])


# ── Summary ──


@router.get("/summary")
async def token_summary() -> Dict[str, Any]:
    """All-time token totals plus current/live session info.

    Returns:
        - all_time: cumulative totals across all sessions
        - live_session: currently active or most recent session
    """
    all_time = get_all_time_totals()
    live = get_live_session()
    return {
        "all_time": all_time,
        "live_session": live,
    }


# ── Daily Breakdown ──


@router.get("/daily")
async def daily_breakdown(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> List[Dict[str, Any]]:
    """Token consumption aggregated by calendar day.

    Returns array of objects with date, token counts, session count, cost.
    """
    return get_daily_summary(days=days)


# ── Weekly Breakdown ──


@router.get("/weekly")
async def weekly_breakdown(
    weeks: int = Query(12, ge=1, le=104, description="Number of weeks to include"),
) -> List[Dict[str, Any]]:
    """Token consumption aggregated by ISO week.

    Returns array of objects with week_start, token counts, session count, cost.
    """
    return get_weekly_summary(weeks=weeks)


# ── Recent Sessions ──


@router.get("/sessions")
async def recent_sessions(
    limit: int = Query(
        20, ge=1, le=500, description="Number of recent sessions to return"
    ),
) -> List[Dict[str, Any]]:
    """Return the most recent sessions with token data."""
    return get_recent_sessions(limit=limit)


# ── Provider Breakdown ──


@router.get("/providers")
async def provider_breakdown() -> List[Dict[str, Any]]:
    """Token consumption aggregated by billing provider and model."""
    return get_provider_summary()


# ── Live Session ──


@router.get("/live")
async def live_session() -> Dict[str, Any]:
    """Return the currently active session (or most recent)."""
    session = get_live_session()
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No sessions found in the Hermes database.",
        )
    return session


# ── Single Session ──


@router.get("/session/{session_id}")
async def session_detail(session_id: str) -> Dict[str, Any]:
    """Return detailed token data for a specific session."""
    session = get_session_tokens(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}",
        )
    return session
