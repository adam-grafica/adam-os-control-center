"""
Pipeline de Manufactura — MIDI SOFT & AdamGráfica.

Tracks cada proyecto a través de las 7 fases del pipeline
con departamento activo, historial de fases completadas,
y entregables por fase.
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class PipelinePhase:
    """Una fase completada del pipeline."""
    phase_id: int  # 0-6
    name: str
    department: str
    status: str  # completed, in_progress, pending
    started_at: str
    completed_at: str | None = None
    deliverables: list[dict] = field(default_factory=list)
    signatories: list[str] = field(default_factory=list)


@dataclass
class PipelineProject:
    """Un proyecto en el pipeline."""
    project_id: str
    name: str
    team: str  # "midisoft" | "adamgrafica"
    current_phase: int  # 0-6
    phase_name: str
    active_department: str
    agent_progress: str  # e.g. "3/5 tasks done"
    phases: list[dict] = field(default_factory=list)
    pending_tasks: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class PipelineManager:
    """Gestiona el estado del pipeline para todos los proyectos."""

    # The 7 phases of the MIDI SOFT pipeline
    PHASES = [
        (0, "Intake & Brief", "Product", "📋"),
        (1, "Deep Research", "Product + UX/UI", "🔍"),
        (2, "Arquitectura & Coordinación", "Engineering", "🏗️"),
        (3, "Consenso de Ingeniería", "All Departments", "🤝"),
        (4, "Ejecución", "Engineering + QA", "⚡"),
        (5, "Integración & QA", "QA/Quality", "✅"),
        (6, "Deploy & Sign-off", "Delivery/Program Ops", "🚀"),
    ]

    # Phase descriptions for the visual pipeline
    PHASE_DESCRIPTIONS = [
        "Definición del proyecto y alcance inicial",
        "Investigación profunda del dominio y competidores",
        "Arquitectura del sistema y coordinación de módulos",
        "Consenso de ingeniería y sign-off técnico",
        "Implementación en paralelo por agentes",
        "Tests, revisión de código y validación",
        "Deploy final, documentación y cierre",
    ]

    def __init__(self, state_dir: str = ""):
        self._state_dir = state_dir or os.environ.get(
            "STATE_DB_PATH",
            os.path.expanduser("~/.hermes/state")
        )
        self._projects: dict[str, PipelineProject] = {}
        self._load_state()

    def _state_file_path(self) -> str:
        """Return the path to the pipeline state JSON file."""
        # Store alongside the state DB directory
        parent = os.path.dirname(self._state_dir)
        return os.path.join(parent, "pipeline_state.json")

    def _load_state(self):
        """Load project states from disk."""
        state_file = self._state_file_path()
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    data = json.load(f)
                    for pid, pdata in data.get("projects", {}).items():
                        self._projects[pid] = PipelineProject(**pdata)
                logger.info(
                    "Loaded %d pipeline projects from %s",
                    len(self._projects), state_file
                )
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning("Failed to load pipeline state: %s", exc)

    def _save_state(self):
        """Persist pipeline state to disk."""
        state_file = self._state_file_path()
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "w") as f:
            json.dump({
                "projects": {pid: asdict(p) for pid, p in self._projects.items()},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)

    def register_project(
        self,
        project_id: str,
        name: str,
        team: str = "midisoft"
    ) -> PipelineProject:
        """Register a new project entering the pipeline."""
        now = datetime.now(timezone.utc).isoformat()
        pid, pname, pdept, _ = self.PHASES[0]
        self._projects[project_id] = PipelineProject(
            project_id=project_id,
            name=name,
            team=team,
            current_phase=0,
            phase_name=pname,
            active_department=pdept,
            agent_progress="Awaiting intake...",
            phases=[{
                "phase_id": pid,
                "name": pname,
                "department": pdept,
                "status": "in_progress",
                "started_at": now,
                "deliverables": [],
                "signatories": []
            }],
            pending_tasks=[
                {
                    "id": f"{project_id}-review-brief",
                    "title": "Review project brief",
                    "department": "Product",
                    "status": "pending"
                },
                {
                    "id": f"{project_id}-define-scope",
                    "title": "Define project scope",
                    "department": "Product",
                    "status": "pending"
                },
            ],
            created_at=now,
            updated_at=now
        )
        self._save_state()
        logger.info(
            "Project %s (%s) registered in pipeline at phase 0",
            project_id, name
        )
        return self._projects[project_id]

    def advance_phase(self, project_id: str) -> dict | None:
        """Advance project to next phase. Returns the new phase or None if complete."""
        project = self._projects.get(project_id)
        if not project:
            logger.warning("advance_phase: project %s not found", project_id)
            return None

        if project.current_phase >= 6:
            logger.info("Project %s already at final phase", project_id)
            return None

        now = datetime.now(timezone.utc).isoformat()

        # Mark current phase as completed
        for phase in project.phases:
            if phase["phase_id"] == project.current_phase:
                phase["status"] = "completed"
                phase["completed_at"] = now
                break

        # Advance to next phase
        next_idx = project.current_phase + 1
        if next_idx < 7:
            pid, pname, pdept, _ = self.PHASES[next_idx]
            new_phase = {
                "phase_id": pid,
                "name": pname,
                "department": pdept,
                "status": "in_progress",
                "started_at": now,
                "deliverables": [],
                "signatories": []
            }
            project.phases.append(new_phase)
            project.current_phase = pid
            project.phase_name = pname
            project.active_department = pdept
            project.agent_progress = "Phase started..."
            logger.info("Project %s advanced to phase %d: %s", project_id, pid, pname)

        project.updated_at = now
        self._save_state()
        return asdict(project)

    def set_phase(self, project_id: str, target_phase: int) -> dict | None:
        """Set a project to a specific phase (fast-forward or rewind)."""
        project = self._projects.get(project_id)
        if not project:
            return None

        target_phase = max(0, min(target_phase, 6))
        now = datetime.now(timezone.utc).isoformat()

        # Build phases up to target
        phases_built: list[dict] = []
        for i in range(target_phase + 1):
            pid, pname, pdept, _ = self.PHASES[i]
            existing = next(
                (p for p in project.phases if p["phase_id"] == pid),
                None
            )
            if existing:
                phases_built.append(existing)
            else:
                phases_built.append({
                    "phase_id": pid,
                    "name": pname,
                    "department": pdept,
                    "status": "in_progress" if i == target_phase else "completed",
                    "started_at": now,
                    "completed_at": now if i < target_phase else None,
                    "deliverables": [],
                    "signatories": []
                })

        # Mark all phases before target as completed
        for i, phase in enumerate(phases_built):
            if i < target_phase:
                phase["status"] = "completed"
                if not phase.get("completed_at"):
                    phase["completed_at"] = now
            elif i == target_phase:
                phase["status"] = "in_progress"

        pid, pname, pdept, _ = self.PHASES[target_phase]
        project.phases = phases_built
        project.current_phase = target_phase
        project.phase_name = pname
        project.active_department = pdept
        project.agent_progress = "Phase started..." if target_phase > 0 else "Awaiting intake..."
        project.updated_at = now

        self._save_state()
        logger.info("Project %s set to phase %d: %s", project_id, target_phase, pname)
        return asdict(project)

    def update_agent_progress(self, project_id: str, progress: str):
        """Update the agent progress string for a project."""
        project = self._projects.get(project_id)
        if project:
            project.agent_progress = progress
            project.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_state()
            return True
        return False

    def add_deliverable(
        self,
        project_id: str,
        phase_id: int,
        title: str,
        url: str = ""
    ):
        """Add a deliverable to a specific phase."""
        project = self._projects.get(project_id)
        if project:
            for phase in project.phases:
                if phase["phase_id"] == phase_id:
                    phase["deliverables"].append({
                        "title": title,
                        "url": url,
                        "added_at": datetime.now(timezone.utc).isoformat()
                    })
                    project.updated_at = datetime.now(timezone.utc).isoformat()
                    self._save_state()
                    return True
        return False

    def add_pending_task(self, project_id: str, title: str, department: str):
        """Add a pending task."""
        project = self._projects.get(project_id)
        if project:
            task_id = f"{project_id}-{len(project.pending_tasks)}"
            project.pending_tasks.append({
                "id": task_id,
                "title": title,
                "department": department,
                "status": "pending"
            })
            project.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_state()
            return True
        return False

    def complete_task(self, project_id: str, task_id: str):
        """Mark a task as completed."""
        project = self._projects.get(project_id)
        if project:
            for task in project.pending_tasks:
                if task["id"] == task_id:
                    task["status"] = "completed"
                    task["completed_at"] = datetime.now(timezone.utc).isoformat()
                    project.updated_at = datetime.now(timezone.utc).isoformat()
                    self._save_state()
                    return True
        return False

    def get_all_projects(self) -> list[dict]:
        """Get all active projects with their pipeline status."""
        return [asdict(p) for p in self._projects.values()]

    def get_project(self, project_id: str) -> dict | None:
        """Get specific project pipeline data."""
        project = self._projects.get(project_id)
        return asdict(project) if project else None

    def get_pipeline_overview(self) -> dict:
        """Get pipeline overview stats with phase details."""
        total = len(self._projects)
        by_phase: dict[int, int] = {}
        phase_details: list[dict] = []

        for phase_id, phase_name, dept, icon in self.PHASES:
            count = sum(
                1 for p in self._projects.values()
                if p.current_phase == phase_id
            )
            by_phase[phase_id] = count
            phase_details.append({
                "phase_id": phase_id,
                "name": phase_name,
                "department": dept,
                "icon": icon,
                "active_projects": count,
                "description": self.PHASE_DESCRIPTIONS[phase_id],
            })

        return {
            "total_projects": total,
            "projects_by_phase": by_phase,
            "phase_details": phase_details,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_pipeline: PipelineManager | None = None


def get_pipeline() -> PipelineManager:
    global _pipeline
    if _pipeline is None:
        _pipeline = PipelineManager()
    return _pipeline
