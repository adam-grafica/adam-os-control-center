"""ADAM OS Control Center — Control API Endpoints

Provides the Kanban task board interface: create, move, assign tasks
through the CommandCenter service.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException

from app.services.command_center import command_center, KANBAN_COLUMNS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control", tags=["Control"])


@router.get("/kanban")
async def get_kanban() -> Dict[str, List[Dict[str, Any]]]:
    """Return the full kanban board with tasks grouped by column.

    Columns: backlog, ready, running, blocked, review, done.
    """
    return command_center.get_kanban()


@router.post("/task")
async def create_task(
    body: Dict[str, Any] = Body(
        ...,
        description="Task creation payload",
    ),
) -> Dict[str, Any]:
    """Create a new task in the kanban board.

    Default column is 'backlog'. Valid priorities: low, medium, high, critical.

    Request body:
    ```json
    {
        "title": "Deploy monitoring agent",
        "priority": "high",
        "description": "Set up Prometheus node_exporter on all nodes",
        "column": "ready"
    }
    ```
    """
    title = body.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="'title' is required")

    priority = body.get("priority", "medium")
    description = body.get("description", "")
    column = body.get("column", "backlog")

    task = command_center.create_task(
        title=title,
        priority=priority,
        description=description,
        column=column,
    )
    return task


@router.post("/task/{task_id}/move")
async def move_task(
    task_id: str,
    body: Dict[str, str] = Body(
        ...,
        description="Move payload with from_column and to_column",
    ),
) -> Dict[str, Any]:
    """Move a task between kanban columns.

    Request body:
    ```json
    {
        "from_column": "running",
        "to_column": "review"
    }
    ```
    """
    from_col = body.get("from_column")
    to_col = body.get("to_column")

    if not from_col or not to_col:
        raise HTTPException(
            status_code=400,
            detail="Both 'from_column' and 'to_column' are required",
        )

    result = command_center.move_task(task_id, from_col, to_col)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found or invalid transition '{from_col}' -> '{to_col}'",
        )
    return result


@router.post("/task/{task_id}/assign")
async def assign_task(
    task_id: str,
    body: Dict[str, str] = Body(
        ...,
        description="Assignment payload with agent_id",
    ),
) -> Dict[str, Any]:
    """Assign a task to an agent.

    Request body:
    ```json
    {
        "agent_id": "midisoft"
    }
    ```
    """
    agent_id = body.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="'agent_id' is required")

    result = command_center.assign_task(task_id, agent_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found",
        )
    return result
