"""ADAM OS Control Center — Infrastructure API Endpoints

Provides real-time server metrics via the InfraReader service.
All endpoints return JSON with live data from psutil.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from app.services.infra_reader import infra_reader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/infra", tags=["Infrastructure"])


@router.get("/snapshot")
async def infra_snapshot() -> Dict[str, Any]:
    """Return a complete snapshot of server infrastructure.

    Includes CPU, memory, disk, network, uptime, and top processes.
    """
    return infra_reader.get_full_infra_snapshot()


@router.get("/cpu")
async def cpu_metrics() -> Dict[str, Any]:
    """Return CPU metrics: usage percent, load average, core count."""
    return infra_reader.get_cpu()


@router.get("/memory")
async def memory_metrics() -> Dict[str, Any]:
    """Return RAM metrics: total, available, used, percent."""
    return infra_reader.get_memory()


@router.get("/disk")
async def disk_metrics() -> List[Dict[str, Any]]:
    """Return disk usage info for all mounted partitions."""
    return infra_reader.get_disk()


@router.get("/network")
async def network_metrics() -> Dict[str, Any]:
    """Return network I/O counters and per-interface stats."""
    return infra_reader.get_network()


@router.get("/processes")
async def top_processes() -> List[Dict[str, Any]]:
    """Return top 10 processes sorted by memory usage."""
    return infra_reader.get_top_processes(10)


@router.post("/memory/free")
async def free_ram() -> Dict[str, Any]:
    """Attempt to free RAM by clearing kernel caches.

    Requires root / CAP_SYS_ADMIN. Returns success status and
    freed bytes.
    """
    return infra_reader.free_ram()
