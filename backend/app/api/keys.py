"""ADAM OS Dashboard — API Key Management Endpoints

REST API for managing API keys across providers (opencode-zen, nvidia, mistral).
Supports CRUD, health checks, auto-detection, and provider summaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ApiKeyCreate,
    ApiKeyEntry,
    ApiKeyTestResult,
    ApiKeyUpdate,
    ProviderHealthSummary,
)
from app.services.keys_manager import (
    auto_detect_provider_health,
    create_key,
    delete_key,
    get_key,
    get_provider_summaries,
    list_keys,
    test_all_keys,
    test_key,
    update_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


# ── List & Summaries ──


@router.get("", response_model=List[ApiKeyEntry])
async def get_all_keys() -> List[ApiKeyEntry]:
    """List all configured API keys (values masked)."""
    return list_keys()


@router.get("/summary", response_model=List[ProviderHealthSummary])
async def provider_summary() -> List[ProviderHealthSummary]:
    """Get health summaries for each provider."""
    return get_provider_summaries()


@router.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """Quick health check — tests first active key per provider."""
    return await auto_detect_provider_health()


# ── CRUD ──


@router.post("", response_model=ApiKeyEntry, status_code=201)
async def add_key(payload: ApiKeyCreate) -> ApiKeyEntry:
    """Add a new API key.
    
    The key value is stored in .env; the registry only stores metadata.
    """
    if payload.provider not in ("opencode-zen", "nvidia", "mistral"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{payload.provider}'. "
            f"Valid: opencode-zen, nvidia, mistral",
        )
    if payload.tier not in ("main", "fallback", "round-robin"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier '{payload.tier}'. "
            f"Valid: main, fallback, round-robin",
        )
    return create_key(payload)


@router.get("/{key_id}", response_model=ApiKeyEntry)
async def get_single_key(key_id: str) -> ApiKeyEntry:
    """Get details for a single API key (value masked)."""
    key = get_key(key_id)
    if not key:
        raise HTTPException(
            status_code=404, detail=f"API key not found: {key_id}"
        )
    return key


@router.put("/{key_id}", response_model=ApiKeyEntry)
async def edit_key(key_id: str, payload: ApiKeyUpdate) -> ApiKeyEntry:
    """Update an existing API key.
    
    Pass a new key_value to update the .env; leave null to keep existing.
    """
    updated = update_key(key_id, payload)
    if not updated:
        raise HTTPException(
            status_code=404, detail=f"API key not found: {key_id}"
        )
    return updated


@router.delete("/{key_id}")
async def remove_key(key_id: str) -> Dict[str, Any]:
    """Delete an API key from the registry.
    
    Note: the key value remains in .env for safety.
    """
    deleted = delete_key(key_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"API key not found: {key_id}"
        )
    return {"status": "deleted", "id": key_id}


# ── Testing ──


@router.post("/test/{key_id}", response_model=ApiKeyTestResult)
async def test_single_key(key_id: str) -> ApiKeyTestResult:
    """Test a single API key: make request to provider's endpoint.
    
    Updates the key's health status in the registry.
    """
    result = await test_key(key_id)
    if not result:
        raise HTTPException(
            status_code=404, detail=f"API key not found: {key_id}"
        )
    return result


@router.post("/test-all", response_model=Dict[str, List[ApiKeyTestResult]])
async def test_all_keys_endpoint() -> Dict[str, List[ApiKeyTestResult]]:
    """Test ALL active keys across all providers.
    
    Runs tests concurrently per provider. Updates all statuses.
    """
    return await test_all_keys()
