"""
ADAM OS Command Center — FastAPI Backend v2
=============================================
Endpoints:
  GET /                         → static/index.html
  GET /api/health               → status, hermes, version, uptime
  GET /api/system               → CPU, memory, disk (psutil)
  GET /api/notion/tasks         → Notion DB query (tasks)
  GET /api/notion/projects      → Notion page (projects)
  GET /api/notion/clients       → Notion page (clients)
  GET /api/config               → static config data
  WS  /ws/chat                  → bidirectional real-time chat
  WS  /ws/system                → real-time system stats (emits every 2s)
  GET /api/tasks                → list tasks (filter: ?status=&mission_id=)
  POST /api/tasks               → create task
  PUT  /api/tasks/{id}          → update task
  DELETE /api/tasks/{id}        → delete task
  GET /api/missions             → list missions
  POST /api/missions            → create mission
  GET /api/revenue              → actual vs forecast
  POST /api/revenue             → add revenue entry
  GET /api/agents/logs          → agent communication logs
  GET /api/chat/messages        → chat history
  POST /api/chat/messages       → send chat message (REST)
  GET /api/projects             → active projects
  GET /api/chat/pending         → pending unanswered messages
  POST /api/chat/respond/{id}   → mark message as responded
"""

import os
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional

import psutil
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

START_TIME = time.time()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Notion config
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

NOTION_TASKS_DB = "1ba5f8c7-cf88-80f1-9547-000bde777ec3"
NOTION_PROJECTS_PAGE = "1b85f8c7-cf88-804c-8a6b-cfa82e81e110"
NOTION_CLIENTS_PAGE = "1b85f8c7-cf88-8014-af33-ea3e9fa54823"

app = FastAPI(title="ADAM OS Command Center", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

from database import (
    init_db,
    get_tasks, create_task, update_task, delete_task,
    get_missions, create_mission,
    get_revenue, add_revenue,
    get_agent_logs, log_agent_action,
    get_chat_messages, add_chat_message,
    get_projects, get_pending_chats, mark_chat_responded,
    get_departments, get_employees, get_agent_hierarchy,
)

@app.on_event("startup")
async def startup():
    init_db()
    logging.info("Database initialized")

# ---------------------------------------------------------------------------
# WebSocket manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.chat_connections: list[WebSocket] = []
        self.system_connections: list[WebSocket] = []

    async def connect_chat(self, ws: WebSocket):
        await ws.accept()
        self.chat_connections.append(ws)

    def disconnect_chat(self, ws: WebSocket):
        if ws in self.chat_connections:
            self.chat_connections.remove(ws)

    async def connect_system(self, ws: WebSocket):
        await ws.accept()
        self.system_connections.append(ws)

    def disconnect_system(self, ws: WebSocket):
        if ws in self.system_connections:
            self.system_connections.remove(ws)

    async def broadcast_chat(self, message: dict):
        dead = []
        for ws in self.chat_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_chat(ws)

manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html not found"}, status_code=404)

# ---------------------------------------------------------------------------
# Health, System, Config
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "hermes": "online",
        "version": "2.1.0",
        "uptime_seconds": int(time.time() - START_TIME),
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/api/system")
async def system():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu_percent = psutil.cpu_percent(interval=0.1)
    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(),
            "load_avg": [round(x, 2) for x in psutil.getloadavg()],
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/api/config")
async def config():
    return {
        "stacks": {
            "adamgrafica": {
                "name": "AdamGráfica",
                "type": "Agencia de Marketing",
                "services": ["Branding", "Redes Sociales", "Diseño Gráfico", "Marketing Digital"],
                "active_projects": 1,
            },
            "midisoft": {
                "name": "Midisoft",
                "type": "Agencia de Desarrollo",
                "services": ["Tauri Apps", "TypeScript/Rust", "Sistemas IA", "MIDI AI Ecosystem"],
                "active_projects": 1,
            },
        },
        "agents": [
            {"name": "Axon", "role": "Executive Orchestrator", "status": "online"},
            {"name": "Hermes", "role": "Meta-Agent Router", "status": "online"},
            {"name": "Gen Pro", "role": "Sistema de Prompts", "status": "online"},
            {"name": "CODE ARCHITECT", "role": "Arquitecto de Software", "status": "online"},
            {"name": "THE RETOUCH WIZARD", "role": "Director Visual", "status": "standby"},
            {"name": "HERALD", "role": "Custodio Dev", "status": "standby"},
            {"name": "CMO Agent", "role": "Marketing", "status": "standby"},
            {"name": "Gen Asesor Coach", "role": "Notion + Proyectos", "status": "online"},
        ],
        "routers": [
            {"name": "Router Core", "role": "Orquestador decisiones 100% free"},
            {"name": "Router Expert", "role": "Tareas complejas vía modelos premium"},
            {"name": "Router Canales", "role": "Workflows de contenido multicanal"},
        ],
    }

# ---------------------------------------------------------------------------
# WebSocket: Real-time system stats (push every 2s)
# ---------------------------------------------------------------------------

@app.websocket("/ws/system")
async def websocket_system(ws: WebSocket):
    await manager.connect_system(ws)
    try:
        while True:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu = psutil.cpu_percent(interval=0.1)
            data = {
                "type": "system",
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {"percent": cpu, "cores": psutil.cpu_count()},
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "percent": mem.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": disk.percent,
                },
            }
            await ws.send_json(data)
            await asyncio.sleep(2)
            # Check if client sent a message (disconnect detection)
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                if msg == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect_system(ws)

