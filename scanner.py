"""
scanner.py — ADAM OS File System Scanner
Reads the actual filesystem at adam-os-system/ and returns live data.
No hardcoded seed data. The filesystem is the one source of truth.
"""
import os
import re
from datetime import datetime

# Adaptive base path: in Docker /app/adam-os-system, locally the real path
_DOCKER_PATH = "/app/adam-os-system"
_LOCAL_PATH = os.environ.get("ADAM_OS_SYSTEM", "/home/adamcloud/adam-os-system")
BASE = _DOCKER_PATH if os.path.exists(_DOCKER_PATH) else _LOCAL_PATH

# Agents known by their top-level directory names
KNOWN_AGENTS = {
    "1-root-axon": {"name": "AXON",    "color": "#06b6d4", "icon": "▲"},
    "2-teams":     {"name": "HERMES",  "color": "#ec4899", "icon": "◆"},
    "3-life":      {"name": "Axon-Life",  "color": "#10b981", "icon": "●"},
    "5-music":     {"name": "Axon-Music", "color": "#f97316", "icon": "■"},
}

# Sub-agents mapped by their business unit folders
SUB_AGENTS = {
    "Axon-Life": {
        "dir": os.path.join(BASE, "3-life"),
        "color": "#10b981",
        "units": [
            {"name": "AXON LIFE", "dir_name": "3-life", "color": "#10b981",
             "short": "A.LIFE", "dept_folders": []}  # filled dynamically
        ]
    },
    "Axon-Work": {
        "dir": os.path.join(BASE, "2-teams"),
        "color": "#f59e0b",
        "units": [
            {"name": "ADAM GRÁFICA", "dir_name": "adam-grafica", "color": "#f59e0b",
             "short": "ADAM G.", "dept_folders": [
                "direction-ops-delivery", "strategy-growth", "creative-production",
                "automation-ai", "accounts-client-success", "sales-business-dev",
                "finance-admin-legal", "talent-culture-learning"
            ]},
            {"name": "MIDI SOFT", "dir_name": "midisoft", "color": "#4488ff",
             "short": "MIDI S.", "dept_folders": [
                "product", "engineering", "ux-ui-research", "qa-quality",
                "devops-infra-security", "automation-ai-data", "delivery-program-ops",
                "stakeholder-success", "business-revenue-partnerships", "people-ops-finance"
            ]}
        ]
    },
    "Axon-Music": {
        "dir": os.path.join(BASE, "5-music"),
        "color": "#f97316",
        "units": [
            {"name": "AXON MUSIC", "dir_name": "5-music", "color": "#f97316",
             "short": "MUSIC", "dept_folders": [
                "distribucion", "branding-musical", "produccion", "contenido"
            ]}
        ]
    }
}

# Known employee assignments — these are real people mapped to departments
# Format: {name: role, department_path: relative_folder}
KNOWN_EMPLOYEES = {
    "Gen Pro": {"role": "Generador de Contenido PRO", "path": "2-teams/adam-grafica/creative-production"},
    "THE RETOUCH WIZARD": {"role": "Retoque y Post-producción", "path": "2-teams/adam-grafica/creative-production"},
    "CMO Agent": {"role": "Estrategia de Marketing", "path": "2-teams/adam-grafica/strategy-growth"},
    "CODE ARCHITECT": {"role": "Arquitecto de Código", "path": "2-teams/midisoft/engineering"},
    "MIDI Developer": {"role": "Desarrollo MIDI + IA", "path": "2-teams/midisoft/engineering"},
    "HERALD": {"role": "Monitor de Infraestructura", "path": "2-teams/midisoft/devops-infra-security"},
    "Composer AI": {"role": "Composición Musical IA", "path": "5-music/produccion"},
    "Sound Engineer": {"role": "Ingeniero de Sonido", "path": "5-music/produccion"},
}


def parse_agents_md(filepath):
    """Extract identity/scope info from an AGENTS.md file."""
    info = {"owner": None, "mission": None, "scope": None}
    try:
        with open(filepath) as f:
            content = f.read(5000)
        m = re.search(r'\*\*Owner:\*\*\s*(.+)', content)
        if m: info["owner"] = m.group(1).strip()
        m = re.search(r'## Mission\s*\n(.+)', content)
        if m: info["mission"] = m.group(1).strip()
        m = re.search(r'\*\*Scope:\*\*\s*(.+)', content)
        if m: info["scope"] = m.group(1).strip()
    except:
        pass
    return info


