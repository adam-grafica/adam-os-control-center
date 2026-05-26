"""
ADAM OS Command Center — Database v3.1
=======================================
Refleja ESTRICTAMENTE la estructura de carpetas real del sistema:
  adam-os-system/
  ├── 1-root-axon [AXON]
  ├── 2-teams [HERMES]
  │   ├── adam-grafica/ → 8 departamentos
  │   └── midisoft/ → 10 departamentos
"""

import sqlite3, os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "dashboard.db")
SYSTEM_ROOT = "/home/adamcloud/adam-os-system"

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def dict_row(row):
    return None if row is None else dict(row)

def dict_list(rows):
    return [dict(r) for r in rows]

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT '',
            level INTEGER DEFAULT 0,
            parent_id INTEGER REFERENCES agents(id),
            dir_path TEXT DEFAULT '',
            color TEXT DEFAULT '#00f0ff',
            status TEXT DEFAULT 'active'
        );
        
        CREATE TABLE IF NOT EXISTS business_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT DEFAULT '',
            dir_name TEXT DEFAULT '',      -- nombre de la carpeta real
            dir_path TEXT DEFAULT '',      -- ruta completa del directorio
            agent_id INTEGER REFERENCES agents(id),
            parent_id INTEGER REFERENCES business_units(id),
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#ffd700',
            status TEXT DEFAULT 'active'
        );
        
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT '',
            department_id INTEGER REFERENCES business_units(id),
            status TEXT DEFAULT 'active'
        );
        
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assigned_to TEXT DEFAULT 'AXON',
            department_id INTEGER REFERENCES business_units(id),
            employee_id INTEGER REFERENCES employees(id),
            status TEXT DEFAULT 'pending',
            mission TEXT DEFAULT '',
            priority TEXT DEFAULT 'medium',
            progress REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            session_id TEXT DEFAULT 'default',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    c.execute("SELECT COUNT(*) FROM agents")
    if c.fetchone()[0] == 0:
        _seed_all(c)
    
    conn.commit()
    conn.close()

