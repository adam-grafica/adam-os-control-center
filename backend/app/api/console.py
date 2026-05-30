"""ADAM OS Control Center — Console API Endpoints

Provides real-time log streaming via SSE and recent log queries
through the LogStreamer service.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.services.log_streamer import log_streamer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/console", tags=["Console"])


@router.get("/stream")
async def stream_logs(request: Request) -> EventSourceResponse:
    """SSE endpoint that streams log entries in real-time.

    Clients receive a new 'data' event for each log entry as it arrives.
    Heartbeat comments (starting with ':') are sent every 0.5s to keep
    the connection alive when no logs are produced.
    """
    return EventSourceResponse(log_streamer.stream_logs())


@router.get("/logs")
async def recent_logs(
    limit: int = Query(50, ge=1, le=1000, description="Number of log entries to return"),
) -> List[Dict[str, Any]]:
    """Return recent log entries from the in-memory buffer.

    Entries are ordered newest first. Default limit is 50, max 1000.
    """
    return log_streamer.get_recent_logs(limit=limit)
