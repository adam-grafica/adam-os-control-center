"""ADAM OS Dashboard — Pydantic v2 Models / Schemas

All request/response models used by the REST API and SSE streams.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Error Response ──


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    detail: str = Field(..., description="Human-readable error message")
    code: Optional[str] = Field(None, description="Machine-readable error code")


# ── State Snapshot ──


class StateSnapshot(BaseModel):
    """A single row from the state_snapshots table."""

    id: str = Field(..., description="UUID of the snapshot")
    ts: Optional[datetime] = Field(None, description="Timestamp of the snapshot")
    mode: str = Field("normal", description="Organism mode: normal/light/safe/critical")
    health: int = Field(100, ge=0, le=100, description="Health score 0-100")
    tokens_estimated: int = Field(0, description="Estimated token usage")
    context_depth: int = Field(0, description="Current context depth")
    active_tasks: int = Field(0, description="Number of active tasks")
    last_error: Optional[str] = Field(None, description="Most recent error message")
    last_error_ts: Optional[datetime] = Field(None, description="Timestamp of last error")
    error_count: int = Field(0, description="Accumulated error count")


# ── Event Log ──


class EventLog(BaseModel):
    """A single row from the events_log table."""

    id: str = Field(..., description="UUID of the event")
    ts: Optional[datetime] = Field(None, description="Timestamp of the event")
    source: str = Field(..., description="Source organ/system that generated the event")
    event_type: str = Field(
        ...,
        description="Event type: request/alert/state_change/memory_update/training/policy_check/action_request/anomaly",
    )
    severity: str = Field("low", description="Severity: low/medium/high/critical")
    payload: Optional[str] = Field(None, description="JSON string payload")
    result: Optional[str] = Field(None, description="Result of the event action")
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )


# ── Threat Memory ──


class ThreatMemory(BaseModel):
    """A single row from the threat_memory table."""

    id: str = Field(..., description="UUID of the threat record")
    threat_type: str = Field(
        ...,
        description="Threat type: rate_limit/timeout_repeated/tool_error_repeated/inconsistent_output/reasoning_loop/prompt_injection/ambiguous_input/degraded_provider",
    )
    first_seen: Optional[datetime] = Field(None, description="When the threat was first detected")
    last_seen: Optional[datetime] = Field(None, description="When the threat was last observed")
    occurrences: int = Field(1, description="Number of occurrences")
    status: str = Field(
        "monitoring", description="Status: resolved/monitoring/critical"
    )
    mitigation: Optional[str] = Field(None, description="Applied mitigation strategy")


# ── Organ Health ──


class OrganHealth(BaseModel):
    """Health status for a single organ."""

    status: str = Field("healthy", description="healthy/warning/critical")
    health_score: int = Field(100, ge=0, le=100, description="Health score 0-100")
    last_active: Optional[datetime] = Field(None, description="When the organ last reported")
    metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Organ-specific metrics"
    )


# ── Organ Snapshot (detailed view of one organ) ──


class OrganSnapshot(BaseModel):
    """Full detail for a single organ, including recent events."""

    name: str = Field(..., description="Organ name")
    status: str = Field("healthy", description="healthy/warning/critical")
    health_score: int = Field(100, ge=0, le=100, description="Health score 0-100")
    metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Organ-specific metrics"
    )
    recent_events: List[EventLog] = Field(
        default_factory=list, description="Most recent events from this organ"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "heart",
                "status": "healthy",
                "health_score": 95,
                "metrics": {"decisions_last_hour": 12, "avg_latency_ms": 45},
                "recent_events": [],
            }
        }
    }


# ── Timeline Point (for chart data) ──


class TimelinePoint(BaseModel):
    """A single data point for timeline/trend charts."""

    ts: str = Field(..., description="ISO format timestamp")
    health: int = Field(..., ge=0, le=100, description="Health value")
    mode: Optional[str] = Field(None, description="Organism mode at this point")
    tokens: Optional[int] = Field(None, description="Token count at this point")
    tasks: Optional[int] = Field(None, description="Active tasks at this point")


# ── Dashboard Snapshot (composite response) ──


class DashboardSnapshot(BaseModel):
    """Complete dashboard snapshot combining all data sources."""

    organism_health: int = Field(..., ge=0, le=100, description="Overall health score")
    organism_mood: str = Field(
        "stable", description="Derived mood: thriving/stable/stressed/critical"
    )
    current_mode: str = Field(
        "normal", description="Current organism mode: normal/light/safe/critical"
    )
    active_threats: int = Field(0, ge=0, description="Count of active threats")
    organs: Dict[str, OrganHealth] = Field(
        ..., description="Health status for each of the 7 organs"
    )
    recent_events: List[EventLog] = Field(
        default_factory=list, description="Most recent system events"
    )
    active_threats_list: List[ThreatMemory] = Field(
        default_factory=list, description="List of active threats with details"
    )
    snapshot_ts: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Timestamp when this snapshot was generated",
    )


# ── Organ definitions ──

ORGAN_NAMES = [
    "heart",
    "autonomic",
    "immune",
    "proprioception",
    "reflexes",
    "dreams",
    "growth",
]

ORGAN_DESCRIPTIONS = {
    "heart": "Central decision-making organ — rules on allow/deny/defer",
    "autonomic": "Background housekeeping — scheduling, compaction, audits",
    "immune": "Threat detection and mitigation — monitors for anomalies",
    "proprioception": "Self-awareness and state sensing — context depth, memory usage",
    "reflexes": "Fast pattern-match responses — trained and hard-coded reflexes",
    "dreams": "Offline consolidation — memory compaction and insight extraction",
    "growth": "Learning and adaptation — skill acquisition and policy updates",
}

# ── API Key Management ──


class ApiKeyEntry(BaseModel):
    """A single API key entry for the hub."""

    id: str = Field(..., description="Unique identifier")
    provider: str = Field(
        ...,
        description="Provider: opencode-zen, nvidia, mistral",
    )
    tier: str = Field(
        ...,
        description="Tier: main, fallback, round-robin",
    )
    key_alias: str = Field(
        ..., description="Friendly name/alias for this key"
    )
    key_env_var: str = Field(
        ..., description="Environment variable name"
    )
    key_preview: str = Field(
        ..., description="Last 4 characters of the key (masked)"
    )
    is_active: bool = Field(
        True, description="Whether this key is currently active"
    )
    position: int = Field(
        0, description="Order/priority in the pool (0 = first)"
    )
    last_checked: Optional[str] = Field(
        None, description="ISO datetime of last health check"
    )
    last_status: str = Field(
        "unknown",
        description="Health status: unknown/healthy/degraded/error",
    )
    error_message: Optional[str] = Field(
        None, description="Last error message if status is error"
    )
    model: Optional[str] = Field(
        None,
        description="Associated model name for this key (e.g., deepseek-v4-flash-free)",
    )
    base_url: Optional[str] = Field(
        None, description="API base URL for this provider"
    )


class ApiKeyCreate(BaseModel):
    """Payload for creating a new API key entry."""

    provider: str = Field(
        ...,
        description="Provider: opencode-zen, nvidia, mistral",
    )
    tier: str = Field(
        ...,
        description="Tier: main, fallback, round-robin",
    )
    key_alias: str = Field(
        ..., description="Friendly name/alias"
    )
    key_value: str = Field(
        ..., description="The actual API key value"
    )
    key_env_var: Optional[str] = Field(
        None,
        description="Optional explicit env var name (auto-generated if omitted)",
    )
    position: Optional[int] = Field(
        None, description="Optional position override"
    )
    model: Optional[str] = Field(None, description="Model name")
    base_url: Optional[str] = Field(None, description="API base URL")


class ApiKeyUpdate(BaseModel):
    """Payload for updating an existing API key."""

    key_alias: Optional[str] = Field(
        None, description="New friendly name"
    )
    key_value: Optional[str] = Field(
        None, description="New key value"
    )
    is_active: Optional[bool] = Field(
        None, description="Whether the key is active"
    )
    position: Optional[int] = Field(
        None, description="New position in pool"
    )
    model: Optional[str] = Field(None, description="Update model name")
    base_url: Optional[str] = Field(None, description="Update base URL")


class ProviderHealthSummary(BaseModel):
    """Health summary for a single provider."""

    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Default model for this provider")
    total_keys: int = Field(0, description="Total keys configured")
    active_keys: int = Field(0, description="Active keys")
    healthy_keys: int = Field(0, description="Healthy keys")
    degraded_keys: int = Field(0, description="Degraded keys")
    error_keys: int = Field(0, description="Error keys")
    overall_status: str = Field(
        "unknown", description="healthy/degraded/error/unknown"
    )
    tier: str = Field(..., description="main/fallback/round-robin")


class ApiKeyTestResult(BaseModel):
    """Result of testing a single API key."""

    id: str = Field(..., description="Key ID")
    key_alias: str = Field(..., description="Key alias")
    provider: str = Field(..., description="Provider name")
    status: str = Field(
        ..., description="Result: healthy/degraded/error"
    )
    latency_ms: Optional[int] = Field(
        None, description="Response time in ms"
    )
    message: str = Field(..., description="Human-readable result")
    http_status: Optional[int] = Field(
        None, description="HTTP status code if applicable"
    )
