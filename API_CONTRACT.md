# API Contract — ADAM OS Dashboard v2

## Endpoints

### GET /api/health
```json
{
  "status": "online",
  "hermes": "online",
  "version": "1.0.0",
  "uptime_seconds": 0
}
```

### GET /api/system
```json
{
  "cpu": { "percent": 0, "cores": 0 },
  "memory": { "total_gb": 0, "used_gb": 0, "percent": 0 },
  "disk": { "total_gb": 0, "used_gb": 0, "percent": 0 }
}
```

### GET /api/notion/tasks
```json
{
  "total": 8,
  "por_hacer": 5,
  "en_proceso": 1,
  "completado": 2,
  "items": [
    {"name": "Tarea ejemplo", "status": "Por hacer", "progress": null}
  ]
}
```

### GET /api/notion/projects
```json
{
  "active": 3,
  "projects": [
    {"name": "Carolina Marina", "status": "En Proceso", "type": "Branding + Presencia Digital"}
  ]
}
```

### GET /api/notion/clients
```json
{
  "total": 0, "active": 0, "prospect": 0, "inactive": 0
}
```

### GET /api/config
```json
{
  "stacks": {
    "adamgrafica": {
      "name": "AdamGráfica",
      "type": "Agencia de Marketing",
      "services": ["Branding", "Redes Sociales", "Diseño Gráfico", "Marketing Digital"],
      "description": "Agencia 95% IA - Valparaíso, Chile",
      "since": 2018
    },
    "midisoft": {
      "name": "Midisoft",
      "type": "Agencia de Desarrollo",
      "services": ["Tauri Apps", "TypeScript/Rust", "Sistemas IA", "MIDI AI Ecosystem"],
      "description": "Agentic Development Environment",
      "since": 2024
    }
  },
  "agents": [
    {"name": "Hermes", "role": "Meta-Agent Router", "status": "online"},
    {"name": "Axon", "role": "Executive Orchestrator", "status": "online"},
    {"name": "Gen Pro", "role": "Sistema de Prompts", "status": "online"},
    {"name": "CODE ARCHITECT", "role": "Arquitecto de Software", "status": "online"},
    {"name": "THE RETOUCH WIZARD", "role": "Director Visual", "status": "standby"},
    {"name": "HERALD", "role": "Custodio Dev (Perplexity)", "status": "standby"},
    {"name": "CMO Agent", "role": "Marketing (Perplexity)", "status": "standby"},
    {"name": "Gen Asesor Coach", "role": "Notion + Proyectos", "status": "online"}
  ],
  "routers": [
    {"name": "Router Core", "mode": "Activo", "description": "Rutas por modo: Ejecutor/Desarrollador/Pesado"},
    {"name": "MCP Gateway", "mode": "Activo", "description": "Contexto compartido entre agentes"},
    {"name": "Kanban Orchestrator", "mode": "Activo", "description": "Delegación y planificación"}
  ]
}
```

## Notion Page IDs for backend
- Tareas DB: 1ba5f8c7-cf88-80f1-9547-000bde777ec3
- Team Tasks DB: bb264787-8b72-4f68-93af-77b963ca5da4
- Proyectos page: 2885f8c7-cf88-80b1-99a5-fd7eeb12abf8
- Clientes page: 2885f8c7-cf88-80aa-8ee4-eec921b03a0e

## Stack
- Backend: Python FastAPI + uvicorn
- Frontend: Single HTML file (vanilla JS, no frameworks)
- Deploy: Dockerfile → CapRover
- Port: 8080 (CapRover standard)
