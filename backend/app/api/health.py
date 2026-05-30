"""ADAM OS Dashboard — Health & Status API Endpoints

Provides health checks and full organism snapshot.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.db import StateDB, get_db
from app.models.schemas import DashboardSnapshot
from app.services.snapshots import create_snapshot_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
async def health_check() -> Dict[str, Any]:
    """Simple health check endpoint.

    Returns 200 OK with status information.
    """
    return {
        "status": "ok",
        "service": "ADAM OS Dashboard API",
        "version": "1.0.0",
    }


@router.get("/organism", response_model=DashboardSnapshot)
async def organism_health(
    db: StateDB = Depends(get_db),
) -> DashboardSnapshot:
    """Return the full organism health snapshot.

    Includes health score, mood, mode, organ statuses, recent events,
    and active threats.
    """
    snapshot_service = create_snapshot_service(db)
    return await snapshot_service.get_current_snapshot()


@router.get("/state")
async def latest_state(
    db: StateDB = Depends(get_db),
) -> Dict[str, Any] | None:
    """Return the raw latest state snapshot from the database.

    This is the unprocessed state_snapshots table row.
    """
    state = await db.get_latest_state_snapshot()
    if state is None:
        return {"detail": "No state data available yet"}
    return state
