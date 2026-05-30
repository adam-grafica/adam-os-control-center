"""ADAM OS Control Center — API Providers API Endpoints

Provides access to external API provider registry: listing, status,
and call recording via the ApiRegistry service.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

from app.services.api_registry import api_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/providers", tags=["API Providers"])


@router.get("")
async def list_providers() -> List[Dict[str, Any]]:
    """Return all registered API providers with status and stats.

    Sorted by enabled status first, then by name.
    """
    return api_registry.get_providers()


@router.get("/{provider_id}")
async def get_provider(provider_id: str) -> Dict[str, Any]:
    """Return a single API provider by ID.

    Includes aggregate stats (total calls, tokens, cost, avg latency).
    """
    provider = api_registry.get_provider(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider_id}' not found",
        )
    return provider


@router.post("/{provider_id}/status")
async def update_provider_status(
    provider_id: str,
    body: Dict[str, str] = Body(..., description="Body with 'status' field"),
) -> Dict[str, Any]:
    """Update a provider's operational status.

    Valid status values: online, offline, degraded, error, unknown.

    Request body:
    ```json
    {"status": "online"}
    ```
    """
    status = body.get("status", "")
    if not status:
        raise HTTPException(status_code=400, detail="'status' field is required")

    result = api_registry.update_provider_status(provider_id, status)
    if result is None:
        # Check if provider exists at all
        existing = api_registry.get_provider(provider_id)
        if existing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status value '{status}'",
        )
    return result