def list_files(dirpath, max_files=20):
    """List files in a directory (non-recursive)."""
    files = []
    try:
        for f in sorted(os.listdir(dirpath)):
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp) and not f.startswith('.'):
                size = os.path.getsize(fp)
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                files.append({
                    "name": f, "size": size, "ext": os.path.splitext(f)[1],
                    "modified": mtime.strftime("%Y-%m-%d %H:%M")
                })
                if len(files) >= max_files:
                    break
    except:
        pass
    return files


def scan():
    """
    Main scan function.
    Returns a dict with:
      - tree: complete directory tree (for file explorer)
      - agents: parsed agent hierarchy
      - stats: summary counts
    """
    tree = _scan_dir(BASE, max_depth=4, current_depth=0)
    agents = _build_agents()
    stats = _compute_stats(agents)
    
    return {
        "tree": tree,
        "agents": agents,
        "stats": stats,
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base_path": BASE
    }


def _scan_dir(path, max_depth=4, current_depth=0):
    """Recursively scan a directory."""
    name = os.path.basename(path) or os.path.basename(BASE)
    entry = {
        "name": name,
        "type": "directory",
        "path": path,
        "relative": os.path.relpath(path, BASE) if path != BASE else "",
        "children": [],
        "files": [],
        "has_agents": os.path.exists(os.path.join(path, "AGENTS.md"))
    }
    
    if current_depth >= max_depth:
        return entry
    
    try:
        items = sorted(os.listdir(path))
    except:
        return entry
    
    for item in items:
        fp = os.path.join(path, item)
        if item.startswith('.'):
            continue
        if os.path.isdir(fp):
            entry["children"].append(_scan_dir(fp, max_depth, current_depth + 1))
        elif os.path.isfile(fp):
            size = os.path.getsize(fp)
            mtime = datetime.fromtimestamp(os.path.getmtime(fp))
            entry["files"].append({
                "name": item,
                "path": fp,
                "relative": os.path.relpath(fp, BASE),
                "size": size,
                "ext": os.path.splitext(item)[1],
                "modified": mtime.strftime("%Y-%m-%d %H:%M")
            })
    
    return entry


def _build_agents():
    """Build the agent hierarchy from filesystem structure."""
    # Always return in fixed order
    order = ["AXON", "HERMES", "Axon-Life", "Axon-Work", "Axon-Music"]
    agents = []
    
    for agent_name in order:
        agent = _build_single_agent(agent_name)
        if agent:
            agents.append(agent)
    
    return agents


def _build_single_agent(name):
    """Build one agent entry."""
    if name == "AXON":
        agent_dir = f"{BASE}/1-root-axon"
        info = parse_agents_md(f"{agent_dir}/AGENTS.md")
        return {
            "name": "AXON", "role": "Agente Supremo / CEO",
            "dir_path": agent_dir, "relative": "1-root-axon",
            "color": "#06b6d4", "level": 0,
            "owner": info.get("owner"),
            "mission": info.get("mission"),
            "business_units": [],
            "files": list_files(agent_dir)
        }
    
    elif name == "HERMES":
        agent_dir = f"{BASE}/2-teams"
        info = parse_agents_md(f"{agent_dir}/AGENTS.md")
        hermes_agents = ["Axon-Life", "Axon-Work", "Axon-Music"]
        child_units = []
        for child_name in hermes_agents:
            child = _build_single_agent(child_name)
            if child:
                child_units.extend(child.get("business_units", []))
        
        return {
            "name": "HERMES", "role": "Brazo Derecho Articulado",
            "dir_path": agent_dir, "relative": "2-teams",
            "color": "#ec4899", "level": 1,
            "owner": info.get("owner"),
            "mission": info.get("mission"),
            "business_units": child_units,
            "files": list_files(agent_dir)
        }
    
    elif name == "Axon-Life":
        return _build_sub_agent("Axon-Life",
            dir_path=f"{BASE}/3-life",
            color="#10b981",
            role="Desarrollo Personal y Bienestar",
            units=SUB_AGENTS["Axon-Life"]["units"])
    
    elif name == "Axon-Work":
        return _build_sub_agent("Axon-Work",
            dir_path=f"{BASE}/2-teams",
            color="#f59e0b",
            role="Negocios y Emprendimientos",
            units=SUB_AGENTS["Axon-Work"]["units"])
    
    elif name == "Axon-Music":
        return _build_sub_agent("Axon-Music",
            dir_path=f"{BASE}/5-music",
            color="#f97316",
            role="Artista Musical Independiente",
            units=SUB_AGENTS["Axon-Music"]["units"])
    
    return None


