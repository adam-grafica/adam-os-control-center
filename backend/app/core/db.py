"""ADAM OS Dashboard — Async SQLite Database Access

Read-only connection to the state database using aiosqlite with WAL mode.
URI-based read-only connection ensures no accidental writes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiosqlite
from app.settings import settings

logger = logging.getLogger(__name__)

# ── URI for read-only access ──
# Use file: URI with ?mode=ro to force read-only
_STATE_DB_URI = f"file:{settings.STATE_DB_PATH}?mode=ro"


class StateDB:
    """Async read-only interface to the ADAM OS SQLite state database.

    All methods return dictionaries. Methods are safe to call from
    concurrent async contexts — aiosqlite uses a single connection
    with its own lock internally.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or settings.STATE_DB_PATH
        self._conn: aiosqlite.Connection | None = None
        self._connected = False

    async def connect(self) -> None:
        """Open the read-only connection and verify WAL mode.

        Also executes the extended schema (schema_ext.sql) if available
        to ensure auxiliary tables exist.
        """
        if self._connected:
            return
        # Use URI mode for read-only
        uri = f"file:{self._db_path}?mode=ro"
        self._conn = await aiosqlite.connect(uri, uri=True)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA query_only = 1;")
        # Check WAL mode
        cursor = await self._conn.execute("PRAGMA journal_mode;")
        row = await cursor.fetchone()
        journal_mode = row[0] if row else "unknown"
        logger.info(
            "StateDB connected (read-only): %s | journal_mode=%s",
            self._db_path,
            journal_mode,
        )
        self._connected = True

        # ── Execute extended schema ──
        await self._run_schema_ext()

    async def _run_schema_ext(self) -> None:
        """Execute schema_ext.sql to ensure auxiliary tables exist.

        This is best-effort: if the file is missing or the DB is
        read-only (expected), the error is logged but not re-raised.
        """
        schema_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "schema_ext.sql"
        )
        if not os.path.isfile(schema_path):
            logger.debug("Extended schema not found at %s — skipping", schema_path)
            return
        try:
            schema_sql = await asyncio.get_event_loop().run_in_executor(
                None, lambda: open(schema_path, "r").read()
            )
            await self._conn.executescript(schema_sql)
            logger.info("Extended schema applied from %s", schema_path)
        except Exception as exc:
            logger.warning(
                "Could not apply extended schema (read-only DB?): %s", exc
            )

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._conn and self._connected:
            await self._conn.close()
            self._conn = None
            self._connected = False
            logger.info("StateDB disconnected")

    # ── State Snapshots ──

    async def get_latest_state_snapshot(self) -> Dict[str, Any] | None:
        """Return the most recent state snapshot row."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM state_snapshots ORDER BY rowid DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    # ── Events ──

    async def get_events(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Return paginated events ordered by timestamp descending."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM events_log ORDER BY ts DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_events_by_type(
        self, event_type: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return events filtered by event_type, ordered by timestamp desc."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM events_log WHERE event_type = ? ORDER BY ts DESC LIMIT ?",
            (event_type, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ── Threats ──

    async def get_threats(self) -> List[Dict[str, Any]]:
        """Return active threats (monitoring or critical)."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM threat_memory WHERE status IN ('monitoring', 'critical') ORDER BY last_seen DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ── Timeline / History ──

    async def get_state_timeline(
        self, hours: int = 24, limit: int = 288
    ) -> List[Dict[str, Any]]:
        """Return state snapshots from the last N hours for timeline charts.

        Args:
            hours: How many hours of history to include.
            limit: Maximum number of rows to return.

        Returns:
            List of state snapshot dicts ordered by timestamp ascending.
        """
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        async with self._conn.execute(
            "SELECT * FROM state_snapshots WHERE ts >= ? ORDER BY ts ASC LIMIT ?",
            (cutoff, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ── Organ-specific helpers ──

    async def get_events_by_source(
        self, source: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return events filtered by source (organ name)."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM events_log WHERE source = ? ORDER BY ts DESC LIMIT ?",
            (source, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_heart_decisions(
        self, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return recent heart decisions."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM heart_decisions ORDER BY ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_reflex_log(
        self, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Return recent reflex log entries."""
        if not self._conn:
            raise RuntimeError("StateDB not connected")
        async with self._conn.execute(
            "SELECT * FROM reflex_log ORDER BY ts DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ── Module-level singleton ──

_db: StateDB | None = None


async def get_db() -> StateDB:
    """FastAPI dependency that returns the singleton StateDB instance."""
    global _db
    if _db is None:
        _db = StateDB()
        await _db.connect()
    return _db


async def init_db() -> None:
    """Initialize the global database connection."""
    global _db
    if _db is None:
        _db = StateDB()
        await _db.connect()


async def close_db() -> None:
    """Close the global database connection."""
    global _db
    if _db is not None:
        await _db.disconnect()
        _db = None
