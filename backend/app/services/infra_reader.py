"""ADAM OS Control Center — Infra Reader Service

Reads live server metrics using psutil. Falls back gracefully if psutil
is not available or if a specific metric fails to read.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Optional psutil import ──

try:
    import psutil as _psutil

    HAS_PSUTIL = True
except ImportError:
    _psutil = None
    HAS_PSUTIL = False
    logger.warning("psutil not installed — infra metrics will return empty data")


class InfraReader:
    """Read server infrastructure metrics via psutil.

    Every public method is wrapped in try/except — if psutil is missing
    or a metric fails, an empty/zero structure is returned instead of
    raising an error.
    """

    def __init__(self):
        self._boot_time: float | None = None
        self._boot_time_ts: float = 0

    # ── Public API ──

    def get_full_infra_snapshot(self) -> Dict[str, Any]:
        """Return a complete snapshot of server infrastructure.

        Returns:
            dict with keys: cpu, memory, disk, network, uptime, processes, ts
        """
        snapshot = {
            "ts": time.time(),
            "cpu": self.get_cpu(),
            "memory": self.get_memory(),
            "disk": self.get_disk(),
            "network": self.get_network(),
            "uptime": self.get_uptime(),
            "processes": self.get_top_processes(10),
        }
        return snapshot

    def get_cpu(self) -> Dict[str, Any]:
        """Return CPU metrics: percent, load average, core count."""
        result: Dict[str, Any] = {
            "percent": 0.0,
            "per_cpu": [],
            "load_avg": [0.0, 0.0, 0.0],
            "cores": 0,
            "status": "unavailable",
        }
        if not HAS_PSUTIL:
            return result
        try:
            result["percent"] = _psutil.cpu_percent(interval=0.1)
            result["per_cpu"] = _psutil.cpu_percent(interval=0.1, percpu=True)
            result["load_avg"] = [round(x, 2) for x in _psutil.getloadavg()]
            result["cores"] = _psutil.cpu_count(logical=True)
            result["status"] = "ok"
        except Exception as exc:
            logger.warning("Failed to read CPU metrics: %s", exc)
            result["status"] = f"error: {exc}"
        return result

    def get_memory(self) -> Dict[str, Any]:
        """Return memory metrics: total, available, percent, used, free."""
        result: Dict[str, Any] = {
            "total": 0,
            "available": 0,
            "used": 0,
            "free": 0,
            "percent": 0.0,
            "status": "unavailable",
        }
        if not HAS_PSUTIL:
            return result
        try:
            mem = _psutil.virtual_memory()
            result["total"] = mem.total
            result["available"] = mem.available
            result["used"] = mem.used
            result["free"] = mem.free
            result["percent"] = mem.percent
            result["status"] = "ok" if mem.percent < 90 else "critical"
        except Exception as exc:
            logger.warning("Failed to read memory metrics: %s", exc)
            result["status"] = f"error: {exc}"
        return result

    def get_disk(self) -> List[Dict[str, Any]]:
        """Return disk usage information for all mounted partitions."""
        if not HAS_PSUTIL:
            return []
        partitions: List[Dict[str, Any]] = []
        try:
            for part in _psutil.disk_partitions():
                # Skip pseudo-filesystems
                if part.fstype in ("", "squashfs", "tmpfs", "devtmpfs", "proc", "sysfs", "cgroup", "cgroup2", "devpts", "fusectl", "overlay"):
                    continue
                try:
                    usage = _psutil.disk_usage(part.mountpoint)
                    partitions.append(
                        {
                            "device": part.device,
                            "mountpoint": part.mountpoint,
                            "fstype": part.fstype,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent,
                        }
                    )
                except PermissionError:
                    continue
        except Exception as exc:
            logger.warning("Failed to read disk metrics: %s", exc)
        return partitions

    def get_network(self) -> Dict[str, Any]:
        """Return network I/O counters."""
        result: Dict[str, Any] = {
            "bytes_sent": 0,
            "bytes_recv": 0,
            "packets_sent": 0,
            "packets_recv": 0,
            "errors_in": 0,
            "errors_out": 0,
            "interfaces": {},
            "status": "unavailable",
        }
        if not HAS_PSUTIL:
            return result
        try:
            net = _psutil.net_io_counters()
            result["bytes_sent"] = net.bytes_sent
            result["bytes_recv"] = net.bytes_recv
            result["packets_sent"] = net.packets_sent
            result["packets_recv"] = net.packets_recv
            result["errors_in"] = net.errin
            result["errors_out"] = net.errout

            # Per-interface stats
            interfaces = {}
            for iface, stats in _psutil.net_io_counters(pernic=True).items():
                interfaces[iface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                }
            result["interfaces"] = interfaces
            result["status"] = "ok"
        except Exception as exc:
            logger.warning("Failed to read network metrics: %s", exc)
            result["status"] = f"error: {exc}"
        return result

    def get_uptime(self) -> Dict[str, Any]:
        """Return system uptime information."""
        result: Dict[str, Any] = {
            "uptime_seconds": 0,
            "boot_time": None,
            "status": "unavailable",
        }
        if not HAS_PSUTIL:
            return result
        try:
            boot = _psutil.boot_time()
            result["boot_time"] = boot
            result["uptime_seconds"] = time.time() - boot
            result["status"] = "ok"
        except Exception as exc:
            logger.warning("Failed to read uptime: %s", exc)
            result["status"] = f"error: {exc}"
        return result

    def get_top_processes(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return top N processes sorted by memory usage."""
        if not HAS_PSUTIL:
            return []
        processes: List[Dict[str, Any]] = []
        try:
            for proc in _psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "status"]
            ):
                try:
                    pinfo = proc.info
                    processes.append(
                        {
                            "pid": pinfo["pid"],
                            "name": pinfo["name"],
                            "cpu_percent": pinfo["cpu_percent"] or 0.0,
                            "memory_percent": pinfo["memory_percent"] or 0.0,
                            "status": pinfo["status"],
                        }
                    )
                except (OSError, _psutil.NoSuchProcess):
                    continue
        except Exception as exc:
            logger.warning("Failed to list processes: %s", exc)
            return []

        processes.sort(key=lambda p: p["memory_percent"], reverse=True)
        return processes[:n]

    def free_ram(self) -> Dict[str, Any]:
        """Attempt to free RAM by clearing kernel caches.

        Only works when running with appropriate capabilities (CAP_SYS_ADMIN
        or root). Returns a result dict indicating success or failure.

        Guardrails:
          - Only runs on Linux
          - Only clears pagecache, dentries, and inodes (level 3)
          - Does NOT touch swap
        """
        result: Dict[str, Any] = {
            "success": False,
            "freed_bytes": 0,
            "before": {},
            "after": {},
            "message": "",
        }
        if not HAS_PSUTIL:
            result["message"] = "psutil not available"
            return result

        if os.name != "posix" or not os.uname().sysname == "Linux":
            result["message"] = "Only supported on Linux"
            return result

        try:
            # Record before
            mem_before = _psutil.virtual_memory()
            result["before"] = {
                "available": mem_before.available,
                "used": mem_before.used,
                "percent": mem_before.percent,
            }

            # Sync disks to flush buffers
            os.system("sync")

            # Drop caches (level 3 = pagecache + dentries + inodes)
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")

            # Read after
            mem_after = _psutil.virtual_memory()
            result["after"] = {
                "available": mem_after.available,
                "used": mem_after.used,
                "percent": mem_after.percent,
            }
            result["freed_bytes"] = mem_after.available - mem_before.available
            result["success"] = True
            result["message"] = (
                f"Freed {result['freed_bytes'] / 1024 / 1024:.1f} MB "
                f"({result['freed_bytes']:,} bytes)"
            )
        except PermissionError:
            result["message"] = (
                "Permission denied: need CAP_SYS_ADMIN or root to drop caches"
            )
        except Exception as exc:
            result["message"] = f"Error freeing RAM: {exc}"
            logger.warning("free_ram failed: %s", exc)

        return result


# ── Module-level singleton ──

infra_reader = InfraReader()