def _seed_all(c):
    # ===== AGENTES =====
    agents = [
        (1, "AXON",   "Agente Supremo / CEO",             0, None, "/home/adamcloud/adam-os-system/1-root-axon", "#00f0ff"),
        (2, "HERMES", "Brazo Derecho Articulado",          1, 1,    "/home/adamcloud/adam-os-system/2-teams",      "#ff00e5"),
    ]
    for id_, name, role, level, parent, dpath, color in agents:
        c.execute("INSERT OR REPLACE INTO agents (id,name,role,level,parent_id,dir_path,color) VALUES (?,?,?,?,?,?,?)",
                  (id_, name, role, level, parent, dpath, color))

    # ===== BUSINESS UNITS (carpetas reales) =====
    # ADAM GRÁFICA = carpeta adam-grafica/
    # MIDI SOFT = carpeta midisoft/
    units = [
        # Business units
        (1,  "ADAM GRÁFICA", "ADAM G.", "adam-grafica", "adam-grafica", 2, None,
         "Agencia boutique de branding, diseño, marketing y desarrollo", "#ffd700"),
        (2,  "MIDI SOFT",    "MIDI S.",  "midisoft",      "midisoft",     2, None,
         "Laboratorio de software, producto e infraestructura",       "#4488ff"),
        
        # ADAM GRÁFICA → Departamentos (parent_id=1)
        (10, "direction-ops-delivery",   "Delivery",   "direction-ops-delivery",   "adam-grafica", 2, 1, "", "#ff9944"),
        (11, "strategy-growth",          "Strategy",   "strategy-growth",          "adam-grafica", 2, 1, "", "#ffbb00"),
        (12, "creative-production",      "Creative",   "creative-production",      "adam-grafica", 2, 1, "", "#ff66aa"),
        (13, "automation-ai",            "AutoAI",     "automation-ai",            "adam-grafica", 2, 1, "", "#aa44ff"),
        (14, "accounts-client-success",  "Accounts",   "accounts-client-success",  "adam-grafica", 2, 1, "", "#44ddcc"),
        (15, "sales-business-dev",       "Sales",      "sales-business-dev",       "adam-grafica", 2, 1, "", "#44bb88"),
        (16, "finance-admin-legal",      "Finance",    "finance-admin-legal",      "adam-grafica", 2, 1, "", "#88cc44"),
        (17, "talent-culture-learning",  "Talent",     "talent-culture-learning",  "adam-grafica", 2, 1, "", "#cc6688"),
        
        # MIDI SOFT → Departamentos (parent_id=2)
        (20, "product",                 "Product",    "product",                 "midisoft", 2, 2, "", "#4488ff"),
        (21, "engineering",             "Engineering", "engineering",            "midisoft", 2, 2, "", "#44ccff"),
        (22, "ux-ui-research",          "UX/UI",      "ux-ui-research",          "midisoft", 2, 2, "", "#8866ff"),
        (23, "qa-quality",              "QA",         "qa-quality",              "midisoft", 2, 2, "", "#66dd88"),
        (24, "devops-infra-security",   "DevOps",     "devops-infra-security",   "midisoft", 2, 2, "", "#ff6644"),
        (25, "automation-ai-data",      "AI Data",    "automation-ai-data",      "midisoft", 2, 2, "", "#aa88ff"),
        (26, "delivery-program-ops",    "Delivery",   "delivery-program-ops",    "midisoft", 2, 2, "", "#44aa88"),
        (27, "stakeholder-success",     "Stakeholder", "stakeholder-success",    "midisoft", 2, 2, "", "#88cc66"),
        (28, "business-revenue-partnerships", "Revenue","business-revenue-partnerships","midisoft",2,2,"","#ffaa44"),
        (29, "people-ops-finance",      "People",     "people-ops-finance",      "midisoft", 2, 2, "", "#cc88aa"),
    ]
    for id_, name, short, dname, dpath, agent_id, parent, desc, color in units:
        full_path = f"/home/adamcloud/adam-os-system/2-teams/{dpath}"
        c.execute(
            "INSERT OR REPLACE INTO business_units (id,name,short_name,dir_name,dir_path,agent_id,parent_id,description,color) VALUES (?,?,?,?,?,?,?,?,?)",
            (id_, name, short, dname, full_path, agent_id, parent, desc, color)
        )

    # ===== EMPLEADOS =====
    employees = [
        # ADAM GRÁFICA → creative-production
        ("Gen Pro",           "Generador de Contenido PRO",    12),
        ("THE RETOUCH WIZARD","Retoque y Post-producción",    12),
        # ADAM GRÁFICA → strategy-growth
        ("CMO Agent",         "Estrategia de Marketing",       11),
        # ADAM GRÁFICA → direction-ops-delivery
        # ADAM GRÁFICA → accounts-client-success
        # ADAM GRÁFICA → automation-ai
        # ADAM GRÁFICA → sales-business-dev
        # ADAM GRÁFICA → finance-admin-legal
        # ADAM GRÁFICA → talent-culture-learning
        
        # MIDI SOFT → engineering
        ("CODE ARCHITECT",    "Arquitecto de Código",          21),
        ("MIDI Developer",    "Desarrollo MIDI + IA",          21),
        ("Composer AI",       "Composición Musical IA",        21),
        ("Sound Engineer",    "Ingeniero de Sonido",           21),
        # MIDI SOFT → devops-infra-security
        ("HERALD",            "Monitor de Infraestructura",    24),
        # MIDI SOFT → product
        # MIDI SOFT → ux-ui-research
        # MIDI SOFT → qa-quality
        # MIDI SOFT → automation-ai-data
        # MIDI SOFT → delivery-program-ops
        # MIDI SOFT → stakeholder-success
        # MIDI SOFT → business-revenue-partnerships
        # MIDI SOFT → people-ops-finance
    ]
    for name, role, dept in employees:
        c.execute("INSERT INTO employees (name,role,department_id) VALUES (?,?,?)", (name, role, dept))

    # ===== TAREAS =====
    tasks = [
        ("ARMAR ESTRUCTURA ADAM OS EN COMMAND CENTER", "Reflejar las carpetas reales adam-grafica/ y midisoft/ en el dashboard, con sus 8 y 10 departamentos respectivamente", "AXON", None, None, "in_progress", "v3.1", "critical", 80),
        ("ASIGNAR EMPLEADOS A DEPARTAMENTOS VACÍOS", "Varios departamentos de ADAM GRÁFICA y MIDI SOFT no tienen empleados aún. Definir quién va dónde.", "AXON", None, None, "pending", "v3.1", "high", 0),
        ("CREAR DEPARTAMENTOS FALTANTES SI ES NECESARIO", "Verificar si la estructura actual de carpetas en adam-os-system/2-teams/ cubre todas las necesidades", "HERMES", None, None, "pending", "v3.1", "medium", 0),
    ]
    for title, desc, assigned, dept_id, emp_id, status, mission, priority, progress in tasks:
        c.execute(
            "INSERT INTO tasks (title,description,assigned_to,department_id,employee_id,status,mission,priority,progress) VALUES (?,?,?,?,?,?,?,?,?)",
            (title, desc, assigned, dept_id, emp_id, status, mission, priority, progress)
        )

    # ===== LOGS =====
    logs = [
        ("AXON",   "system_start", "v3.1 - estructura real",             "success", "Command Center ahora refleja las carpetas exactas del sistema"),
        ("HERMES", "route", "2-teams/adam-grafica + midisoft",           "success", "Enrutando tareas a los 18 departamentos reales"),
        ("Gen Pro","idle",   "",                                          "idle",    "Esperando tarea creativa en creative-production/"),
        ("CODE ARCHITECT","idle","",                                      "idle",    "Esperando tarea de desarrollo en midisoft/engineering/"),
    ]
    for agent, action, target, status, details in logs:
        c.execute("INSERT INTO agent_logs (agent_name,action,target,status,details) VALUES (?,?,?,?,?)",
                  (agent, action, target, status, details))

    # ===== CHAT =====
    c.execute("INSERT INTO chat_messages (sender,message,session_id) VALUES (?,?,?)",
              ("AXON", "🖥️ ADAM OS v3.1 — el Command Center ahora refleja las carpetas reales del sistema. Cada departamento del dashboard tiene su directorio real en adam-os-system/. ¿Qué tal se ve?", "default"))

