"""ADAM OS Dashboard — FastAPI Application Entry Point

Assembles the FastAPI app with middleware, routers, SSE streaming,
static file mounting, and debug endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sse_starlette.sse import EventSourceResponse

from app.api import health as health_router
from app.api import events as events_router
from app.api import organs as organs_router
from app.api import infra as infra_router
from app.api import agents as agents_router
from app.api import console as console_router
from app.api import files as files_router
from app.api import config as config_router
from app.api import apis as apis_router
from app.api import control as control_router
from app.api import pipeline as pipeline_router
from app.api import tokens as tokens_router
from app.api import keys as keys_router
from app.core.db import close_db, init_db, get_db
from app.core.pubsub import event_bus
from app.settings import settings
from app.services.snapshots import create_snapshot_service
from app.services.infra_reader import infra_reader
from app.services.log_streamer import log_streamer
from app.services.pipeline_service import get_pipeline

# ── Logging ──

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Lifespan ──


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize DB on startup, close on shutdown."""
    logger.info("Starting ADAM OS Dashboard API ...")
    await init_db()
    logger.info(
        "Connected to state database: %s", settings.STATE_DB_PATH
    )
    yield
    await close_db()
    logger.info("ADAM OS Dashboard API shut down.")


# ── Application ──

app = FastAPI(
    title="ADAM OS Dashboard API",
    description="REST API + SSE streaming for the ADAM OS living digital organism dashboard.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Auth Middleware ──


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication middleware.

    If AUTH_ENABLED=True, requires a valid Bearer token in the
    Authorization header for all routes except public exclusions.
    If API_TOKEN is empty, logs a WARNING but allows requests through
    (useful for development/debugging).

    Excluded routes (no auth required):
      - /api/health
      - /api/stream/*  (SSE endpoints)
      - /favicon.svg
      - /               (static frontend)
    """

    EXCLUDED_PATHS: tuple = (
        "/api/health",
        "/api/stream/",
        "/favicon.svg",
        "/",
    )

    async def dispatch(self, request: Request, call_next):
        # Skip auth if disabled or path is excluded
        if not settings.AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path
        if any(
            path == excluded or path.startswith(excluded)
            for excluded in self.EXCLUDED_PATHS
        ):
            return await call_next(request)

        # Validate Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or malformed Authorization header. Expected: Bearer <token>"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header is empty."},
            )

        if not settings.API_TOKEN:
            logger.warning(
                "API_TOKEN is not configured — allowing request from %s",
                request.client.host if request.client else "unknown",
            )
            return await call_next(request)

        if token != settings.API_TOKEN:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API token."},
            )

        return await call_next(request)


app.add_middleware(AuthMiddleware)

# ── Routers (all /api/... routes — registered first so they take priority) ──

app.include_router(health_router.router)
app.include_router(events_router.router)
app.include_router(organs_router.router)
app.include_router(infra_router.router)
app.include_router(agents_router.router)
app.include_router(console_router.router)
app.include_router(files_router.router)
app.include_router(config_router.router)
app.include_router(apis_router.router)
app.include_router(control_router.router)
app.include_router(pipeline_router.router)
app.include_router(tokens_router.router)
app.include_router(keys_router.router)


# ── SSE Streaming ──


@app.get("/api/stream/state")
async def stream_state(request: Request) -> EventSourceResponse:
    """SSE endpoint that streams state updates every SSE_HEARTBEAT seconds.

    Clients receive a new 'state_update' event each interval with the
    latest dashboard snapshot. Also listens for in-process broadcasts
    via the event bus.
    """

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        """Yield SSE events to the client."""
        db = await get_db()
        snapshot_service = create_snapshot_service(db)

        # Queue for receiving broadcast updates
        update_queue: asyncio.Queue = asyncio.Queue()

        def handle_broadcast(event_data: Dict[str, Any]) -> None:
            """Callback for in-process broadcasts via event bus."""
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(
                    lambda: update_queue.put_nowait(event_data)
                )
            except Exception:
                pass

        unsubscribe = event_bus.subscribe(handle_broadcast)

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for broadcast or timeout
                    event = await asyncio.wait_for(
                        update_queue.get(), timeout=settings.SSE_HEARTBEAT
                    )
                    yield {
                        "event": "state_update",
                        "data": json.dumps(event.get("data", event)),
                    }
                except asyncio.TimeoutError:
                    # No broadcast received — send heartbeat snapshot
                    try:
                        snapshot = await snapshot_service.get_current_snapshot()
                        yield {
                            "event": "state_update",
                            "data": snapshot.model_dump_json(),
                        }
                    except Exception as exc:
                        logger.warning(
                            "Failed to generate heartbeat snapshot: %s", exc
                        )
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps(
                                {"ts": asyncio.get_running_loop().time()}
                            ),
                        }
        finally:
            unsubscribe()

    return EventSourceResponse(event_generator())


# ── Master SSE Stream (combines organism + infra) ──


@app.get("/api/stream/master")
async def stream_master(request: Request) -> EventSourceResponse:
    """Master SSE endpoint that streams combined organism + infra state.

    Emits a 'combined_update' event every ~2 seconds containing:
      - organism: full dashboard snapshot (health, organs, events, threats)
      - infra: live server metrics (CPU, RAM, disk, network, processes)

    Also listens for in-process broadcasts via the event bus.
    """

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        db = await get_db()
        snapshot_service = create_snapshot_service(db)
        update_queue: asyncio.Queue = asyncio.Queue()

        def handle_broadcast(event_data: Dict[str, Any]) -> None:
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(
                    lambda: update_queue.put_nowait(event_data)
                )
            except Exception:
                pass

        unsubscribe = event_bus.subscribe(handle_broadcast)

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    # Wait for broadcast or timeout at 2s
                    event = await asyncio.wait_for(
                        update_queue.get(), timeout=2.0
                    )
                    yield {
                        "event": "combined_update",
                        "data": json.dumps(event.get("data", event)),
                    }
                except asyncio.TimeoutError:
                    # No broadcast — build combined snapshot
                    combined: Dict[str, Any] = {"ts": asyncio.get_running_loop().time()}

                    try:
                        snapshot = await snapshot_service.get_current_snapshot()
                        combined["organism"] = snapshot.model_dump(mode="json")
                    except Exception as exc:
                        logger.warning(
                            "Failed to generate organism snapshot: %s", exc
                        )
                        combined["organism"] = None

                    try:
                        combined["infra"] = infra_reader.get_full_infra_snapshot()
                    except Exception as exc:
                        logger.warning(
                            "Failed to generate infra snapshot: %s", exc
                        )
                        combined["infra"] = None

                    try:
                        pipeline_mgr = get_pipeline()
                        combined["pipeline"] = {
                            "projects": pipeline_mgr.get_all_projects(),
                            "overview": pipeline_mgr.get_pipeline_overview(),
                        }
                    except Exception as exc:
                        logger.warning(
                            "Failed to generate pipeline snapshot: %s", exc
                        )
                        combined["pipeline"] = None

                    yield {
                        "event": "combined_update",
                        "data": json.dumps(combined),
                    }
        finally:
            unsubscribe()

    return EventSourceResponse(event_generator())


# ── Debug / Info Endpoints ──


@app.get("/api/debug/config")
async def debug_config() -> Dict[str, Any]:
    """Return current configuration (sanitized). Only available if DEBUG=true."""
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Debug mode not enabled")

    return {
        "ADAM_OS_ROOT": settings.ADAM_OS_ROOT,
        "STATE_DB_PATH": settings.STATE_DB_PATH,
        "API_HOST": settings.API_HOST,
        "API_PORT": settings.API_PORT,
        "CORS_ORIGINS": settings.CORS_ORIGINS,
        "SNAPSHOT_CACHE_TTL": settings.SNAPSHOT_CACHE_TTL,
        "EVENTS_HISTORY_LIMIT": settings.EVENTS_HISTORY_LIMIT,
        "SSE_HEARTBEAT": settings.SSE_HEARTBEAT,
        "DEBUG": settings.DEBUG,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "frontend_build_exists": os.path.isdir(
            settings.frontend_build_path
        ),
    }


# ── Static Frontend ──
# Mount the Svelte SPA at "/" so it serves index.html on the root.
# API routes (/api/...) are registered above and take priority.
# If the build doesn't exist, fall through to the @app.get("/") info route.

_frontend_path = settings.frontend_build_path
_frontend_index = os.path.join(_frontend_path, "index.html")
if os.path.isfile(_frontend_index):
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/",
        StaticFiles(directory=_frontend_path, html=True),
        name="frontend",
    )
    logger.info("Frontend static files mounted from: %s", _frontend_path)
else:
    logger.info(
        "Frontend build not found at %s — API-only mode.", _frontend_path
    )


# ── Root Info Route (only served in API-only mode, when no frontend build) ──
# NOTE: This route never matches when the frontend static files are mounted,
# because FastAPI mounts take precedence for exact-path matches at the root.
# The mount above handles "/" when frontend exists.


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "service": "ADAM OS Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "health": "/api/health",
            "organism": "/api/health/organism",
            "state": "/api/health/state",
            "events": "/api/events",
            "events_by_type": "/api/events/type/{type}",
            "events_timeline": "/api/events/timeline",
            "organs": "/api/organs",
            "organ_detail": "/api/organs/{organ}",
            "organ_history": "/api/organs/{organ}/history",
            "sse_stream": "/api/stream/state",
            "sse_master": "/api/stream/master",
            "infra": "/api/infra/snapshot",
            "infra_cpu": "/api/infra/cpu",
            "infra_memory": "/api/infra/memory",
            "infra_disk": "/api/infra/disk",
            "infra_network": "/api/infra/network",
            "infra_processes": "/api/infra/processes",
            "agents_status": "/api/agents/status",
            "agents_tasks": "/api/agents/tasks",
            "agents_tools": "/api/agents/tools",
            "console_stream": "/api/console/stream",
            "console_logs": "/api/console/logs",
            "files_tree": "/api/files/tree",
            "files_read": "/api/files/read",
            "files_write": "/api/files/write",
            "files_search": "/api/files/search",
            "config": "/api/config",
            "providers": "/api/providers",
            "kanban": "/api/control/kanban",
            "kanban_create_task": "/api/control/task",
            "pipeline": "/api/pipeline",
            "pipeline_overview": "/api/pipeline/overview",
            "pipeline_project": "/api/pipeline/{project_id}",
            "pipeline_advance": "/api/pipeline/{project_id}/advance",
            "pipeline_progress": "/api/pipeline/{project_id}/progress",
        },
    }


# ── Exception Handlers ──


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> JSONResponse:
    """Handle 404 errors, preserving the original detail from route handlers."""
    detail = getattr(exc, "detail", None)
    if detail is None:
        detail = f"Endpoint not found: {request.url.path}"
    return JSONResponse(
        status_code=404,
        content={"detail": detail},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Internal server error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Entry Point ──

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
