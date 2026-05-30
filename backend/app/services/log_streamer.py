"""ADAM OS Control Center — Log Streamer Service

In-memory rotating log buffer with SSE streaming support.
Stores the last N log entries in a deque and provides an async generator
for Server-Sent Events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from typing import Any, AsyncGenerator, Dict, List

logger = logging.getLogger(__name__)

# ── Default buffer size ──

DEFAULT_BUFFER_SIZE = 1000
SSE_STREAM_SLEEP = 0.5  # seconds between yielding when queue is empty


class LogStreamer:
    """In-memory rotating log buffer with SSE support.

    Stores up to ``buffer_size`` entries in a deque. Entries beyond
    the limit are silently dropped (oldest first).
    """

    def __init__(self, buffer_size: int = DEFAULT_BUFFER_SIZE):
        self._buffer: deque[Dict[str, Any]] = deque(maxlen=buffer_size)
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._buffer_size = buffer_size
        self._seq = 0

    # ── Public API ──

    def add_log(
        self,
        level: str = "info",
        source: str = "system",
        type: str = "log",
        message: str = "",
        **extra: Any,
    ) -> Dict[str, Any]:
        """Add a log entry to the buffer and notify SSE subscribers.

        Args:
            level: log level (debug, info, warning, error, critical)
            source: origin of the log entry (service name)
            type: log type (log, event, metric, alert)
            message: human-readable log message
            **extra: additional key-value pairs to include

        Returns:
            The created log entry dict.
        """
        entry: Dict[str, Any] = {
            "seq": self._seq,
            "ts": time.time(),
            "level": level,
            "source": source,
            "type": type,
            "message": message,
            **extra,
        }
        self._seq += 1
        self._buffer.append(entry)

        # Notify SSE subscribers (non-blocking, best-effort)
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: self._queue.put_nowait(entry))
        except (RuntimeError, asyncio.QueueFull):
            pass

        return entry

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent log entries from the buffer.

        Args:
            limit: maximum number of entries to return.

        Returns:
            List of log entry dicts, newest first.
        """
        logs = list(self._buffer)
        logs.reverse()
        return logs[:limit]

    async def stream_logs(self) -> AsyncGenerator[str, None]:
        """Async generator yielding SSE-formatted log entries.

        Yields JSON-serialized log entries as they arrive. When the
        queue is empty, yields a heartbeat comment every 0.5s to keep
        the connection alive.
        """
        # Flush existing buffer first
        for entry in list(self._buffer):
            yield f"data: {json.dumps(entry)}\n\n"

        while True:
            try:
                entry = await asyncio.wait_for(
                    self._queue.get(), timeout=SSE_STREAM_SLEEP
                )
                yield f"data: {json.dumps(entry)}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                yield f": heartbeat {time.time()}\n\n"

    @property
    def buffer_size(self) -> int:
        return self._buffer_size

    @property
    def count(self) -> int:
        return len(self._buffer)


# ── Module-level singleton ──

log_streamer = LogStreamer()