# ===== QUERIES =====

def get_agents():
    conn = get_db()
    rows = conn.execute("SELECT * FROM agents ORDER BY level, id").fetchall()
    conn.close()
    return dict_list(rows)

def get_business_units(parent_id=None, agent_id=None):
    conn = get_db()
    c = conn.cursor()
    conditions = []
    params = []
    if parent_id is not None:
        conditions.append("parent_id = ?")
        params.append(parent_id)
    if agent_id is not None:
        conditions.append("agent_id = ?")
        params.append(agent_id)
    query = "SELECT * FROM business_units"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return dict_list(rows)

def get_employees(department_id=None):
    conn = get_db()
    c = conn.cursor()
    if department_id:
        rows = c.execute("SELECT * FROM employees WHERE department_id=? ORDER BY name", (department_id,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM employees ORDER BY department_id, name").fetchall()
    conn.close()
    return dict_list(rows)

def get_full_hierarchy():
    """Refleja EXACTAMENTE la estructura de carpetas del sistema."""
    conn = get_db()
    c = conn.cursor()
    
    agents = dict_list(c.execute("SELECT * FROM agents ORDER BY level, id").fetchall())
    agent_map = {a["id"]: a for a in agents}
    for a in agents:
        a["children_agents"] = []
    for a in agents:
        if a["parent_id"] and a["parent_id"] in agent_map:
            agent_map[a["parent_id"]]["children_agents"].append(a)
    
    # Business units (toplevel: without parent)
    for agent in agents:
        top_units = dict_list(c.execute(
            "SELECT * FROM business_units WHERE agent_id=? AND parent_id IS NULL ORDER BY id",
            (agent["id"],)
        ).fetchall())
        for tu in top_units:
            # Get departments under this business unit
            depts = dict_list(c.execute(
                "SELECT * FROM business_units WHERE parent_id=? ORDER BY id", (tu["id"],)
            ).fetchall())
            for d in depts:
                d["employees"] = dict_list(c.execute(
                    "SELECT * FROM employees WHERE department_id=?", (d["id"],)
                ).fetchall())
            tu["departments"] = depts
            tu["employees"] = dict_list(c.execute(
                "SELECT * FROM employees WHERE department_id=?", (tu["id"],)
            ).fetchall())
        agent["business_units"] = top_units
    
    conn.close()
    return agents

def get_tasks(status=None):
    conn = get_db()
    c = conn.cursor()
    query = """SELECT t.*, bu.name as department_name, bu.dir_path as department_path
               FROM tasks t LEFT JOIN business_units bu ON t.department_id=bu.id"""
    params = []
    if status:
        query += " WHERE t.status = ?"
        params.append(status)
    query += " ORDER BY CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, t.created_at DESC"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return dict_list(rows)

def create_task(title, description="", assigned_to="AXON", department_id=None, employee_id=None, mission="", priority="medium"):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (title,description,assigned_to,department_id,employee_id,mission,priority) VALUES (?,?,?,?,?,?,?)",
        (title, description, assigned_to, department_id, employee_id, mission, priority)
    )
    task_id = c.lastrowid
    conn.commit()
    task = c.execute("SELECT t.*, bu.name as department_name, bu.dir_path as department_path FROM tasks t LEFT JOIN business_units bu ON t.department_id=bu.id WHERE t.id=?", (task_id,)).fetchone()
    conn.close()
    log_agent_action("AXON", "task_create", f"Task #{task_id}: {title[:60]}")
    return dict_row(task)

def update_task(task_id, **kwargs):
    allowed = {"title", "description", "assigned_to", "status", "priority", "progress", "mission", "department_id", "employee_id"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return None
    updates["updated_at"] = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
    params = list(updates.values()) + [task_id]
    c.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", params)
    conn.commit()
    task = c.execute("SELECT t.*, bu.name as department_name, bu.dir_path as department_path FROM tasks t LEFT JOIN business_units bu ON t.department_id=bu.id WHERE t.id=?", (task_id,)).fetchone()
    conn.close()
    if "status" in updates:
        log_agent_action("AXON", "task_status", f"Task #{task_id} → {updates['status']}")
    return dict_row(task)

def delete_task(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def get_agent_logs(limit=30):
    conn = get_db()
    rows = conn.execute("SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return dict_list(rows)

def log_agent_action(agent, action, target="", status="success", details=""):
    conn = get_db()
    conn.execute("INSERT INTO agent_logs (agent_name,action,target,status,details) VALUES (?,?,?,?,?)",
                 (agent, action, target, status, details))
    conn.commit()
    conn.close()

def get_chat_messages(session_id="default", since_id=0):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE session_id=? AND id>? ORDER BY timestamp ASC",
        (session_id, since_id)
    ).fetchall()
    conn.close()
    return dict_list(rows)

def add_chat_message(sender, message, session_id="default"):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO chat_messages (sender,message,session_id) VALUES (?,?,?)",
              (sender, message, session_id))
    mid = c.lastrowid
    conn.commit()
    msg = c.execute("SELECT * FROM chat_messages WHERE id=?", (mid,)).fetchone()
    conn.close()
    if sender != "AXON":
        log_agent_action(sender, "chat_message", message[:80])
    return dict_row(msg)

if __name__ == "__main__":
    db_path = DB_PATH
    if os.path.exists(db_path):
        bak = db_path + ".bak3"
        os.rename(db_path, bak)
        print(f"📦 DB anterior respaldada → {bak}")
    init_db()
    print("✅ ADAM OS v3.1 Database — estructura real de carpetas")
    hier = get_full_hierarchy()
    for a in hier:
        print(f"\n{a['name']} ({a['role']}) — 📂 {a.get('dir_path','')}")
        for bu in a.get("business_units", []):
            print(f"  ├── 📁 {bu['short_name']} ({bu['dir_name']}/)")
            for d in bu.get("departments", []):
                emps = ", ".join(e["name"] for e in d.get("employees", []))
                print(f"  │   ├── 📂 {d['dir_name']}/ {'→ ' + emps if emps else ''}")
