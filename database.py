"""
ADAM OS Command Center — Database v3
=====================================
Jerarquía real: AGENTES (coordinadores) → UNIDADES DE NEGOCIO → DEPARTAMENTOS → EMPLEADOS
"""

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
    
    c.executescript("""
        -- AGENTES (coordinadores/gerentes)
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT '',
            level INTEGER DEFAULT 0,
            parent_id INTEGER REFERENCES agents(id),
            color TEXT DEFAULT '#00f0ff',
            status TEXT DEFAULT 'active'
        );
        
        -- UNIDADES ORGÁNICAS (business units, departments)
        CREATE TABLE IF NOT EXISTS org_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT DEFAULT '',
            unit_type TEXT NOT NULL DEFAULT 'department',
            parent_id INTEGER REFERENCES org_units(id),
            agent_id INTEGER REFERENCES agents(id),
            description TEXT DEFAULT '',
            color TEXT DEFAULT '#666680',
            status TEXT DEFAULT 'active'
        );
        
        -- EMPLEADOS (trabajadores que ejecutan)
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT DEFAULT '',
            department_id INTEGER REFERENCES org_units(id),
            stack TEXT DEFAULT '',
            avatar TEXT DEFAULT '',
            status TEXT DEFAULT 'active'
        );
        
        -- TAREAS
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            assigned_to TEXT DEFAULT 'AXON',
            assigned_to_type TEXT DEFAULT 'agent',
            department_id INTEGER REFERENCES org_units(id),
            employee_id INTEGER REFERENCES employees(id),
            status TEXT DEFAULT 'pending',
            mission TEXT DEFAULT '',
            priority TEXT DEFAULT 'medium',
            progress REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- LOG DE ACTIVIDAD
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT DEFAULT '',
            status TEXT DEFAULT 'success',
            details TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- CHAT
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            responded INTEGER DEFAULT 0,
            session_id TEXT DEFAULT 'default',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Seed data if empty
    existing_agents = c.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    if existing_agents == 0:
        _seed_all(c)
    
    conn.commit()
    conn.close()

def _seed_all(c):
    """Seed data with the correct ADAM OS System hierarchy."""
    now = datetime.utcnow()
    
    # ===== AGENTES (coordinadores/gerentes) =====
    agents_data = [
        (1, "AXON",     "Agente Supremo / CEO",           0, None,   "#00f0ff"),
        (2, "HERMES",   "Brazo Derecho Articulado",       1, 1,      "#ff00e5"),
        (3, "Axon-Life",   "Vida Personal: hábitos, salud", 2, 2,   "#00ff88"),
        (4, "Axon-Work",   "Trabajo: negocios y emprendimientos", 2, 2, "#ffd700"),
        (5, "Axon-Music",  "Arte Musical: producción y distribución", 2, 2, "#4488ff"),
    ]
    for id_, name, role, level, parent, color in agents_data:
        c.execute(
            "INSERT OR REPLACE INTO agents (id, name, role, level, parent_id, color) VALUES (?,?,?,?,?,?)",
            (id_, name, role, level, parent, color)
        )
    
    # ===== UNIDADES ORGÁNICAS =====
    units_data = [
        # Axon-Life sub-áreas
        (1, "Entrenamiento",      "Entren.", "department", None, 3, "Rutinas de entrenamiento físico", "#00ff88"),
        (2, "Mejora de Hábitos",  "Hábitos",  "department", None, 3, "Tracking y mejora de hábitos diarios", "#00cc66"),
        (3, "Rutinas de Ejercicios", "Ejerc.", "department", None, 3, "Rutinas específicas de ejercicios", "#009944"),
        (4, "Rutinas de Estiramientos", "Stretch", "department", None, 3, "Estiramientos y flexibilidad", "#006622"),
        
        # Axon-Work → ADAM GRÁFICA
        (5, "ADAM GRÁFICA", "ADAM G.", "business_unit", None, 4, "Agencia 95% IA - branding, web, redes", "#ffd700"),
        (6, "Creativo",       "Creativo", "department", 5, 4, "Diseño, contenido visual y branding", "#ffaa00"),
        (7, "Desarrollo",     "Dev",      "department", 5, 4, "Desarrollo web, apps y sistemas", "#ff8800"),
        (8, "Marketing",      "Mkt",      "department", 5, 4, "Estrategia de marketing y redes", "#ff6600"),
        (9, "Infraestructura","Infra",    "department", 5, 4, "Servidores, deploys y DevOps", "#ff4400"),
        
        # Axon-Work → MIDI SOFT
        (10, "MIDI SOFT",     "MIDI S.",  "business_unit", None, 4, "Software MIDI e inteligencia artificial", "#4488ff"),
        (11, "I+D",           "I+D",      "department", 10, 4, "Investigación y desarrollo MIDI+IA", "#3366cc"),
        (12, "Producción",    "Prod.",    "department", 10, 4, "Producción de software y audio", "#2244aa"),
        
        # Axon-Music sub-áreas (por definir estratégicamente)
        (13, "Distribución Musical", "Dist.", "department", None, 5, "Distribución en Spotify y plataformas", "#4488ff"),
        (14, "Branding Musical",     "Brand.", "department", None, 5, "Imagen de productor y presencia digital", "#2266cc"),
    ]
    for id_, name, short, utype, parent, agent_id, desc, color in units_data:
        c.execute(
            "INSERT OR REPLACE INTO org_units (id, name, short_name, unit_type, parent_id, agent_id, description, color) VALUES (?,?,?,?,?,?,?,?)",
            (id_, name, short, utype, parent, agent_id, desc, color)
        )
    
    # ===== EMPLEADOS =====
    employees_data = [
        # ADAM GRÁFICA → Creativo
        ("Gen Pro",            "Generador de Contenido PRO",   6, "adamgrafica"),
        ("THE RETOUCH WIZARD",  "Retoque y Post-producción",   6, "adamgrafica"),
        # ADAM GRÁFICA → Desarrollo
        ("CODE ARCHITECT",     "Arquitecto de Código",         7, "adamgrafica"),
        # ADAM GRÁFICA → Marketing
        ("CMO Agent",          "Estrategia de Marketing",      8, "adamgrafica"),
        # ADAM GRÁFICA → Infraestructura
        ("HERALD",             "Monitor de Infraestructura",   9, "adamgrafica"),
        # MIDI SOFT → I+D
        ("MIDI Developer",     "Desarrollo MIDI + IA",       11, "midisoft"),
        # MIDI SOFT → Producción
        ("Composer AI",        "Composición Musical IA",     12, "midisoft"),
        ("Sound Engineer",     "Ingeniero de Sonido",        12, "midisoft"),
    ]
    for name, role, dept, stack in employees_data:
        c.execute(
            "INSERT INTO employees (name, role, department_id, stack) VALUES (?,?,?,?)",
            (name, role, dept, stack)
        )
    
    # ===== TAREAS INICIALES =====
    tasks = [
        ("ARMAR ESTRUCTURA ADAM OS EN COMMAND CENTER", "Implementar jerarquía real: AXON→HERMES→Subagentes→Unidades→Departamentos→Empleados", "AXON", "agent", None, None, "in_progress", "v3.0", "critical", 60),
        ("DEFINIR DEPARTAMENTOS DE AXON-MUSIC", "Elegir estratégicamente los sub-departamentos de Axon-Music", "AXON", "agent", None, None, "pending", "v3.0", "high", 0),
        ("CONFIGURAR EMPLEADOS EN CADA DEPARTAMENTO", "Verificar que cada empleado esté en su departamento correcto", "HERMES", "agent", None, None, "pending", "v3.0", "high", 0),
        ("CREAR PRIMERA TÁREA REAL PARA ADAM GRÁFICA", "Asignar primera misión real al equipo de AdamGráfica", "AXON", "agent", None, None, "pending", "v3.0", "medium", 0),
    ]
    for title, desc, assigned, atype, dept_id, emp_id, status, mission, priority, progress in tasks:
        c.execute(
            "INSERT INTO tasks (title, description, assigned_to, assigned_to_type, department_id, employee_id, status, mission, priority, progress) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (title, desc, assigned, atype, dept_id, emp_id, status, mission, priority, progress)
        )
    
    # ===== LOGS INICIALES =====
    logs = [
        ("AXON", "system_start", "ADAM OS Command Center v3", "success", "Jerarquía real implementada"),
        ("HERMES", "route", "AXON → estructura org", "success", "Enrutando tareas a agentes coordinadores"),
        ("Axon-Work", "init", "Unidades de negocio", "success", "ADAM GRÁFICA + MIDI SOFT activos"),
        ("Gen Pro", "idle", "", "idle", "Esperando tarea creativa"),
        ("CODE ARCHITECT", "idle", "", "idle", "Esperando tarea de desarrollo"),
        ("HERALD", "monitor", "infraestructura", "success", "Sistemas operativos"),
    ]
    for agent, action, target, status, details in logs:
        c.execute(
            "INSERT INTO agent_logs (agent_name, action, target, status, details) VALUES (?,?,?,?,?)",
            (agent, action, target, status, details)
        )
    
    # ===== MENSAJE DE BIENVENIDA =====
    c.execute(
        "INSERT INTO chat_messages (sender, message, session_id) VALUES (?,?,?)",
        ("AXON", "¡Bienvenido al ADAM OS Command Center v3, Natch! 🚀 La jerarquía está lista: AXON → HERMES → Subagentes → Unidades → Departamentos → Empleados. ¿Qué vamos a conquistar hoy?", "default")
    )

# ============================
# QUERIES
# ============================

def get_agents():
    conn = get_db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM agents ORDER BY level, id").fetchall()
    conn.close()
    return dict_list(rows)

def get_org_units(parent_id=None, agent_id=None):
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
    query = "SELECT * FROM org_units"
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
    """Returns the complete org tree: agents → units → departments → employees."""
    conn = get_db()
    c = conn.cursor()
    
    # Agents with children
    agents = dict_list(c.execute("SELECT * FROM agents ORDER BY level, id").fetchall())
    agent_map = {a["id"]: a for a in agents}
    for a in agents:
        a["children_agents"] = []
        a["units"] = []
    for a in agents:
        if a["parent_id"] and a["parent_id"] in agent_map:
            agent_map[a["parent_id"]]["children_agents"].append(a)
    
    def get_children(parent_id):
        rows = c.execute(
            "SELECT * FROM org_units WHERE parent_id=? ORDER BY id",
            (parent_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["employees"] = dict_list(c.execute(
                "SELECT * FROM employees WHERE department_id=?", (d["id"],)
            ).fetchall())
            d["children"] = get_children(d["id"])
            result.append(d)
        return result
    
    # Attach units to each agent
    for agent in agents:
        units = dict_list(c.execute(
            "SELECT * FROM org_units WHERE agent_id=? AND parent_id IS NULL ORDER BY id",
            (agent["id"],)
        ).fetchall())
        for u in units:
            u["employees"] = dict_list(c.execute(
                "SELECT * FROM employees WHERE department_id=?", (u["id"],)
            ).fetchall())
            u["children"] = get_children(u["id"])
        agent["units"] = units
    
    conn.close()
    return agents

def get_tasks(status=None):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT t.*, o.name as department_name FROM tasks t LEFT JOIN org_units o ON t.department_id=o.id"
    params = []
    conditions = []
    if status:
        conditions.append("t.status = ?")
        params.append(status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, t.created_at DESC"
    rows = c.execute(query, params).fetchall()
    conn.close()
    return dict_list(rows)

def create_task(title, description="", assigned_to="AXON", assigned_to_type="agent", 
                department_id=None, employee_id=None, mission="", priority="medium"):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        """INSERT INTO tasks (title, description, assigned_to, assigned_to_type, department_id, employee_id, mission, priority)
           VALUES (?,?,?,?,?,?,?,?)""",
        (title, description, assigned_to, assigned_to_type, department_id, employee_id, mission, priority)
    )
    task_id = c.lastrowid
    conn.commit()
    task = c.execute("SELECT t.*, o.name as department_name FROM tasks t LEFT JOIN org_units o ON t.department_id=o.id WHERE t.id=?", (task_id,)).fetchone()
    conn.close()
    log_agent_action("AXON", "task_create", f"Task #{task_id}: {title[:60]}")
    return dict_row(task)

def update_task(task_id, **kwargs):
    allowed = {"title", "description", "assigned_to", "assigned_to_type", "status", "priority", 
               "progress", "mission", "department_id", "employee_id"}
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
    task = c.execute("SELECT t.*, o.name as department_name FROM tasks t LEFT JOIN org_units o ON t.department_id=o.id WHERE t.id=?", (task_id,)).fetchone()
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
    c = conn.cursor()
    rows = c.execute("SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
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
    if sender != "AXON":
        log_agent_action(sender, "chat_message", message[:80])
    return dict_row(msg)

if __name__ == "__main__":
    # Remove old db to start fresh
    db_path = DB_PATH
    if os.path.exists(db_path):
        backup = db_path + ".bak"
        os.rename(db_path, backup)
        print(f"📦 Respaldada DB anterior → {backup}")
    
    init_db()
    print("✅ ADAM OS v3 Database initialized!")
    print(f"   Path: {DB_PATH}")
    print(f"   Agentes: {len(get_agents())}")
    print(f"   Unidades: {len(get_org_units())}")
    print(f"   Empleados: {len(get_employees())}")
    
    # Show hierarchy
    hier = get_full_hierarchy()
    for agent in hier:
        print(f"\n{agent['name']} ({agent['role']})")
        for unit in agent.get("units", []):
            print(f"  ├── {unit['name']} [{unit['unit_type']}]")
            for child in unit.get("children", []):
                print(f"  │   ├── {child['name']} [{child['unit_type']}]")
                for emp in child.get("employees", []):
                    print(f"  │   │   ├── {emp['name']} ({emp['role']})")
            for emp in unit.get("employees", []):
                print(f"  │   ├── {emp['name']} ({emp['role']})")
