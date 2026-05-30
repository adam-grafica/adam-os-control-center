"""ADAM OS Control Center — API Registry Service

Tracks external API providers, their status, usage metrics, and
cost accounting. Provides a simple in-memory registry with usage logs.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Default providers ──

DEFAULT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "type": "llm",
        "status": "unknown",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "enabled": True,
    },
    "anthropic": {
        "id": "anthropic",
        "name": "Anthropic",
        "type": "llm",
        "status": "unknown",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "enabled": True,
    },
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek",
        "type": "llm",
        "status": "unknown",
        "models": ["deepseek-chat", "deepseek-coder"],
        "enabled": True,
    },
    "huggingface": {
        "id": "huggingface",
        "name": "HuggingFace Hub",
        "type": "model_hub",
        "status": "unknown",
        "models": ["all-models"],
        "enabled": True,
    },
    "github": {
        "id": "github",
        "name": "GitHub API",
        "type": "devops",
        "status": "unknown",
        "enabled": True,
    },
    "firecrawl": {
        "id": "firecrawl",
        "name": "FireCrawl",
        "type": "web",
        "status": "unknown",
        "enabled": True,
    },
}


class ApiRegistry:
    """In-memory registry of API providers and their call metrics.

    Tracks:
      - Provider status and available models
      - Per-provider call history (tokens, latency, cost)
      - Aggregate statistics
    """

    def __init__(self):
        self._providers: Dict[str, Dict[str, Any]] = {}
        self._call_log: List[Dict[str, Any]] = []
        self._max_call_log = 10000
        self._reset()

    def _reset(self) -> None:
        """Initialize or reset providers to defaults."""
        self._providers = {
            pid: {**info} for pid, info in DEFAULT_PROVIDERS.items()
        }

    # ── Provider Queries ──

    def get_providers(self) -> List[Dict[str, Any]]:
        """Return all registered providers with current status and stats."""
        result = []
        for pid, provider in self._providers.items():
            entry = {**provider}
            # Attach aggregate stats
            stats = self._get_provider_stats(pid)
            if stats:
                entry["stats"] = stats
            result.append(entry)
        # Sort: enabled first, then by name
        result.sort(key=lambda p: (not p.get("enabled", False), p.get("name", "")))
        return result

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Return a single provider by ID."""
        provider = self._providers.get(provider_id)
        if provider is None:
            return None
        entry = {**provider}
        stats = self._get_provider_stats(provider_id)
        if stats:
            entry["stats"] = stats
        return entry

    def update_provider_status(
        self, provider_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        """Update a provider's operational status.

        Args:
            provider_id: the provider identifier.
            status: one of 'online', 'offline', 'degraded', 'error', 'unknown'.

        Returns:
            Updated provider dict or None if not found.
        """
        if provider_id not in self._providers:
            return None
        valid_statuses = {"online", "offline", "degraded", "error", "unknown"}
        if status not in valid_statuses:
            logger.warning(
                "Invalid status '%s' for provider %s. Valid: %s",
                status,
                provider_id,
                ", ".join(sorted(valid_statuses)),
            )
            return None
        self._providers[provider_id]["status"] = status
        self._providers[provider_id]["last_updated"] = time.time()
        logger.info("Provider %s status changed to %s", provider_id, status)
        return self.get_provider(provider_id)

    # ── Call Recording ──

    def record_api_call(
        self,
        provider_id: str,
        tokens: int = 0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        model: str = "",
        success: bool = True,
    ) -> Dict[str, Any]:
        """Record an API call for a provider.

        Args:
            provider_id: which provider was called.
            tokens: tokens used (input + output).
            latency_ms: call duration in milliseconds.
            cost: estimated cost in USD.
            model: model name used.
            success: whether the call succeeded.

        Returns:
            The recorded call entry.
        """
        entry: Dict[str, Any] = {
            "ts": time.time(),
            "provider_id": provider_id,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "cost": cost,
            "model": model,
            "success": success,
        }
        self._call_log.append(entry)

        # Trim log if it exceeds max
        if len(self._call_log) > self._max_call_log:
            excess = len(self._call_log) - self._max_call_log
            self._call_log = self._call_log[excess:]

        return entry

    def get_call_log(
        self, provider_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return recent API call records, newest first.

        Args:
            provider_id: filter to a specific provider (None = all).
            limit: max entries to return.
        """
        log = reversed(self._call_log)
        if provider_id:
            log = (e for e in log if e["provider_id"] == provider_id)
        return list(log)[:limit]

    # ── Internal ──

    def _get_provider_stats(self, provider_id: str) -> Dict[str, Any]:
        """Compute aggregate stats for a provider from the call log."""
        calls = [c for c in self._call_log if c["provider_id"] == provider_id]
        if not calls:
            return {}
        total_tokens = sum(c["tokens"] for c in calls)
        total_cost = sum(c["cost"] for c in calls)
        latencies = [c["latency_ms"] for c in calls if c["latency_ms"] > 0]
        successful = sum(1 for c in calls if c["success"])

        return {
            "total_calls": len(calls),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "success_rate": round(successful / len(calls) * 100, 1) if calls else 100,
        }


# ── Module-level singleton ──

api_registry = ApiRegistry()
