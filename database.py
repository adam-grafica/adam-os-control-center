import sqlite3
import os
from datetime import datetime, date, timedelta

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "dashboard.db")

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def dict_row(row):
    if row is None:
        return None
    return dict(row)

def dict_list(rows):
    return [dict(r) for r in rows]

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.executescript('''
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assigned_to TEXT DEFAULT 'Axon',
            status TEXT DEFAULT 'pending',
            mission_id INTEGER REFERENCES missions(id),
            priority TEXT DEFAULT 'medium',
            progress REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS revenue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            type TEXT DEFAULT 'actual',
            date DATE DEFAULT (date('now')),
            note TEXT DEFAULT ''
        );
        
        CREATE TABLE IF NOT EXISTS revenue_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            predicted_amount REAL DEFAULT 0,
            date DATE DEFAULT (date('now')),
            confidence REAL DEFAULT 0.5
        );
        
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT DEFAULT '',
            status TEXT DEFAULT 'success',
            details TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            responded INTEGER DEFAULT 0,
            session_id TEXT DEFAULT 'default',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            type TEXT DEFAULT '',
            description TEXT DEFAULT '',
            progress REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # Seed data if empty
    existing_tasks = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if existing_tasks == 0:
        _seed_data(c)
    
    conn.commit()
    conn.close()

def _seed_data(c):
    now = datetime.utcnow()
    
    # Missions
    missions = [
        ("ADAM OS Dashboard v2", "Evolucionar el dashboard a Command Center vivo con chat, tareas y datos reales", "active"),
        ("Sistema Captación AdamGráfica", "Pipeline de captación de clientes automatizado", "active"),
        ("Carolina Marina Branding", "Branding completo + presencia digital para Carolina Marina", "active"),
        ("Academia San Fernando", "Plataforma educativa con Gen Asesor Coach", "planning"),
    ]
    for name, desc, status in missions:
        c.execute("INSERT INTO missions (name, description, status) VALUES (?,?,?)", (name, desc, status))
    
    # Tasks for first mission
    dashboard_tasks = [
        ("Construir WebSocket para datos real-time", "Implementar WebSocket en backend para sistema, chat y agentes", "Axon", "in_progress", 1, "critical", 70),
        ("Diseñar Task Board interactivo", "Kanban de tareas con drag-status y asignación a agentes", "Axon", "in_progress", 1, "high", 50),
        ("Implementar Revenue Dynamics", "Gráfico de ingresos reales vs predicción basada en tareas", "Axon", "pending", 1, "high", 0),
        ("Construir Agent Topology", "Visualización de comunicación entre agentes en tiempo real desde logs", "Axon", "pending", 1, "high", 0),
        ("Integrar Chat Dashboard-Axon", "Chat en vivo conectado a Hermes/Axon para trabajar desde el dashboard", "Axon", "pending", 1, "critical", 0),
        ("Conectar proyectos reales desde Notion", "Sincronizar proyectos activos desde Notion API", "Axon", "pending", 1, "medium", 0),
        ("Deploy a CapRover", "Desplegar todo el sistema actualizado", "Axon", "pending", 1, "high", 0),
    ]
    for title, desc, assigned, status, mission_id, priority, progress in dashboard_tasks:
        c.execute(
            "INSERT INTO tasks (title, description, assigned_to, status, mission_id, priority, progress) VALUES (?,?,?,?,?,?,?)",
            (title, desc, assigned, status, mission_id, priority, progress)
        )
    
    # Agent logs (realistic seeds)
    agent_logs = [
        ("Axon", "deploy", "adam-os-control-center", "success", "v2 deployed to CapRover"),
        ("Hermes", "route", "Axon → Frontend Build", "success", "Routing frontend build task to Axon"),
        ("Gen Pro", "generate", "prompt_template_revenue", "success", "Generated revenue prediction template"),
        ("CODE ARCHITECT", "analyze", "architecture_review", "success", "Reviewed WebSocket architecture"),
        ("Axon", "task_assign", "Construir WebSocket", "success", "Assigned to self"),
        ("THE RETOUCH WIZARD", "idle", "", "idle", "Awaiting visual assets"),
        ("CMO Agent", "idle", "", "idle", "Awaiting marketing tasks"),
        ("HERALD", "monitor", "deployment_queue", "success", "No pending deployments"),
    ]
    for agent, action, target, status, details in agent_logs:
        c.execute(
            "INSERT INTO agent_logs (agent_name, action, target, status, details) VALUES (?,?,?,?,?)",
            (agent, action, target, status, details)
        )
    
    # Revenue services
    services = ["Branding", "Desarrollo Web", "Redes Sociales", "Consultoría IA", "Sistema MIDI"]
    for svc in services:
        c.execute("INSERT INTO revenue (service_name, amount, type, date) VALUES (?,0,'actual',date('now'))", (svc,))
        # Forecast for next 30 days
        for d in range(30):
            future = (datetime.utcnow() + timedelta(days=d)).strftime("%Y-%m-%d")
            base_pred = 0
            # Simple prediction: more tasks done = more revenue
            if svc == "Branding":
                base_pred = 50000 + d * 3000  # Growing pipeline
            elif svc == "Desarrollo Web":
                base_pred = 35000 + d * 2000
            elif svc == "Consultoría IA":
                base_pred = 25000 + d * 4000  # Fastest growing
            else:
                base_pred = 15000 + d * 1000
            c.execute(
                "INSERT INTO revenue_forecast (service_name, predicted_amount, date, confidence) VALUES (?,?,?,?)",
                (svc, base_pred * (0.8 + 0.4 * (d / 30)), future, 0.3 + 0.6 * (d / 30))
            )
    
    # Projects
    projects = [
        ("ADAM OS Control Center", "active", "Infraestructura Interna", "Dashboard vivo de control de mando con chat, tareas y agentes", 65),
        ("Carolina Marina Branding", "active", "Branding", "Identidad visual completa + presencia digital", 30),
        ("Academia San Fernando", "active", "Plataforma IA", "Plataforma educativa con Gen Asesor Coach", 40),
        ("Sistema Captación AdamGráfica", "planning", "Automatización", "Pipeline de captación de leads automatizado con IA", 10),
        ("MIDI AI Ecosystem", "planning", "I+D", "Ecosistema de agentes MIDI con inteligencia artificial", 5),
    ]
    for name, status, typ, desc, progress in projects:
        c.execute(
            "INSERT INTO projects (name, status, type, description, progress) VALUES (?,?,?,?,?)",
            (name, status, typ, desc, progress)
        )
    
    # Welcome chat message
    c.execute(
        "INSERT INTO chat_messages (sender, message, session_id) VALUES (?,?,?)",
        ("Axon", "¡Bienvenido al ADAM OS Command Center, Natch! 🚀 Estoy aquí. ¿Qué vamos a conquistar hoy?", "default")
    )

def get_tasks(status=None, mission_id=None):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM tasks"
    params = []
    conditions = []
    if status:
        conditions.append("status = ?")
        params.append(status)
    if mission_id:
        conditions.append("mission_id = ?")
        params.append(mission_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY priority DESC, created_at DESC"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return dict_list(rows)

def create_task(title, description="", assigned_to="Axon", mission_id=None, priority="medium"):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title, description, assigned_to, mission_id, priority) VALUES (?,?,?,?,?)",
        (title, description, assigned_to, mission_id, priority)
    )
    task_id = c.lastrowid
    conn.commit()
    task = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    
    # Log the action
    log_agent_action("Axon", "task_create", f"Task #{task_id}: {title[:50]}")
    
    return dict_row(task)

def update_task(task_id, **kwargs):
    allowed = {"title", "description", "assigned_to", "status", "priority", "progress", "mission_id"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return None
    updates["updated_at"] = datetime.utcnow().isoformat()
    
    conn = get_db()
    c = conn.cursor()
    set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
    params = list(updates.values()) + [task_id]
    c.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", params)
    conn.commit()
    task = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    
    if "status" in updates:
        log_agent_action("Axon", "task_status", f"Task #{task_id} → {updates['status']}")
    
    return dict_row(task)

def delete_task(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def get_missions():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM missions ORDER BY created_at DESC").fetchall()
    # Count tasks per mission
    missions = dict_list(rows)
    for m in missions:
        counts = c.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks WHERE mission_id=? GROUP BY status",
            (m["id"],)
        ).fetchall()
        m["task_counts"] = {r["status"]: r["cnt"] for r in counts}
    conn.close()
    return missions

def create_mission(name, description=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO missions (name, description) VALUES (?,?)", (name, description))
    mid = c.lastrowid
    conn.commit()
    mission = c.execute("SELECT * FROM missions WHERE id=?", (mid,)).fetchone()
    conn.close()
    return dict_row(mission)

def get_revenue():
    conn = get_db()
    c = conn.cursor()
    actual = dict_list(c.execute(
        "SELECT service_name, SUM(amount) as total FROM revenue WHERE type='actual' GROUP BY service_name"
    ).fetchall())
    forecast = dict_list(c.execute(
        "SELECT service_name, SUM(predicted_amount) as total, AVG(confidence) as avg_confidence FROM revenue_forecast WHERE date >= date('now') GROUP BY service_name"
    ).fetchall())
    # Get daily forecast for charts
    daily = dict_list(c.execute(
        "SELECT date, SUM(predicted_amount) as total FROM revenue_forecast WHERE date >= date('now') GROUP BY date ORDER BY date LIMIT 30"
    ).fetchall())
    conn.close()
    return {"actual": actual, "forecast": forecast, "daily_forecast": daily}

def add_revenue(service_name, amount, note=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO revenue (service_name, amount, type, note) VALUES (?,?,'actual',?)",
              (service_name, amount, note))
    conn.commit()
    conn.close()

def get_agent_logs(limit=50):
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return dict_list(rows)

def log_agent_action(agent, action, target="", status="success", details=""):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO agent_logs (agent_name, action, target, status, details) VALUES (?,?,?,?,?)",
        (agent, action, target, status, details)
    )
    conn.commit()
    conn.close()

def get_chat_messages(session_id="default", since_id=0):
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM chat_messages WHERE session_id=? AND id>? ORDER BY timestamp ASC",
        (session_id, since_id)
    ).fetchall()
    conn.close()
    return dict_list(rows)

def add_chat_message(sender, message, session_id="default"):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO chat_messages (sender, message, session_id) VALUES (?,?,?)",
        (sender, message, session_id)
    )
    mid = c.lastrowid
    conn.commit()
    msg = c.execute("SELECT * FROM chat_messages WHERE id=?", (mid,)).fetchone()
    conn.close()
    
    # If user sent a message, log it
    if sender != "Axon":
        log_agent_action("Natch", "chat_message", message[:80])
    
    return dict_row(msg)

def get_projects():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return dict_list(rows)

def get_pending_chats():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute(
        "SELECT * FROM chat_messages WHERE sender != 'Axon' AND responded=0 ORDER BY timestamp ASC"
    ).fetchall()
    conn.close()
    return dict_list(rows)

def mark_chat_responded(msg_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE chat_messages SET responded=1 WHERE id=?", (msg_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized successfully!")
    print(f"   Path: {DB_PATH}")
    print(f"   Tasks: {len(get_tasks())}")
    print(f"   Missions: {len(get_missions())}")
    print(f"   Agent Logs: {len(get_agent_logs())}")
    print(f"   Chat Messages: {len(get_chat_messages())}")
