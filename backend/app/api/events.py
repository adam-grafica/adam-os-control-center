"""ADAM OS Dashboard — Events API Endpoints

Provides access to the events log with filtering and timeline data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.db import StateDB, get_db
from app.models.schemas import EventLog, TimelinePoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=List[EventLog])
async def list_events(
    limit: int = Query(100, ge=1, le=500, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    db: StateDB = Depends(get_db),
) -> List[EventLog]:
    """List recent events with pagination.

    Events are ordered by timestamp descending (newest first).
    """
    rows = await db.get_events(limit=limit, offset=offset)
    return [EventLog(**r) for r in rows]


@router.get("/type/{event_type}", response_model=List[EventLog])
async def events_by_type(
    event_type: str,
    limit: int = Query(50, ge=1, le=500, description="Number of events to return"),
    db: StateDB = Depends(get_db),
) -> List[EventLog]:
    """List events filtered by event type.

    Supported event types: request, alert, state_change, memory_update,
    training, policy_check, action_request, anomaly.
    """
    rows = await db.get_events_by_type(event_type=event_type, limit=limit)
    return [EventLog(**r) for r in rows]


@router.get("/timeline", response_model=List[TimelinePoint])
async def event_timeline(
    hours: int = Query(
        24, ge=1, le=168, description="Hours of history to include"
    ),
    db: StateDB = Depends(get_db),
) -> List[TimelinePoint]:
    """Return timeline data for charts.

    This queries the state_snapshots table over the given time window
    and returns health, mode, tokens, and tasks at each point.
    """
    rows = await db.get_state_timeline(hours=hours, limit=288)
    return [
        TimelinePoint(
            ts=r.get("ts", ""),
            health=r.get("health", 0) or 0,
            mode=r.get("mode"),
            tokens=r.get("tokens_estimated"),
            tasks=r.get("active_tasks"),
        )
        for r in rows
    ]
