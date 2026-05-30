"""ADAM OS Dashboard — Token Tracker Service

Read-only SQLite service that queries Hermes Agent's session database
to expose token consumption metrics via the token_tracker API.

Connects to: /home/adamcloud/.hermes/profiles/axon/state.db
Uses READ-ONLY transactions only — never writes to the Hermes DB.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from app.settings import settings

logger = logging.getLogger(__name__)

# Columns we care about from the sessions table
TOKEN_COLUMNS = [
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
]

# ── DB Connection ──


def _get_connection() -> Optional[sqlite3.Connection]:
    """Open a READ-ONLY connection to the Hermes state DB.

    Uses timeout=5 to handle concurrent writes from Hermes Agent.
    Returns None if the DB is unreachable or locked.
    """
    if not os.path.isfile(settings.HERMES_DB_PATH):
        logger.warning("Hermes session DB not found: %s", settings.HERMES_DB_PATH)
        return None
    try:
        conn = sqlite3.connect(settings.HERMES_DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        # Ensure we never accidentally write
        conn.execute("PRAGMA query_only = ON;")
        return conn
    except sqlite3.OperationalError as exc:
        logger.error("Failed to connect to Hermes session DB: %s", exc)
        return None


def _safe_query(
    query: str,
    params: tuple = (),
    fetch: str = "all",
) -> Any:
    """Run a SELECT query with error handling and connection management.

    Args:
        query: SQL SELECT statement
        params: Bound parameters
        fetch: 'all' returns list of dicts, 'one' returns single dict or None

    Returns:
        List[Dict] for fetch='all', Dict|None for fetch='one', or fallback
        empty result on error.
    """
    conn = _get_connection()
    if not conn:
        return [] if fetch == "all" else None
    try:
        cursor = conn.execute(query, params)
        if fetch == "one":
            row = cursor.fetchone()
            return dict(row) if row else None
        return [dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError as exc:
        logger.error("SQLite query failed: %s | Query: %s", exc, query[:120])
        return [] if fetch == "all" else None
    except Exception as exc:
        logger.error("Unexpected DB error: %s", exc, exc_info=True)
        return [] if fetch == "all" else None
    finally:
        conn.close()


def _sum_tokens(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """Sum token columns across multiple session rows."""
    totals: Dict[str, int] = {}
    for col in TOKEN_COLUMNS + ["estimated_cost_usd"]:
        totals[col] = sum(r.get(col) or 0 for r in rows)
    totals["total_tokens"] = sum(
        totals.get(c, 0) for c in TOKEN_COLUMNS if c != "reasoning_tokens"
    )
    return totals


# ═══════════════════════════════════════════════════════════════════
# Query Functions
# ═══════════════════════════════════════════════════════════════════


def get_session_tokens(session_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed token data for a single session."""
    return _safe_query(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,),
        fetch="one",
    )


def get_recent_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """Return the most recent sessions with token data.

    Ordered by started_at descending.
    """
    rows = _safe_query(
        """SELECT id, source, model, started_at, ended_at,
                  message_count, tool_call_count, api_call_count,
                  input_tokens, output_tokens, cache_read_tokens,
                  cache_write_tokens, reasoning_tokens,
                  billing_provider, estimated_cost_usd, actual_cost_usd
           FROM sessions
           ORDER BY started_at DESC
           LIMIT ?""",
        (limit,),
        fetch="all",
    )
    return rows


def get_daily_summary(days: int = 30) -> List[Dict[str, Any]]:
    """Aggregate token consumption by calendar day.

    Returns list of dicts with keys: date, input_tokens, output_tokens,
    cache_read_tokens, cache_write_tokens, reasoning_tokens,
    total_tokens, session_count, estimated_cost_usd.
    """
    rows = _safe_query(
        """SELECT date(datetime(started_at, 'unixepoch')) AS day,
                  SUM(input_tokens)       AS input_tokens,
                  SUM(output_tokens)      AS output_tokens,
                  SUM(cache_read_tokens)  AS cache_read_tokens,
                  SUM(cache_write_tokens) AS cache_write_tokens,
                  SUM(reasoning_tokens)   AS reasoning_tokens,
                  COUNT(*)                AS session_count,
                  SUM(estimated_cost_usd) AS estimated_cost_usd
           FROM sessions
           WHERE started_at >= ?1
           GROUP BY day
           ORDER BY day DESC""",
        (time.time() - days * 86400,),
        fetch="all",
    )
    # Add computed total_tokens per row
    for row in rows:
        row["total_tokens"] = (
            (row.get("input_tokens") or 0)
            + (row.get("output_tokens") or 0)
            + (row.get("cache_read_tokens") or 0)
            + (row.get("cache_write_tokens") or 0)
        )
    return rows


