"""ADAM OS Dashboard — API Keys Manager Service

Manages API key registry in a JSON file, syncs with .env files,
and performs health checks against each provider's API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    httpx = None  # type: ignore
    _HAS_HTTPX = False

from app.models.schemas import (
    ApiKeyCreate,
    ApiKeyEntry,
    ApiKeyTestResult,
    ApiKeyUpdate,
    ProviderHealthSummary,
)
from app.settings import settings

logger = logging.getLogger(__name__)

# ── Provider configuration ──

PROVIDER_CONFIG: Dict[str, Dict[str, Any]] = {
    "opencode-zen": {
        "model": "deepseek-v4-flash-free",
        "base_url": "https://api.opencode.zen/v1",
        "tier": "main",
        "test_endpoint": "/models",
        "env_prefix": "OPENCODE_ZEN_API_KEY",
        "color": "#3b82f6",
    },
    "nvidia": {
        "model": "deepseek-ai/deepseek-v4-flash",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "tier": "fallback",
        "test_endpoint": "/models",
        "env_prefix": "NVIDIA_API_KEY",
        "color": "#76b900",
    },
    "mistral": {
        "model": "mistral-medium-3-5",
        "base_url": "https://api.mistral.ai/v1",
        "tier": "fallback",
        "test_endpoint": "/models",
        "env_prefix": "MISTRAL_API_KEY",
        "color": "#ff7000",
    },
}

KEYS_DB_PATH = os.path.join(
    settings.ADAM_OS_ROOT,
    "state",
    "api_keys.json",
)
ENV_PATH = os.path.join(
    settings.ADAM_OS_ROOT, "..", ".env"
)
HERMES_ENV_PATH = os.path.join(
    "/home/adamcloud/.hermes", ".env"
)


# ═══════════════════════════════════════════════════════════════════
# JSON Store
# ═══════════════════════════════════════════════════════════════════


def _check_httpx() -> None:
    """Raise RuntimeError if httpx is not available."""
    if not _HAS_HTTPX:
        raise RuntimeError(
            "httpx is not installed. Install it with: pip install httpx"
        )


def _ensure_keys_db() -> str:
    """Ensure keys directory exists and return path."""
    os.makedirs(os.path.dirname(KEYS_DB_PATH), exist_ok=True)
    if not os.path.isfile(KEYS_DB_PATH):
        with open(KEYS_DB_PATH, "w") as f:
            json.dump([], f)
    return KEYS_DB_PATH


def _read_keys_db() -> List[Dict[str, Any]]:
    """Read all keys from JSON store."""
    _ensure_keys_db()
    try:
        with open(KEYS_DB_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _write_keys_db(keys: List[Dict[str, Any]]) -> None:
    """Write keys to JSON store."""
    os.makedirs(os.path.dirname(KEYS_DB_PATH), exist_ok=True)
    with open(KEYS_DB_PATH, "w") as f:
        json.dump(keys, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════
# Env file management
# ═══════════════════════════════════════════════════════════════════


def _get_env_path() -> str:
    """Return the .env file path that exists, preferring the Hermes one."""
    expanded = os.path.expanduser(HERMES_ENV_PATH)
    if os.path.isfile(expanded):
        return expanded
    expanded2 = os.path.expanduser(ENV_PATH)
    if os.path.isfile(expanded2):
        return expanded2
    return expanded


def _read_env() -> Dict[str, str]:
    """Read current .env file into dict."""
    env_path = _get_env_path()
    env: Dict[str, str] = {}
    if not os.path.isfile(env_path):
        return env
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _write_env(env: Dict[str, str]) -> None:
    """Write env dict to .env file, preserving comments."""
    env_path = _get_env_path()
    os.makedirs(os.path.dirname(env_path), exist_ok=True)

    # Read existing to preserve comments
    existing_lines: List[str] = []
    if os.path.isfile(env_path):
        with open(env_path, "r") as f:
            existing_lines = f.readlines()

    # Build new content: update existing vars, keep comments
    written_keys: set = set()
    new_lines: List[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in env:
                new_lines.append(f'{key}="{env[key]}"\n')
                written_keys.add(key)
                continue
        new_lines.append(line)

    # Add any keys not present
    for key, val in env.items():
        if key not in written_keys:
            new_lines.append(f'{key}="{val}"\n')

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    # Also update runtime env so test requests can find them
    for key, val in env.items():
        os.environ[key] = val


# ═══════════════════════════════════════════════════════════════════
# Key masking
# ═══════════════════════════════════════════════════════════════════


def _mask_key(key: str) -> str:
    """Show only last 4 characters."""
    if len(key) <= 8:
        return "****" + key[-4:]
    return key[:2] + "****" + key[-4:]


def _preview_key(key: str) -> str:
    """Return last 4 chars for identification."""
    return key[-4:] if len(key) >= 4 else key


def _generate_env_var(provider: str, position: int) -> str:
    """Generate standard env var name for a key."""
    prefix = PROVIDER_CONFIG[provider]["env_prefix"]
    if position == 0:
        return prefix  # First key uses base name
    return f"{prefix}_{position + 1}"


# ═══════════════════════════════════════════════════════════════════
# CRUD Operations
# ═══════════════════════════════════════════════════════════════════


def list_keys() -> List[ApiKeyEntry]:
    """Return all keys (values masked)."""
    keys = _read_keys_db()
    return [ApiKeyEntry(**k) for k in keys]


def get_key(key_id: str) -> Optional[ApiKeyEntry]:
    """Return a single key by ID."""
    keys = _read_keys_db()
    for k in keys:
        if k["id"] == key_id:
            return ApiKeyEntry(**k)
    return None


def get_key_value(key_id: str) -> Optional[str]:
    """Return the actual key value from .env for a given key ID."""
    keys = _read_keys_db()
    for k in keys:
        if k["id"] == key_id:
            env = _read_env()
            return env.get(k["key_env_var"])
    return None


def create_key(payload: ApiKeyCreate) -> ApiKeyEntry:
    """Create a new API key entry and write to .env."""
    keys = _read_keys_db()

    # Calculate position
    provider_keys = [k for k in keys if k["provider"] == payload.provider]
    position = (
        payload.position
        if payload.position is not None
        else (max((k["position"] for k in provider_keys), default=-1) + 1)
    )

    # Generate env var name
    env_var = payload.key_env_var or _generate_env_var(
        payload.provider, position
    )

    # Create entry
    key_id = str(uuid.uuid4())
    entry: Dict[str, Any] = {
        "id": key_id,
        "provider": payload.provider,
        "tier": payload.tier,
        "key_alias": payload.key_alias,
        "key_env_var": env_var,
        "key_preview": _preview_key(payload.key_value),
        "is_active": True,
        "position": position,
        "last_checked": None,
        "last_status": "unknown",
        "error_message": None,
        "model": payload.model
        or PROVIDER_CONFIG.get(payload.provider, {}).get("model"),
        "base_url": payload.base_url
        or PROVIDER_CONFIG.get(payload.provider, {}).get("base_url"),
    }

    keys.append(entry)
    _write_keys_db(keys)

    # Write key value to .env
    env = _read_env()
    env[env_var] = payload.key_value
    _write_env(env)

    return ApiKeyEntry(**entry)


def update_key(key_id: str, payload: ApiKeyUpdate) -> Optional[ApiKeyEntry]:
    """Update an existing key entry."""
    keys = _read_keys_db()
    for i, k in enumerate(keys):
        if k["id"] == key_id:
            if payload.key_alias is not None:
                keys[i]["key_alias"] = payload.key_alias
            if payload.is_active is not None:
                keys[i]["is_active"] = payload.is_active
            if payload.position is not None:
                keys[i]["position"] = payload.position
            if payload.model is not None:
                keys[i]["model"] = payload.model
            if payload.base_url is not None:
                keys[i]["base_url"] = payload.base_url

            # If key_value provided, update .env and refresh preview
            if payload.key_value is not None:
                env = _read_env()
                env[keys[i]["key_env_var"]] = payload.key_value
                _write_env(env)
                keys[i]["key_preview"] = _preview_key(payload.key_value)
                # Reset health status since key changed
                keys[i]["last_status"] = "unknown"
                keys[i]["last_checked"] = None
                keys[i]["error_message"] = None

            _write_keys_db(keys)
            return ApiKeyEntry(**keys[i])
    return None


def delete_key(key_id: str) -> bool:
    """Delete a key entry. Does NOT remove from .env (safe cleanup)."""
    keys = _read_keys_db()
    for i, k in enumerate(keys):
        if k["id"] == key_id:
            keys.pop(i)
            _write_keys_db(keys)
            return True
    return False


# ═══════════════════════════════════════════════════════════════════
# Health Checks
# ═══════════════════════════════════════════════════════════════════


async def test_key(
    key_id: str, timeout: int = 15
) -> Optional[ApiKeyTestResult]:
    """Test a single API key by making a lightweight request.

    Returns the test result and also updates the stored status.
    """
    _check_httpx()
    keys = _read_keys_db()
    entry = None
    for k in keys:
        if k["id"] == key_id:
            entry = k
            break

    if not entry:
        return None

    provider = entry["provider"]
    key_value = get_key_value(key_id)
    if not key_value:
        result = ApiKeyTestResult(
            id=key_id,
            key_alias=entry["key_alias"],
            provider=provider,
            status="error",
            message="Key value not found in .env",
        )
        _update_key_status(key_id, "error", result.message)
        return result

    config = PROVIDER_CONFIG.get(provider, {})
    base_url = entry.get("base_url") or config.get("base_url", "")
    test_endpoint = config.get("test_endpoint", "/v1/models")
    url = base_url.rstrip("/") + test_endpoint

    headers = {
        "Authorization": f"Bearer {key_value}",
        "Content-Type": "application/json",
    }

    start = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            response = await client.get(url, headers=headers)
            elapsed = int((asyncio.get_event_loop().time() - start) * 1000)

            if response.status_code == 200:
                status = "healthy"
                message = f"OK ({response.status_code}, {elapsed}ms)"
            elif response.status_code == 401 or response.status_code == 403:
                status = "error"
                message = f"Authentication failed ({response.status_code})"
            elif response.status_code == 429:
                status = "degraded"
                message = f"Rate limited ({response.status_code})"
            else:
                status = "degraded"
                message = (
                    f"Unexpected response ({response.status_code}, {elapsed}ms)"
                )

            result = ApiKeyTestResult(
                id=key_id,
                key_alias=entry["key_alias"],
                provider=provider,
                status=status,
                latency_ms=elapsed,
                message=message,
                http_status=response.status_code,
            )
            _update_key_status(key_id, status, message if status != "healthy" else None)
            return result

    except httpx.TimeoutException:
        elapsed = int((asyncio.get_event_loop().time() - start) * 1000)
        result = ApiKeyTestResult(
            id=key_id,
            key_alias=entry["key_alias"],
            provider=provider,
            status="degraded",
            latency_ms=elapsed,
            message=f"Request timed out ({elapsed}ms)",
        )
        _update_key_status(key_id, "degraded", result.message)
        return result

    except Exception as e:
        result = ApiKeyTestResult(
            id=key_id,
            key_alias=entry["key_alias"],
            provider=provider,
            status="error",
            message=f"Connection failed: {type(e).__name__}",
        )
        _update_key_status(key_id, "error", str(e))
        return result


async def test_all_keys(
    timeout: int = 15,
) -> Dict[str, List[ApiKeyTestResult]]:
    """Test all active keys across all providers.

    Returns dict keyed by provider name.
    """
    keys = list_keys()
    active = [k for k in keys if k.is_active]

    # Run tests concurrently per provider
    results: Dict[str, List[ApiKeyTestResult]] = {}
    tasks = []

    for key in active:
        task = test_key(key.id, timeout=timeout)
        tasks.append((key.provider, task))

    for provider, task in tasks:
        result = await task
        if result:
            results.setdefault(provider, []).append(result)

    return results


def get_provider_summaries() -> List[ProviderHealthSummary]:
    """Generate health summaries for each configured provider."""
    keys = list_keys()
    summaries: List[ProviderHealthSummary] = []

    for provider, config in PROVIDER_CONFIG.items():
        provider_keys = [k for k in keys if k.provider == provider]
        active = [k for k in provider_keys if k.is_active]
        healthy = [k for k in active if k.last_status == "healthy"]
        degraded = [k for k in active if k.last_status == "degraded"]
        error = [k for k in active if k.last_status == "error"]

        if not active:
            overall = "unknown"
        elif healthy and not degraded and not error:
            overall = "healthy"
        elif error and not healthy:
            overall = "error"
        elif degraded or error:
            overall = "degraded"
        else:
            overall = "healthy"

        summaries.append(
            ProviderHealthSummary(
                provider=provider,
                model=config["model"],
                total_keys=len(provider_keys),
                active_keys=len(active),
                healthy_keys=len(healthy),
                degraded_keys=len(degraded),
                error_keys=len(error),
                overall_status=overall,
                tier=config["tier"],
            )
        )

    return summaries


async def auto_detect_provider_health(
    timeout: int = 10,
) -> Dict[str, str]:
    """Quick health check across all providers.

    Tests the first active key per provider. Returns {provider: status}.
    """
    keys = list_keys()
    results: Dict[str, str] = {}

    for provider in PROVIDER_CONFIG:
        provider_keys = [
            k for k in keys if k.provider == provider and k.is_active
        ]
        if not provider_keys:
            # No keys configured — try without auth to detect network
            results[provider] = "unconfigured"
            continue

        # Test the first active key
        key = provider_keys[0]
        result = await test_key(key.id, timeout=timeout)
        if result:
            results[provider] = result.status
        else:
            results[provider] = "unknown"

    return results


# ═══════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════


def _update_key_status(
    key_id: str, status: str, error_message: Optional[str] = None
) -> None:
    """Update the health status of a key in the store."""
    keys = _read_keys_db()
    for i, k in enumerate(keys):
        if k["id"] == key_id:
            keys[i]["last_status"] = status
            keys[i]["last_checked"] = datetime.now(timezone.utc).isoformat()
            keys[i]["error_message"] = error_message
            _write_keys_db(keys)
            return
