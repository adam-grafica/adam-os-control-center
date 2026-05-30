"""ADAM OS Dashboard — Simple TTL Cache

Thread-safe in-memory cache with configurable TTL per entry.
Used to cache state snapshots and reduce database reads.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from app.settings import settings


class SimpleCache:
    """Thread-safe time-to-live (TTL) cache.

    Each key has an independent expiration time. Getting an expired
    key returns None and removes the entry.
    """

    def __init__(self, default_ttl: float = 5.0):
        self._default_ttl = default_ttl
        self._store: Dict[str, Tuple[float, Any]] = {}  # key -> (expiry, value)

    def set(
        self, key: str, value: Any, ttl: Optional[float] = None
    ) -> None:
        """Store a value with optional TTL (defaults to class default)."""
        ttl = ttl if ttl is not None else self._default_ttl
        expiry = time.time() + ttl
        self._store[key] = (expiry, value)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value. Returns None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        expiry, value = entry
        if time.time() > expiry:
            # Expired — remove and return None
            self._store.pop(key, None)
            return None
        return value

    def invalidate(self, key: str) -> None:
        """Remove a specific key from cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from cache."""
        self._store.clear()

    @property
    def size(self) -> int:
        """Return the number of entries currently in cache."""
        return len(self._store)


# ── Module-level singleton for snapshot caching ──

snapshot_cache = SimpleCache(default_ttl=float(settings.SNAPSHOT_CACHE_TTL))
