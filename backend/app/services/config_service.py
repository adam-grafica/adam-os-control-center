"""ADAM OS Control Center — Config Service

Read/write application configuration stored as JSON on disk.
Provides default config with thresholds, UI settings, and security options.
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Default configuration ──

DEFAULT_CONFIG: Dict[str, Any] = {
    "refresh_interval_ms": 2000,
    "thresholds": {
        "ram_warning": 75,
        "ram_critical": 90,
        "cpu_warning": 80,
        "cpu_critical": 95,
        "disk_warning": 85,
        "disk_critical": 95,
    },
    "ui": {
        "dark_mode": True,
        "compact_view": False,
        "show_timeline": True,
        "log_level_display": "info",
    },
    "security": {
        "require_auth": False,
        "allowed_origins": ["*"],
        "free_ram_enabled": False,
    },
    "streaming": {
        "sse_heartbeat_interval": 30,
        "sse_log_interval": 0.5,
    },
}

DEFAULT_CONFIG_PATH = "/tmp/adam-os-control-center/backend/config.json"


class ConfigService:
    """JSON-backed configuration service.

    Reads config from a JSON file on disk. Falls back to DEFAULT_CONFIG
    if the file doesn't exist. Writes updates with deep-merge semantics.
    """

    def __init__(self, config_path: str | None = None):
        self._config_path = Path(config_path or DEFAULT_CONFIG_PATH)
        self._cache: Dict[str, Any] | None = None
        self._load()

    # ── Public API ──

    def get_config(self) -> Dict[str, Any]:
        """Return the full configuration dict."""
        if self._cache is None:
            self._load()
        return deepcopy(self._cache or DEFAULT_CONFIG)

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Apply updates to the configuration with deep-merge.

        Args:
            updates: partial config dict to merge in.

        Returns:
            The updated full configuration.
        """
        current = self._cache or DEFAULT_CONFIG
        merged = self._deep_merge(current, updates)
        self._cache = merged
        self._save()
        return deepcopy(merged)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a single config value by dot-separated key.

        Example: config.get("thresholds.ram_warning") -> 75
        """
        current = self._cache or DEFAULT_CONFIG
        parts = key.split(".")
        value = current
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
            if value is None:
                return default
        return value

    def reset_to_defaults(self) -> Dict[str, Any]:
        """Reset configuration to factory defaults."""
        self._cache = deepcopy(DEFAULT_CONFIG)
        self._save()
        return deepcopy(self._cache)

    # ── Internal ──

    def _load(self) -> None:
        """Load config from JSON file."""
        try:
            if self._config_path.is_file():
                raw = self._config_path.read_text(encoding="utf-8")
                data = json.loads(raw)
                # Merge with defaults so new keys are always present
                self._cache = self._deep_merge(deepcopy(DEFAULT_CONFIG), data)
                logger.info("Config loaded from %s", self._config_path)
            else:
                self._cache = deepcopy(DEFAULT_CONFIG)
                logger.info(
                    "Config file not found at %s — using defaults",
                    self._config_path,
                )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load config: %s — using defaults", exc)
            self._cache = deepcopy(DEFAULT_CONFIG)

    def _save(self) -> None:
        """Write config to JSON file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Config saved to %s", self._config_path)
        except OSError as exc:
            logger.warning("Failed to save config: %s", exc)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge override into base (mutates base)."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigService._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)
        return base


# ── Module-level singleton ──

config_service = ConfigService()
