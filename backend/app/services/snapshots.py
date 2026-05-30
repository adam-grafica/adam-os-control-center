"""ADAM OS Dashboard — Snapshot Service

Builds composite dashboard snapshots by querying the database and
applying derived state (mood, organ health, etc.).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.cache import snapshot_cache
from app.core.db import StateDB
from app.models.schemas import (
    DashboardSnapshot,
    EventLog,
    OrganHealth,
    ThreatMemory,
)

logger = logging.getLogger(__name__)


class SnapshotService:
    """Builds composite snapshots from the database with caching."""

    def __init__(self, db: StateDB):
        self._db = db

    async def get_current_snapshot(self) -> DashboardSnapshot:
        """Build and return a complete dashboard snapshot.

        Results are cached for SNAPSHOT_CACHE_TTL seconds.
        """
        # Try cache first
        cached = snapshot_cache.get("dashboard_snapshot")
        if cached is not None:
            return DashboardSnapshot(**cached)

        # Fetch raw data
        state = await self._db.get_latest_state_snapshot()
        threats = await self._db.get_threats()
        events = await self._db.get_events(limit=10)

        if state is None:
            snapshot = self._get_empty_snapshot()
        else:
            organs = await self._build_organs_snapshot(state)
            health = state.get("health", 100) or 100
            mood = self._calculate_mood(health, threats, state.get("mode", "normal"))
            mode = state.get("mode", "normal") or "normal"

            snapshot = DashboardSnapshot(
                organism_health=health,
                organism_mood=mood,
                current_mode=mode,
                active_threats=len(threats),
                organs=organs,
                recent_events=[EventLog(**e) for e in events],
                active_threats_list=[ThreatMemory(**t) for t in threats],
                snapshot_ts=datetime.utcnow().isoformat() + "Z",
            )

        # Cache the result
        snapshot_cache.set(
            "dashboard_snapshot", snapshot.model_dump(mode="json")
        )

        return snapshot

    async def _build_organs_snapshot(
        self, state: Dict[str, Any]
    ) -> Dict[str, OrganHealth]:
        """Build health status for all 7 organs from current state + DB queries."""
        health_score = state.get("health", 100) or 100

        # Individual organ data from their respective tables
        heart_decisions = await self._db.get_heart_decisions(limit=5)
        reflex_entries = await self._db.get_reflex_log(limit=5)

        organs = {}

        # ── Heart ──
        organs["heart"] = OrganHealth(
            status=self._health_to_status(health_score),
            health_score=max(0, health_score - 5),
            last_active=heart_decisions[0].get("ts") if heart_decisions else None,
            metrics={
                "total_decisions": len(heart_decisions),
                "recent_decisions": [
                    {"action": d.get("action"), "decision": d.get("decision")}
                    for d in heart_decisions[:5]
                ],
            },
        )

        # ── Autonomic ──
        organs["autonomic"] = OrganHealth(
            status=self._health_to_status(health_score),
            health_score=health_score,
            metrics={
                "mode": state.get("mode", "normal"),
                "active_tasks": state.get("active_tasks", 0),
                "context_depth": state.get("context_depth", 0),
            },
        )

        # ── Immune (threat-driven health) ──
        threats = await self._db.get_threats()
        critical_threats = [t for t in threats if t.get("status") == "critical"]
        immune_health = max(
            0, 100 - len(threats) * 10 - len(critical_threats) * 20
        )
        organs["immune"] = OrganHealth(
            status=self._health_to_status(immune_health),
            health_score=immune_health,
            metrics={
                "active_threats": len(threats),
                "critical_threats": len(critical_threats),
                "threat_types": list(
                    set(t.get("threat_type", "unknown") for t in threats)
                ),
            },
        )

        # ── Proprioception ──
        proprioception_health = max(
            0,
            health_score
            - (state.get("context_depth", 0) or 0) * 2,
        )
        organs["proprioception"] = OrganHealth(
            status=self._health_to_status(proprioception_health),
            health_score=proprioception_health,
            metrics={
                "context_depth": state.get("context_depth", 0),
                "tokens_estimated": state.get("tokens_estimated", 0),
                "error_count": state.get("error_count", 0),
            },
        )

        # ── Reflexes ──
        reflex_health = max(0, 100 - len(reflex_entries) * 2)
        organs["reflexes"] = OrganHealth(
            status=self._health_to_status(reflex_health),
            health_score=reflex_health,
            metrics={
                "recent_reflexes": len(reflex_entries),
                "success_rate": (
                    sum(
                        1 for r in reflex_entries if r.get("success")
                    )
                    / len(reflex_entries)
                    * 100
                    if reflex_entries
                    else 100
                ),
            },
        )

        # ── Dreams ──
        organs["dreams"] = OrganHealth(
            status=self._health_to_status(health_score),
            health_score=health_score,
            metrics={
                "last_compaction": None,
                "insights_generated": 0,
            },
        )

        # ── Growth ──
        organs["growth"] = OrganHealth(
            status=self._health_to_status(health_score),
            health_score=health_score,
            metrics={
                "skills_available": 0,
                "adaptation_rate": "nominal",
            },
        )

        return organs

    def _calculate_mood(
        self,
        health: int,
        threats: List[Dict[str, Any]],
        mode: str,
    ) -> str:
        """Derive organism mood from health, threats, and mode.

        Returns one of: thriving, stable, stressed, critical.
        """
        if health >= 85 and not threats and mode == "normal":
            return "thriving"
        if health >= 60 and mode != "critical":
            return "stable"
        if health >= 30 or mode == "safe":
            return "stressed"
        return "critical"

    def _health_to_status(self, health: int) -> str:
        """Convert a numeric health score to a status string."""
        if health >= 70:
            return "healthy"
        if health >= 40:
            return "warning"
        return "critical"

    def _get_empty_snapshot(self) -> DashboardSnapshot:
        """Return a default snapshot when no state exists yet."""
        now = datetime.utcnow().isoformat() + "Z"
        default_health = OrganHealth()
        return DashboardSnapshot(
            organism_health=100,
            organism_mood="stable",
            current_mode="normal",
            active_threats=0,
            organs={
                name: default_health
                for name in [
                    "heart",
                    "autonomic",
                    "immune",
                    "proprioception",
                    "reflexes",
                    "dreams",
                    "growth",
                ]
            },
            recent_events=[],
            active_threats_list=[],
            snapshot_ts=now,
        )


# ── Factory (not a FastAPI dependency to avoid type annotation conflicts) ──


def create_snapshot_service(db: StateDB) -> SnapshotService:
    """Create a SnapshotService instance with the given database handle."""
    return SnapshotService(db)
