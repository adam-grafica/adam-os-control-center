"""
ADAM OS Dashboard — FastAPI Backend
=====================================
Endpoints:
  GET /                         → static/index.html
  GET /api/health               → status, hermes, version, uptime
  GET /api/system               → CPU, memory, disk (psutil)
  GET /api/notion/tasks         → Notion DB query (tasks)
  GET /api/notion/projects      → Notion page (projects)
  GET /api/notion/clients       → Notion page (clients)
  GET /api/config               → static config data
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional

import psutil
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

app = FastAPI(title="ADAM OS Dashboard API", version="1.0.0")

# CORS — allow all origins for dashboard use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Globals & start time
# ---------------------------------------------------------------------------

START_TIME = time.time()
logger = logging.getLogger("adam-os-dashboard")

# ---------------------------------------------------------------------------
# Static files — serve /app/static/index.html on GET /
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Serve /app/static/ as static files (images, css, etc.)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serve the single-page dashboard frontend."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse(
        {"error": "Frontend not built yet — index.html missing from /app/static/"},
        status_code=404,
    )


# ---------------------------------------------------------------------------
# Notion helper
# ---------------------------------------------------------------------------

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_VERSION = "2025-09-03"
NOTION_BASE = "https://api.notion.com/v1"

# Task DB    1ba5f8c7-cf88-80f1-9547-000bde777ec3
# Projects   2885f8c7-cf88-80b1-99a5-fd7eeb12abf8
# Clients    2885f8c7-cf88-80aa-8ee4-eec921b03a0e
NOTION_TASKS_DB = "1ba5f8c7-cf88-80f1-9547-000bde777ec3"
NOTION_PROJECTS_PAGE = "2885f8c7-cf88-80b1-99a5-fd7eeb12abf8"
NOTION_CLIENTS_PAGE = "2885f8c7-cf88-80aa-8ee4-eec921b03a0e"

# Simple TTL cache (seconds)
_cache: dict = {}


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"] < 60):
        return entry["data"]
    return None


def _cache_set(key: str, data):
    _cache[key] = {"ts": time.time(), "data": data}


def _notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def _notion_query_database(database_id: str) -> list:
    """Query a Notion database and return the results array."""
    cache_key = f"db:{database_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if not NOTION_API_KEY:
        logger.warning("NOTION_API_KEY not set")
        return []

    url = f"{NOTION_BASE}/data_sources/{database_id}/query"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=_notion_headers(), json={})

    if resp.status_code != 200:
        logger.error("Notion DB query failed: %s %s", resp.status_code, resp.text)
        return []

    data = resp.json()
    results = data.get("results", [])
    _cache_set(cache_key, results)
    return results


async def _notion_get_page(page_id: str) -> Optional[dict]:
    """Retrieve a Notion page."""
    cache_key = f"page:{page_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if not NOTION_API_KEY:
        logger.warning("NOTION_API_KEY not set")
        return None

    url = f"{NOTION_BASE}/pages/{page_id}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=_notion_headers())

    if resp.status_code != 200:
        logger.error("Notion page get failed: %s %s", resp.status_code, resp.text)
        return None

    data = resp.json()
    _cache_set(cache_key, data)
    return data


async def _notion_get_blocks(block_id: str) -> list:
    """Retrieve children blocks of a page/block."""
    cache_key = f"blocks:{block_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if not NOTION_API_KEY:
        return []

    url = f"{NOTION_BASE}/blocks/{block_id}/children"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=_notion_headers())

    if resp.status_code != 200:
        logger.error("Notion blocks get failed: %s %s", resp.status_code, resp.text)
        return []

    data = resp.json()
    results = data.get("results", [])
    _cache_set(cache_key, results)
    return results


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    uptime_s = int(time.time() - START_TIME)
    return {
        "status": "online",
        "hermes": "online",
        "version": "1.0.0",
        "uptime_seconds": uptime_s,
    }


@app.get("/api/system")
async def system():
    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_cores = psutil.cpu_count()

    mem = psutil.virtual_memory()
    total_gb = round(mem.total / (1024 ** 3), 2)
    used_gb = round(mem.used / (1024 ** 3), 2)

    disk = psutil.disk_usage("/")
    disk_total = round(disk.total / (1024 ** 3), 2)
    disk_used = round(disk.used / (1024 ** 3), 2)

    return {
        "cpu": {"percent": cpu_percent, "cores": cpu_cores},
        "memory": {"total_gb": total_gb, "used_gb": used_gb, "percent": mem.percent},
        "disk": {"total_gb": disk_total, "used_gb": disk_used, "percent": disk.percent},
    }


# ----- Notion: Tareas -------------------------------------------------------


def _parse_task_status(properties: dict) -> str:
    """Extract task status from Notion DB row properties."""
    for key in ("Estado", "Status", "status", "estado", "State"):
        prop = properties.get(key, {})
        if prop.get("type") == "status":
            status_obj = prop.get("status", {})
            if status_obj:
                return status_obj.get("name", "Sin estado")
        if prop.get("type") == "select":
            sel = prop.get("select")
            if sel:
                return sel.get("name", "Sin estado")
    return "Sin estado"


def _parse_task_name(properties: dict) -> str:
    """Extract task title from Notion DB row properties."""
    for key in ("Tarea", "Name", "name", "Nombre", "nombre", "Title", "title"):
        prop = properties.get(key, {})
        if prop.get("type") == "title":
            title_arr = prop.get("title", [])
            if title_arr:
                return "".join(t.get("plain_text", "") for t in title_arr)
    return "Sin nombre"


def _parse_task_progress(properties: dict):
    """Extract progress (0-100) if available."""
    for key in ("Progress", "progress", "Progreso", "progreso", "%", "Done"):
        prop = properties.get(key, {})
        if prop.get("type") == "number":
            return prop.get("number")
        if prop.get("type") == "rich_text":
            rt = prop.get("rich_text", [])
            if rt:
                txt = "".join(t.get("plain_text", "") for t in rt)
                try:
                    return int(txt.replace("%", ""))
                except (ValueError, TypeError):
                    return None
    return None


@app.get("/api/notion/tasks")
async def notion_tasks():
    items = await _notion_query_database(NOTION_TASKS_DB)

    parsed = []
    for row in items:
        props = row.get("properties", {})
        parsed.append({
            "name": _parse_task_name(props),
            "status": _parse_task_status(props),
            "progress": _parse_task_progress(props),
        })

    total = len(parsed)
    por_hacer = sum(1 for t in parsed if t["status"].lower() in ("por hacer", "to do", "pendiente", "backlog"))
    en_proceso = sum(1 for t in parsed if t["status"].lower() in ("en proceso", "in progress", "doing", "progreso"))
    completado = sum(1 for t in parsed if t["status"].lower() in ("completado", "done", "completo", "terminado", "hecho"))

    return {
        "total": total,
        "por_hacer": por_hacer,
        "en_proceso": en_proceso,
        "completado": completado,
        "items": parsed,
    }


# ----- Notion: Proyectos ----------------------------------------------------


def _extract_text_from_blocks(blocks: list) -> str:
    """Simple extraction of paragraph text from Notion blocks."""
    texts = []
    for block in blocks:
        block_type = block.get("type", "")
        content = block.get(block_type, {})
        rich_text = content.get("rich_text", [])
        for rt in rich_text:
            texts.append(rt.get("plain_text", ""))
    return "\n".join(texts)


@app.get("/api/notion/projects")
async def notion_projects():
    # Get the page properties and child blocks
    page = await _notion_get_page(NOTION_PROJECTS_PAGE)
    blocks = await _notion_get_blocks(NOTION_PROJECTS_PAGE)

    # Try to extract structured data from page properties
    projects = []
    active_count = 0

    if page:
        props = page.get("properties", {})
        # Some pages might have a relation to a DB
        # Try to find project-like properties
        for key, val in props.items():
            if val.get("type") == "relation":
                # Could be a relation to projects DB
                pass

    # Parse blocks to extract project info (name, status, type)
    # This is heuristic — depends on how blocks are structured
    current_project = {}
    for block in blocks:
        btype = block.get("type", "")
        content = block.get(btype, {})
        rich_text = content.get("rich_text", [])
        text = "".join(t.get("plain_text", "") for t in rich_text).strip()

        if not text:
            continue

        # Heuristic: H2/H3 headings might be project names
        if btype in ("heading_2", "heading_3"):
            if current_project:
                projects.append(current_project)
            current_project = {"name": text, "status": "En Proceso", "type": ""}
            active_count += 1
        elif btype == "paragraph" and current_project:
            if "status" in text.lower() or "proceso" in text.lower() or "completado" in text.lower():
                current_project["status"] = text.split(":")[-1].strip() if ":" in text else text
            elif current_project.get("type") == "":
                current_project["type"] = text

    if current_project:
        projects.append(current_project)

    # If blocks didn't yield structured data, try querying child database
    if not projects:
        # Maybe the page contains a linked database — query child pages
        child_db_id = None
        for block in blocks:
            if block.get("type") == "child_database":
                child_db_id = block.get("id")
                break

        if child_db_id:
            items = await _notion_query_database(child_db_id)
            for row in items:
                props = row.get("properties", {})
                name = _parse_task_name(props)
                status = _parse_task_status(props)
                projects.append({
                    "name": name,
                    "status": status,
                    "type": "",
                })
                if status.lower() in ("en proceso", "in progress", "doing"):
                    active_count += 1

    return {
        "active": active_count,
        "projects": projects,
    }


# ----- Notion: Clientes -----------------------------------------------------


@app.get("/api/notion/clients")
async def notion_clients():
    page = await _notion_get_page(NOTION_CLIENTS_PAGE)
    blocks = await _notion_get_blocks(NOTION_CLIENTS_PAGE)

    total = 0
    active = 0
    prospect = 0
    inactive = 0

    # Try to extract from page properties
    if page:
        props = page.get("properties", {})
        for key, val in props.items():
            if val.get("type") == "number":
                name_lower = key.lower()
                if "total" in name_lower:
                    total = val.get("number", 0)
                elif "active" in name_lower or "activo" in name_lower:
                    active = val.get("number", 0)
                elif "prospect" in name_lower:
                    prospect = val.get("number", 0)
                elif "inactive" in name_lower or "inactivo" in name_lower:
                    inactive = val.get("number", 0)

    # If no properties with numbers, try parsing blocks for linked DB
    if total == 0 and active == 0 and prospect == 0 and inactive == 0:
        child_db_id = None
        for block in blocks:
            if block.get("type") == "child_database":
                child_db_id = block.get("id")
                break

        if child_db_id:
            items = await _notion_query_database(child_db_id)
            for row in items:
                props = row.get("properties", {})
                status = _parse_task_status(props)
                total += 1
                s_lower = status.lower()
                if s_lower in ("active", "activo"):
                    active += 1
                elif s_lower in ("prospect", "prospecto", "potencial"):
                    prospect += 1
                elif s_lower in ("inactive", "inactivo", "archived"):
                    inactive += 1

    return {
        "total": total,
        "active": active,
        "prospect": prospect,
        "inactive": inactive,
    }


# ----- Config (static) ------------------------------------------------------


CONFIG_DATA = {
    "stacks": {
        "adamgrafica": {
            "name": "AdamGráfica",
            "type": "Agencia de Marketing",
            "services": ["Branding", "Redes Sociales", "Diseño Gráfico", "Marketing Digital"],
            "description": "Agencia 95% IA - Valparaíso, Chile",
            "since": 2018,
        },
        "midisoft": {
            "name": "Midisoft",
            "type": "Agencia de Desarrollo",
            "services": ["Tauri Apps", "TypeScript/Rust", "Sistemas IA", "MIDI AI Ecosystem"],
            "description": "Agentic Development Environment",
            "since": 2024,
        },
    },
    "agents": [
        {"name": "Hermes", "role": "Meta-Agent Router", "status": "online"},
        {"name": "Axon", "role": "Executive Orchestrator", "status": "online"},
        {"name": "Gen Pro", "role": "Sistema de Prompts", "status": "online"},
        {"name": "CODE ARCHITECT", "role": "Arquitecto de Software", "status": "online"},
        {"name": "THE RETOUCH WIZARD", "role": "Director Visual", "status": "standby"},
        {"name": "HERALD", "role": "Custodio Dev (Perplexity)", "status": "standby"},
        {"name": "CMO Agent", "role": "Marketing (Perplexity)", "status": "standby"},
        {"name": "Gen Asesor Coach", "role": "Notion + Proyectos", "status": "online"},
    ],
    "routers": [
        {"name": "Router Core", "mode": "Activo", "description": "Rutas por modo: Ejecutor/Desarrollador/Pesado"},
        {"name": "MCP Gateway", "mode": "Activo", "description": "Contexto compartido entre agentes"},
        {"name": "Kanban Orchestrator", "mode": "Activo", "description": "Delegación y planificación"},
    ],
}


@app.get("/api/config")
async def config():
    return CONFIG_DATA


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
