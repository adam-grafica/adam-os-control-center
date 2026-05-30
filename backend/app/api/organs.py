"""ADAM OS Dashboard — Organs API Endpoints

Provides organ listing, detail views, and history for each of the 7 organs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.db import StateDB, get_db
from app.models.schemas import (
    EventLog,
    ORGAN_DESCRIPTIONS,
    ORGAN_NAMES,
    OrganSnapshot,
    TimelinePoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organs", tags=["Organs"])


@router.get("")
async def list_organs() -> List[Dict[str, Any]]:
    """List all 7 organs with basic metadata."""
    return [
        {
            "name": name,
            "description": ORGAN_DESCRIPTIONS.get(name, ""),
            "icon": _organ_icon(name),
        }
        for name in ORGAN_NAMES
    ]


@router.get("/{organ}", response_model=OrganSnapshot)
async def organ_detail(
    organ: str,
    db: StateDB = Depends(get_db),
) -> OrganSnapshot:
    """Return detailed information for a specific organ.

    Includes status, health score, organ-specific metrics,
    and recent events from that organ.
    """
    if organ not in ORGAN_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown organ '{organ}'. Valid organs: {', '.join(ORGAN_NAMES)}",
        )

    # Get the latest state for base health
    state = await db.get_latest_state_snapshot()
    base_health = state.get("health", 100) if state else 100

    # Get organ-specific events
    events_rows = await db.get_events_by_source(source=organ, limit=20)
    recent_events = [EventLog(**r) for r in events_rows]

    # Build organ-specific metrics
    metrics = await _build_organ_metrics(organ, db, state or {})

    # Derive status from organ health
    organ_health = await _compute_organ_health(organ, db, state or {}, base_health)

    return OrganSnapshot(
        name=organ,
        status=organ_health["status"],
        health_score=organ_health["score"],
        metrics=metrics,
        recent_events=recent_events,
    )


@router.get("/{organ}/history", response_model=List[TimelinePoint])
async def organ_history(
    organ: str,
    hours: int = Query(
        24, ge=1, le=168, description="Hours of history to include"
    ),
    db: StateDB = Depends(get_db),
) -> List[TimelinePoint]:
    """Return timeline history for a specific organ.

    Currently uses the global state_snapshots timeline as organ-specific
    data; future versions may include per-organ tables.
    """
    if organ not in ORGAN_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown organ '{organ}'. Valid organs: {', '.join(ORGAN_NAMES)}",
        )

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


# ── Helper Functions ──


def _organ_icon(organ_name: str) -> str:
    """Return a simple emoji icon for each organ."""
    icons = {
        "heart": "❤️",
        "autonomic": "⚙️",
        "immune": "🛡️",
        "proprioception": "🧠",
        "reflexes": "⚡",
        "dreams": "💭",
        "growth": "🌱",
    }
    return icons.get(organ_name, "🔬")


async def _build_organ_metrics(
    organ: str, db: StateDB, state: Dict[str, Any]
) -> Dict[str, Any]:
    """Build organ-specific metrics dict."""
    if organ == "heart":
        decisions = await db.get_heart_decisions(limit=10)
        return {
            "total_decisions": len(decisions),
            "recent_decisions": [
                {"action": d.get("action"), "decision": d.get("decision")}
                for d in decisions[:10]
            ],
            "rule_types": list(
                set(d.get("rule_type", "unknown") for d in decisions)
            ),
        }

    elif organ == "autonomic":
        return {
            "mode": state.get("mode", "normal"),
            "active_tasks": state.get("active_tasks", 0),
            "context_depth": state.get("context_depth", 0),
        }

    elif organ == "immune":
        threats = await db.get_threats()
        return {
            "active_threats": len(threats),
            "threat_types": list(
                set(t.get("threat_type", "unknown") for t in threats)
            ),
            "critical_count": len(
                [t for t in threats if t.get("status") == "critical"]
            ),
        }

    elif organ == "proprioception":
        return {
            "context_depth": state.get("context_depth", 0),
            "tokens_estimated": state.get("tokens_estimated", 0),
            "error_count": state.get("error_count", 0),
            "last_error": state.get("last_error"),
        }

    elif organ == "reflexes":
        reflexes = await db.get_reflex_log(limit=10)
        total = len(reflexes)
        successful = sum(1 for r in reflexes if r.get("success"))
        return {
            "recent_reflexes": total,
            "success_rate": (successful / total * 100) if total > 0 else 100,
            "types": list(
                set(r.get("match_type", "unknown") for r in reflexes)
            ),
        }

    elif organ == "dreams":
        return {
            "status": "idle",
            "last_compaction": None,
            "insights_generated": 0,
        }

    elif organ == "growth":
        return {
            "status": "nominal",
            "skills_available": 0,
            "adaptation_rate": "nominal",
        }

    return {}


async def _compute_organ_health(
    organ: str,
    db: StateDB,
    state: Dict[str, Any],
    base_health: int,
) -> Dict[str, Any]:
    """Compute health score and status for a specific organ."""
    if organ == "immune":
        threats = await db.get_threats()
        critical = len([t for t in threats if t.get("status") == "critical"])
        score = max(0, 100 - len(threats) * 10 - critical * 20)
    elif organ == "proprioception":
        depth = state.get("context_depth", 0) or 0
        score = max(0, base_health - depth * 2)
    elif organ == "reflexes":
        reflexes = await db.get_reflex_log(limit=10)
        score = max(0, 100 - len(reflexes) * 2)
    elif organ == "heart":
        score = max(0, base_health - 5)
    else:
        score = base_health

    if score >= 70:
        status = "healthy"
    elif score >= 40:
        status = "warning"
    else:
        status = "critical"

    return {"score": score, "status": status}