# ---------------------------------------------------------------------------
# WebSocket: Chat (bidirectional)
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await manager.connect_chat(ws)
    try:
        # Send recent chat history
        history = get_chat_messages()
        await ws.send_json({"type": "history", "messages": history})

        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            action = msg.get("action", "send")
            
            if action == "send":
                sender = msg.get("sender", "Natch")
                message = msg.get("message", "")
                
                # Save to DB
                saved = add_chat_message(sender, message)
                
                # Broadcast to all connected clients
                await manager.broadcast_chat({
                    "type": "message",
                    "id": saved["id"],
                    "sender": sender,
                    "message": message,
                    "timestamp": saved["timestamp"],
                })
                
                # If from user, auto-generate a response placeholder
                if sender != "Axon":
                    log_agent_action("Natch", "chat_input", message[:60])
                    
            elif action == "typing":
                await manager.broadcast_chat({
                    "type": "typing",
                    "sender": msg.get("sender", "Natch"),
                })
                
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect_chat(ws)

# ---------------------------------------------------------------------------
# Tasks CRUD
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    assigned_to: str = "Axon"
    mission_id: Optional[int] = None
    priority: str = "medium"
    department_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    progress: Optional[float] = None
    mission_id: Optional[int] = None

@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None, mission_id: Optional[int] = None):
    return get_tasks(status=status, mission_id=mission_id)

@app.post("/api/tasks")
async def new_task(task: TaskCreate):
    result = create_task(
        title=task.title,
        description=task.description,
        assigned_to=task.assigned_to,
        mission_id=task.mission_id,
        priority=task.priority,
        department_id=task.department_id,
    )
    # Broadcast new task to chat clients
    await manager.broadcast_chat({
        "type": "system",
        "message": f"📋 Nueva tarea creada: **{task.title}** → {task.assigned_to}",
    })
    return result

