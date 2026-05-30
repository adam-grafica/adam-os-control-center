"""Pytest configuration for ADAM OS Control Center tests.

Sets up environment variables and shared fixtures.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure backend is importable
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

# Set environment before any app module imports
os.environ.setdefault("STATE_DB_PATH", "/home/adamcloud/adam-os-system/state/state.db")
os.environ.setdefault("ADAM_OS_ROOT", "/home/adamcloud/adam-os-system")
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("FILES_WRITE_ENABLED", "true")
