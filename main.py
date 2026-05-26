"""ADAM OS Command Center — API v3.1 — Estructura real de carpetas"""

import logging, time, os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from scanner import scan as fs_scan, read_file as fs_read, write_file as fs_write

_DB = "/home/adamcloud/adam-os-dashboard/data/dashboard.db"

from database import (
    init_db, get_agents, get_business_units, get_employees, get_full_hierarchy,
    get_tasks, create_task, update_task, delete_task,
    get_agent_logs, log_agent_action,
    get_chat_messages, add_chat_message,
)

START_TIME = time.time()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="ADAM OS Command Center", version="3.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    init_db()
    logging.info("ADAM OS v3.1 ready — real directory structure")

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    assigned_to: str = "AXON"
    department_id: Optional[int] = None
    employee_id: Optional[int] = None
    priority: str = "medium"
    mission: str = ""

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    progress: Optional[float] = None
    mission: Optional[str] = None
    department_id: Optional[int] = None
    employee_id: Optional[int] = None

class ChatMessage(BaseModel):
    sender: str = "Natch"
    message: str
    session_id: str = "default"

class FileWrite(BaseModel):
    path: str
    content: str

# ===== HIERARCHY =====
@app.get("/api/hierarchy")
async def hierarchy():
    return get_full_hierarchy()

@app.get("/api/agents")
async def agents_list():
    return get_agents()

@app.get("/api/departments")
async def departments_list(parent_id: Optional[int] = None, agent_id: Optional[int] = None):
    return get_business_units(parent_id=parent_id, agent_id=agent_id)

@app.get("/api/employees")
async def employees_list(department_id: Optional[int] = None):
    return get_employees(department_id)

# ===== TASKS =====
@app.get("/api/tasks")
async def tasks_list(status: Optional[str] = None):
    return get_tasks(status)

@app.post("/api/tasks")
async def new_task(task: TaskCreate):
    return create_task(
        title=task.title, description=task.description,
        assigned_to=task.assigned_to,
        department_id=task.department_id, employee_id=task.employee_id,
        mission=task.mission, priority=task.priority,
    )

@app.put("/api/tasks/{task_id}")
async def update_task_endpoint(task_id: int, update: TaskUpdate):
    return update_task(task_id, **update.dict(exclude_none=True))

@app.delete("/api/tasks/{task_id}")
async def delete_task_endpoint(task_id: int):
    delete_task(task_id)
    return {"status": "deleted"}

# ===== LOGS =====
@app.get("/api/agent-logs")
async def agent_logs(limit: int = 30):
    return get_agent_logs(limit)

@app.post("/api/agent-logs")
async def new_log(agent: str, action: str, target: str = "", status: str = "success", details: str = ""):
    log_agent_action(agent, action, target, status, details)
    return {"status": "logged"}

# ===== CHAT =====
@app.get("/api/chat")
async def chat_messages(session_id: str = "default", since_id: int = 0):
    return get_chat_messages(session_id, since_id)

@app.post("/api/chat")
async def new_chat_message(msg: ChatMessage):
    return add_chat_message(msg.sender, msg.message, msg.session_id)

# ===== FILESYSTEM SCAN (LIVE) =====
@app.get("/api/scan")
async def scan_fs():
    """Scan the real filesystem and return live data."""
    return fs_scan()

# ===== FILE EDITOR =====
@app.get("/api/fs/read")
async def file_read(path: str):
    """Read a file by its relative path from adam-os-system/"""
    data = fs_read(path)
    if data is None:
        return {"error": f"File not found: {path}"}
    return data

@app.post("/api/fs/write")
async def file_write(data: FileWrite):
    """Write content to a file by its relative path."""
    result = fs_write(data.path, data.content)
    if "error" in result:
        return {"error": result["error"]}
    return result

# ===== HEALTH =====
@app.get("/api/health")
async def health():
    return {"status":"online","version":"3.1.0","uptime_seconds":int(time.time()-START_TIME),"timestamp":datetime.utcnow().isoformat()}

# ===== STATIC FILES =====
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