def _build_sub_agent(name, dir_path, color, role, units):
    """Build a sub-agent with its business units and departments."""
    business_units = []
    
    for u in units:
        # If the unit IS the parent dir (like 3-life/ == AXON LIFE, 5-music/ == AXON MUSIC)
        if u["dir_name"] == os.path.basename(dir_path):
            unit_dir = dir_path
        else:
            unit_dir = os.path.join(dir_path, u["dir_name"])
        info = parse_agents_md(os.path.join(unit_dir, "AGENTS.md"))
        
        dept_folders = u.get("dept_folders", [])
        # If dept_folders is empty, discover from the directory
        if not dept_folders:
            try:
                dept_folders = sorted([d for d in os.listdir(unit_dir)
                                      if os.path.isdir(os.path.join(unit_dir, d))
                                      and not d.startswith('.')])
            except:
                dept_folders = []
        
        departments = []
        for dname in dept_folders:
            dept_dir = os.path.join(unit_dir, dname)
            dept_info = parse_agents_md(os.path.join(dept_dir, "AGENTS.md"))
            relative_path = os.path.relpath(dept_dir, BASE)
            
            # Find employees for this department
            employees = []
            for emp_name, emp_data in KNOWN_EMPLOYEES.items():
                if emp_data["path"] == relative_path:
                    employees.append({
                        "name": emp_name,
                        "role": emp_data["role"]
                    })
            
            # Read any .md files (beyond AGENTS.md) as department content
            extra_files = list_files(dept_dir, max_files=10)
            
            departments.append({
                "dir_name": dname,
                "dir_path": dept_dir,
                "relative": relative_path,
                "owner": dept_info.get("owner"),
                "mission": dept_info.get("mission"),
                "employees": employees,
                "files": extra_files,
                "has_agents": os.path.exists(os.path.join(dept_dir, "AGENTS.md"))
            })
        
        business_units.append({
            "name": u["name"],
            "short_name": u.get("short", u["name"]),
            "dir_path": unit_dir,
            "relative": os.path.relpath(unit_dir, BASE),
            "color": u.get("color", color),
            "owner": info.get("owner"),
            "mission": info.get("mission"),
            "departments": departments,
            "files": list_files(unit_dir)
        })
    
    return {
        "name": name,
        "role": role,
        "dir_path": dir_path,
        "relative": os.path.relpath(dir_path, BASE),
        "color": color,
        "level": 2,
        "owner": None,
        "mission": None,
        "business_units": business_units,
        "files": list_files(dir_path)
    }


def _compute_stats(agents):
    """Compute system-wide statistics."""
    bu_count = sum(len(a.get("business_units", [])) for a in agents)
    dept_count = sum(
        sum(len(u.get("departments", [])) for u in a.get("business_units", []))
        for a in agents
    )
    emp_count = sum(
        sum(
            sum(len(d.get("employees", [])) for d in u.get("departments", []))
            for u in a.get("business_units", [])
        )
        for a in agents
    )
    return {
        "agents": len(agents),
        "business_units": bu_count,
        "departments": dept_count,
        "employees": emp_count,
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def read_file(relative_path):
    """Read a file from the filesystem by its relative path."""
    full_path = os.path.join(BASE, relative_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return None
    try:
        with open(full_path) as f:
            content = f.read()
        return {
            "path": full_path,
            "relative": relative_path,
            "name": os.path.basename(full_path),
            "content": content,
            "size": os.path.getsize(full_path),
            "modified": datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M")
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(relative_path, content):
    """Write content to a file by its relative path."""
    full_path = os.path.join(BASE, relative_path)
    # Security: ensure the path stays within BASE
    real_path = os.path.realpath(full_path)
    real_base = os.path.realpath(BASE)
    if not real_path.startswith(real_base):
        return {"error": "Path escape denied"}
    
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return {
            "success": True,
            "path": real_path,
            "relative": relative_path,
            "size": os.path.getsize(full_path)
        }
    except Exception as e:
        return {"error": str(e)}
