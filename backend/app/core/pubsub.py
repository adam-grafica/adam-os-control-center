"""ADAM OS Dashboard — Simple Event Bus (Pub/Sub)

In-process publish/subscribe for broadcasting state updates to
connected SSE clients and other in-process listeners.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Set

logger = logging.getLogger(__name__)

# Type alias for an async callback that receives an event dict
AsyncEventHandler = Callable[[Dict[str, Any]], Any]


class SimpleEventBus:
    """In-process pub/sub event bus.

    Subscribers register async callbacks. When an event is published,
    all registered callbacks are awaited concurrently.
    """

    def __init__(self):
        self._subscribers: Set[AsyncEventHandler] = set()
        self._lock = asyncio.Lock()

    def subscribe(self, callback: AsyncEventHandler) -> Callable[[], None]:
        """Register an async callback to receive events.

        Returns a callable that unsubscribes the callback when invoked.
        """
        async def _register():
            async with self._lock:
                self._subscribers.add(callback)

        # Schedule the registration — this is safe from both sync and async contexts
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(_register())
            else:
                self._subscribers.add(callback)
        except RuntimeError:
            self._subscribers.add(callback)

        def unsubscribe() -> None:
            async def _unregister():
                async with self._lock:
                    self._subscribers.discard(callback)
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(_unregister())
                else:
                    self._subscribers.discard(callback)
            except RuntimeError:
                self._subscribers.discard(callback)

        return unsubscribe

    async def publish(self, event: Dict[str, Any]) -> None:
        """Publish an event dict to all subscribers concurrently."""
        async with self._lock:
            targets = list(self._subscribers)

        if not targets:
            return

        results = await asyncio.gather(
            *[self._safe_dispatch(cb, event) for cb in targets],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Subscriber %s raised %s: %s",
                    targets[i],
                    type(result).__name__,
                    result,
                )

    async def broadcast_state_update(self, snapshot: Dict[str, Any]) -> None:
        """Convenience: publish a 'state_update' event with a snapshot payload.

        This is the primary method used by SnapshotService to notify SSE streams.
        """
        await self.publish(
            {
                "type": "state_update",
                "data": snapshot,
            }
        )

    async def _safe_dispatch(
        self, callback: AsyncEventHandler, event: Dict[str, Any]
    ) -> None:
        """Invoke a single callback, catching any exception."""
        try:
            result = callback(event)
            if result is not None and hasattr(result, "__await__"):
                await result
        except Exception as exc:
            logger.error(
                "Event dispatch error in %s: %s", callback, exc, exc_info=True
            )

    @property
    def subscriber_count(self) -> int:
        """Return the number of currently registered subscribers."""
        return len(self._subscribers)


# ── Module-level singleton ──

event_bus = SimpleEventBus()