def get_weekly_summary(weeks: int = 12) -> List[Dict[str, Any]]:
    """Aggregate token consumption by ISO week.

    Returns list of dicts with keys: week_start, input_tokens,
    output_tokens, cache_read_tokens, cache_write_tokens,
    reasoning_tokens, total_tokens, session_count, estimated_cost_usd.
    """
    cutoff = time.time() - weeks * 7 * 86400
    rows = _safe_query(
        """SELECT date(datetime(started_at, 'unixepoch'), 'weekday 0', '-6 days') AS week_start,
                  SUM(input_tokens)       AS input_tokens,
                  SUM(output_tokens)      AS output_tokens,
                  SUM(cache_read_tokens)  AS cache_read_tokens,
                  SUM(cache_write_tokens) AS cache_write_tokens,
                  SUM(reasoning_tokens)   AS reasoning_tokens,
                  COUNT(*)                AS session_count,
                  SUM(estimated_cost_usd) AS estimated_cost_usd
           FROM sessions
           WHERE started_at >= ?
           GROUP BY week_start
           ORDER BY week_start DESC""",
        (cutoff,),
        fetch="all",
    )
    for row in rows:
        row["total_tokens"] = (
            (row.get("input_tokens") or 0)
            + (row.get("output_tokens") or 0)
            + (row.get("cache_read_tokens") or 0)
            + (row.get("cache_write_tokens") or 0)
        )
    return rows


def get_provider_summary() -> List[Dict[str, Any]]:
    """Aggregate token consumption by billing_provider.

    Returns list of dicts with keys: provider, input_tokens,
    output_tokens, cache_read_tokens, cache_write_tokens,
    reasoning_tokens, total_tokens, session_count,
    estimated_cost_usd, model.
    """
    rows = _safe_query(
        """SELECT COALESCE(billing_provider, 'unknown') AS provider,
                  COALESCE(model, 'unknown')            AS model,
                  SUM(input_tokens)       AS input_tokens,
                  SUM(output_tokens)      AS output_tokens,
                  SUM(cache_read_tokens)  AS cache_read_tokens,
                  SUM(cache_write_tokens) AS cache_write_tokens,
                  SUM(reasoning_tokens)   AS reasoning_tokens,
                  COUNT(*)                AS session_count,
                  SUM(estimated_cost_usd) AS estimated_cost_usd
           FROM sessions
           GROUP BY provider, model
           ORDER BY provider, model""",
        fetch="all",
    )
    for row in rows:
        row["total_tokens"] = (
            (row.get("input_tokens") or 0)
            + (row.get("output_tokens") or 0)
            + (row.get("cache_read_tokens") or 0)
            + (row.get("cache_write_tokens") or 0)
        )
    return rows


def get_live_session() -> Optional[Dict[str, Any]]:
    """Return the most recent session that has no ended_at (still active).

    If no live session exists, returns the most recent session overall
    (in case Hermes ended it very recently but it's still informative).
    """
    # First try: session without ended_at (active)
    row = _safe_query(
        "SELECT * FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        fetch="one",
    )
    if row:
        row["_live"] = True
        return row

    # Fallback: most recent session in last 5 minutes
    row = _safe_query(
        "SELECT * FROM sessions WHERE started_at >= ? ORDER BY started_at DESC LIMIT 1",
        (time.time() - 300,),
        fetch="one",
    )
    if row:
        row["_live"] = False
        return row

    # Last resort: absolute most recent session
    row = _safe_query(
        "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1",
        fetch="one",
    )
    if row:
        row["_live"] = False
        return row

    return None


def get_all_time_totals() -> Dict[str, Any]:
    """Compute cumulative token totals across all sessions.

    Returns dict with input_tokens, output_tokens, cache_read_tokens,
    cache_write_tokens, reasoning_tokens, total_tokens,
    total_sessions, total_messages, total_tool_calls,
    total_api_calls, estimated_cost_usd.
    """
    row = _safe_query(
        """SELECT
                  COALESCE(SUM(input_tokens), 0)       AS input_tokens,
                  COALESCE(SUM(output_tokens), 0)      AS output_tokens,
                  COALESCE(SUM(cache_read_tokens), 0)  AS cache_read_tokens,
                  COALESCE(SUM(cache_write_tokens), 0) AS cache_write_tokens,
                  COALESCE(SUM(reasoning_tokens), 0)   AS reasoning_tokens,
                  COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                  COUNT(*)                             AS total_sessions,
                  COALESCE(SUM(message_count), 0)      AS total_messages,
                  COALESCE(SUM(tool_call_count), 0)    AS total_tool_calls,
                  COALESCE(SUM(api_call_count), 0)     AS total_api_calls
           FROM sessions""",
        fetch="one",
    )

    if not row:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "total_sessions": 0,
            "total_messages": 0,
            "total_tool_calls": 0,
            "total_api_calls": 0,
            "estimated_cost_usd": 0.0,
        }

    row["total_tokens"] = (
        row.get("input_tokens", 0)
        + row.get("output_tokens", 0)
        + row.get("cache_read_tokens", 0)
        + row.get("cache_write_tokens", 0)
    )
    return row
