"""ADAM OS Control Center — Config API Endpoints

Provides read/write access to application configuration
through the ConfigService.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Body

from app.services.config_service import config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Config"])


@router.get("")
async def get_config() -> Dict[str, Any]:
    """Return the full application configuration.

    Includes refresh intervals, thresholds, UI settings, and security options.
    """
    return config_service.get_config()


@router.post("/update")
async def update_config(
    updates: Dict[str, Any] = Body(..., description="Partial config dict to merge"),
) -> Dict[str, Any]:
    """Update configuration values with deep-merge semantics.

    Nested keys are merged recursively. Example:
    ```json
    {"thresholds": {"ram_warning": 80}, "ui": {"dark_mode": false}}
    ```
    """
    return config_service.update_config(updates)
