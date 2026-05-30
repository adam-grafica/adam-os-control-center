"""
ADAM OS Control Center — Pipeline Visual API Endpoints

Provides access to the manufacturing pipeline state: project phases,
agent progress, deliverables, and pending tasks across all projects.
"""

from __future__ import annotations

import logging
from typing import Any
import random

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.pipeline_service import get_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


# ─── Request Models ──────────────────────────────────────────────────────


class ProgressUpdate(BaseModel):
    progress: str


class TaskCreate(BaseModel):
    title: str
    department: str = "Engineering"


class DeliverableCreate(BaseModel):
    title: str
    url: str = ""
    phase_id: int = 0


class PhaseSetRequest(BaseModel):
    target_phase: int


# ─── GET Endpoints ───────────────────────────────────────────────────────


@router.get("")
async def list_pipeline_projects() -> list[dict[str, Any]]:
    """List all projects in the pipeline with full phase data."""
    pipeline = get_pipeline()
    return pipeline.get_all_projects()


@router.get("/overview")
async def pipeline_overview() -> dict[str, Any]:
    """Get aggregate pipeline overview with phase-level stats."""
    pipeline = get_pipeline()
    return pipeline.get_pipeline_overview()


@router.get("/{project_id}")
async def get_project_pipeline(project_id: str) -> dict[str, Any]:
    """Get full pipeline data for a specific project."""
    pipeline = get_pipeline()
    project = pipeline.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found in pipeline"
        )
    return project


# ─── POST Endpoints ──────────────────────────────────────────────────────


@router.post("/{project_id}/advance")
async def advance_project_phase(project_id: str) -> dict[str, Any]:
    """Advance a project to its next phase."""
    pipeline = get_pipeline()
    result = pipeline.advance_phase(project_id)
    if result is None:
        project = pipeline.get_project(project_id)
        if project is None:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_id}' not found"
            )
        raise HTTPException(
            status_code=400,
            detail=f"Project '{project_id}' is already at the final phase"
        )
    return result


@router.post("/{project_id}/progress")
async def update_agent_progress(
    project_id: str,
    body: ProgressUpdate
) -> dict[str, Any]:
    """Update the agent progress string for a project."""
    pipeline = get_pipeline()
    success = pipeline.update_agent_progress(project_id, body.progress)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    return {"status": "ok", "project_id": project_id, "progress": body.progress}


@router.post("/{project_id}/tasks")
async def add_pending_task(
    project_id: str,
    body: TaskCreate
) -> dict[str, Any]:
    """Add a pending task to a project."""
    pipeline = get_pipeline()
    success = pipeline.add_pending_task(project_id, body.title, body.department)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    return {"status": "ok", "project_id": project_id, "task": body.title}


@router.post("/{project_id}/deliverables")
async def add_deliverable(
    project_id: str,
    body: DeliverableCreate
) -> dict[str, Any]:
    """Add a deliverable to a specific phase of a project."""
    pipeline = get_pipeline()
    success = pipeline.add_deliverable(project_id, body.phase_id, body.title, body.url)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    return {"status": "ok", "project_id": project_id, "deliverable": body.title}


@router.post("/{project_id}/set-phase")
async def set_project_phase(
    project_id: str,
    body: PhaseSetRequest
) -> dict[str, Any]:
    """Set a project to a specific phase (fast-forward or rewind)."""
    pipeline = get_pipeline()
    result = pipeline.set_phase(project_id, body.target_phase)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project '{project_id}' not found"
        )
    return result


# ─── PATCH Endpoints ─────────────────────────────────────────────────────


@router.patch("/{project_id}/tasks/{task_id}")
async def complete_pending_task(
    project_id: str,
    task_id: str
) -> dict[str, Any]:
    """Mark a pending task as completed."""
    pipeline = get_pipeline()
    success = pipeline.complete_task(project_id, task_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found for project '{project_id}'"
        )
    return {"status": "ok", "task_id": task_id}


# ─── Seed Endpoint ───────────────────────────────────────────────────────


SEED_PROJECTS = [
    {
        "id": "MIDI-CC-001",
        "name": "Torre de Control — ADAM OS",
        "team": "midisoft",
        "phase": 2,
        "progress": "3/8 Architecture modules drafted",
    },
    {
        "id": "MIDI-CC-002",
        "name": "Sistema de Órdenes MIDI",
        "team": "midisoft",
        "phase": 4,
        "progress": "5/12 agent tasks completed",
    },
    {
        "id": "MIDI-CC-003",
        "name": "Plugin Host Universal",
        "team": "midisoft",
        "phase": 1,
        "progress": "Research phase: 4/7 reports done",
    },
    {
        "id": "AG-001",
        "name": "Visual Identity Kit",
        "team": "adamgrafica",
        "phase": 3,
        "progress": "Consensus meeting scheduled",
    },
    {
        "id": "AG-002",
        "name": "Generative Art Engine",
        "team": "adamgrafica",
        "phase": 5,
        "progress": "QA: verifying 3 regression tests",
    },
]


@router.post("/seed")
async def seed_pipeline_data() -> dict[str, Any]:
    """Seed the pipeline with demo projects."""
    from app.services.pipeline_service import get_pipeline

    pipeline = get_pipeline()

    created = []
    for proj in SEED_PROJECTS:
        existing = pipeline.get_project(proj["id"])
        if existing:
            created.append({"id": proj["id"], "status": "already_exists"})
            continue

        p = pipeline.register_project(
            proj["id"], proj["name"], proj["team"]
        )
        # Advance to desired phase
        if proj["phase"] > 0:
            pipeline.set_phase(proj["id"], proj["phase"])
            pipeline.update_agent_progress(proj["id"], proj["progress"])

        # Add some sample deliverables and tasks
        if proj["phase"] >= 2:
            pipeline.add_deliverable(
                proj["id"], 0,
                "Project brief & scope document",
                "/docs/brief.pdf"
            )
            pipeline.add_deliverable(
                proj["id"], 1,
                "Research report — competitive analysis",
                "/docs/research.pdf"
            )

        if proj["phase"] >= 3:
            pipeline.add_deliverable(
                proj["id"], 2,
                "System architecture diagram v1",
                "/docs/arch.pdf"
            )

        pipeline.add_pending_task(
            proj["id"],
            f"Complete {proj['name']} phase {proj['phase'] + 1} deliverables",
            "Engineering"
        )
        pipeline.add_pending_task(
            proj["id"],
            "Final review and sign-off preparation",
            "QA/Quality"
        )

        created.append({"id": proj["id"], "status": "created"})

    overview = pipeline.get_pipeline_overview()
    return {
        "status": "ok",
        "projects_created": len([c for c in created if c["status"] == "created"]),
        "details": created,
        "overview": overview,
    }