@app.put("/api/tasks/{task_id}")
async def edit_task(task_id: int, task: TaskUpdate):
    updates = {k: v for k, v in task.dict().items() if v is not None}
    result = update_task(task_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if "status" in updates:
        await manager.broadcast_chat({
            "type": "system",
            "message": f"🔄 Tarea #{task_id} cambió a **{updates['status']}**: {result['title'][:50]}",
        })
    
    return result

@app.delete("/api/tasks/{task_id}")
async def remove_task(task_id: int):
    delete_task(task_id)
    return {"status": "deleted"}

# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

class MissionCreate(BaseModel):
    name: str
    description: str = ""

@app.get("/api/missions")
async def list_missions():
    return get_missions()

@app.post("/api/missions")
async def new_mission(mission: MissionCreate):
    return create_mission(mission.name, mission.description)

# ---------------------------------------------------------------------------
# Departments & Employees (hierarchy)
# ---------------------------------------------------------------------------

@app.get("/api/departments")
async def list_departments():
    return get_departments()

@app.get("/api/employees")
async def list_employees(department_id: Optional[int] = None):
    return get_employees(department_id=department_id)

@app.get("/api/hierarchy")
async def hierarchy():
    """Full agent → department → employee tree."""
    return get_agent_hierarchy()

# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------

class RevenueCreate(BaseModel):
    service_name: str
    amount: float
    note: str = ""

@app.get("/api/revenue")
async def revenue():
    return get_revenue()

@app.post("/api/revenue")
async def create_revenue(rev: RevenueCreate):
    add_revenue(rev.service_name, rev.amount, rev.note)
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Agent Logs
# ---------------------------------------------------------------------------

@app.get("/api/agents/logs")
async def agent_logs(limit: int = Query(50, ge=1, le=200)):
    return get_agent_logs(limit=limit)

@app.post("/api/agents/logs")
async def create_agent_log(data: dict):
    log_agent_action(
        data.get("agent_name", "unknown"),
        data.get("action", "unknown"),
        data.get("target", ""),
        data.get("status", "success"),
        data.get("details", ""),
    )
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Chat (REST fallback)
# ---------------------------------------------------------------------------

class ChatSend(BaseModel):
    sender: str = "Natch"
    message: str
    session_id: str = "default"

@app.get("/api/chat/messages")
async def chat_messages(since_id: int = 0, session_id: str = "default"):
    return get_chat_messages(session_id=session_id, since_id=since_id)

@app.post("/api/chat/messages")
async def send_chat_message(msg: ChatSend):
    saved = add_chat_message(msg.sender, msg.message, msg.session_id)
    # Broadcast via WebSocket
    await manager.broadcast_chat({
        "type": "message",
        "id": saved["id"],
        "sender": msg.sender,
        "message": msg.message,
        "timestamp": saved["timestamp"],
        "via": "rest",
    })
    return saved

@app.get("/api/chat/pending")
async def pending_chats():
    """Get unanswered user messages (for Axon to poll)"""
    return get_pending_chats()

@app.post("/api/chat/respond/{msg_id}")
async def respond_chat(msg_id: int):
    """Mark a chat message as responded"""
    mark_chat_responded(msg_id)
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/api/projects")
async def projects():
    return get_projects()

# ---------------------------------------------------------------------------
# Notion endpoints (unchanged)
# ---------------------------------------------------------------------------

async def _notion_query_database(database_id: str):
    if not NOTION_API_KEY:
        return {"error": "NOTION_API_KEY not configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{NOTION_BASE}/data_sources/{database_id}/query",
            headers={
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json={},
        )
        if resp.status_code != 200:
            return {"error": resp.text}
        data = resp.json()
        results = data.get("results", data.get("data", {}).get("results", []))
        parsed = []
        for item in results:
            props = item.get("properties", {})
            parsed.append({
                "id": item.get("id", ""),
                "name": _parse_prop_title(props),
                "status": _parse_prop_status(props),
                "progress": _parse_prop_number(props),
                "due_date": _parse_prop_date(props),
            })
        return {"total": len(parsed), "items": parsed}

def _parse_prop_title(props: dict) -> str:
    for key in ("Tarea", "Name", "Nombre", "name", "title"):
        prop = props.get(key)
        if prop is None:
            continue
        ptype = prop.get("type", "")
        if ptype == "title":
            titles = prop.get("title", [])
            if titles and isinstance(titles[0], dict):
                return titles[0].get("plain_text", "")
            if isinstance(titles, list) and titles:
                return str(titles[0])
        elif ptype == "rich_text":
            texts = prop.get("rich_text", [])
            if texts:
                return "".join(t.get("plain_text", "") for t in texts)
    return "Sin título"

def _parse_prop_status(props: dict) -> str:
    for key in ("Estado", "Status", "status", "estado"):
        prop = props.get(key)
        if prop is None:
            continue
        ptype = prop.get("type", "")
        if ptype == "status":
            st = prop.get("status", {})
            if st and isinstance(st, dict):
                return st.get("name", "Sin estado")
        elif ptype == "select":
            sel = prop.get("select", {})
            if sel and isinstance(sel, dict):
                return sel.get("name", "Sin estado")
    return "Por hacer"

def _parse_prop_number(props: dict) -> float | None:
    for key in ("Progreso", "Progress", "progress"):
        prop = props.get(key)
        if prop is None:
            continue
        if prop.get("type") == "number":
            val = prop.get("number")
            return float(val) if val is not None else None
    return None

def _parse_prop_date(props: dict) -> str | None:
    for key in ("Fecha límite", "Fecha", "Date", "date", "due_date"):
        prop = props.get(key)
        if prop is None:
            continue
        if prop.get("type") == "date":
            d = prop.get("date", {})
            if d and isinstance(d, dict):
                return d.get("start")
    return None

async def _notion_read_page(page_id: str):
    if not NOTION_API_KEY:
        return {"error": "NOTION_API_KEY not configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{NOTION_BASE}/data_sources/{page_id}",
            headers={
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": NOTION_VERSION,
            },
        )
        if resp.status_code != 200:
            return {"error": resp.text}
        data = resp.json()
        props = data.get("properties", {})
        parsed = []
        for key, prop in props.items():
            if prop.get("type") == "rich_text":
                texts = prop.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in texts)
                if text.strip():
                    parsed.append({"name": key, "value": text})
        return {"properties": parsed}

async def _notion_query_children(page_id: str):
    if not NOTION_API_KEY:
        return {"error": "NOTION_API_KEY not configured"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{NOTION_BASE}/blocks/{page_id}/children",
            headers={
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": NOTION_VERSION,
            },
        )
        if resp.status_code != 200:
            return {"error": resp.text}
        data = resp.json()
        results = data.get("results", [])
        parsed = []
        for block in results:
            btype = block.get("type", "")
            bdata = block.get(btype, {})
            if btype == "heading_2":
                texts = bdata.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in texts)
                parsed.append({"type": "heading", "text": text})
            elif btype in ("paragraph", "bulleted_list_item", "numbered_list_item"):
                texts = bdata.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in texts)
                if text.strip():
                    parsed.append({"type": "text", "text": text})
            elif btype == "to_do":
                texts = bdata.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in texts)
                checked = bdata.get("checked", False)
                if text.strip():
                    parsed.append({"type": "todo", "text": text, "checked": checked})
            elif btype == "child_database":
                parsed.append({"type": "database_ref", "title": bdata.get("title", "Sub-DB"), "id": block.get("id")})
        return {"items": parsed}

@app.get("/api/notion/tasks")
async def notion_tasks():
    return await _notion_query_database(NOTION_TASKS_DB)

@app.get("/api/notion/projects")
async def notion_projects():
    # Try reading the page + children
    page = await _notion_read_page(NOTION_PROJECTS_PAGE)
    children = await _notion_query_children(NOTION_PROJECTS_PAGE)
    return {"page": page, "children": children}

@app.get("/api/notion/clients")
async def notion_clients():
    page = await _notion_read_page(NOTION_CLIENTS_PAGE)
    children = await _notion_query_children(NOTION_CLIENTS_PAGE)
    return {"page": page, "children": children}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
