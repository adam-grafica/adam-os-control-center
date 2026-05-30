"""ADAM OS Control Center — Command Center Service

Kanban-style task board for orchestrating ADAM OS tasks across 6 columns:
backlog, ready, running, blocked, review, done.

All data is held in-memory (ephemeral). For persistence, extend with
SQLite/StateDB integration.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Column definitions ──

KANBAN_COLUMNS = ["backlog", "ready", "running", "blocked", "review", "done"]
VALID_TRANSITIONS = {
    "backlog": ["ready"],
    "ready": ["running", "blocked"],
    "running": ["blocked", "review", "backlog"],
    "blocked": ["ready", "running", "backlog"],
    "review": ["running", "done", "backlog"],
    "done": ["backlog"],
}


class CommandCenter:
    """In-memory Kanban task board.

    Tasks flow through 6 columns: backlog → ready → running → review → done.
    Tasks can also be moved to blocked (from ready, running) or back to a
    previous column.
    """

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._columns: Dict[str, List[str]] = {
            col: [] for col in KANBAN_COLUMNS
        }

    # ── Public API ──

    def get_kanban(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return the full kanban board with tasks grouped by column.

        Returns:
            Dict mapping column names to lists of task dicts.
        """
        board: Dict[str, List[Dict[str, Any]]] = {}
        for col in KANBAN_COLUMNS:
            board[col] = [self._tasks[tid] for tid in self._columns[col] if tid in self._tasks]
        return board

    def get_kanban_column(self, column: str) -> Optional[List[Dict[str, Any]]]:
        """Return tasks in a specific column."""
        if column not in self._columns:
            return None
        return [
            self._tasks[tid] for tid in self._columns[column] if tid in self._tasks
        ]

    def create_task(
        self,
        title: str,
        priority: str = "medium",
        description: str = "",
        column: str = "backlog",
        **extra: Any,
    ) -> Dict[str, Any]:
        """Create a new task and place it in the specified column.

        Args:
            title: task title.
            priority: low, medium, high, critical.
            description: task description/details.
            column: target column (default: backlog).
            **extra: additional task fields.

        Returns:
            The created task dict.
        """
        if column not in self._columns:
            column = "backlog"

        valid_priorities = {"low", "medium", "high", "critical"}
        if priority not in valid_priorities:
            priority = "medium"

        task_id = str(uuid.uuid4())[:8]
        now = time.time()

        task: Dict[str, Any] = {
            "id": task_id,
            "title": title,
            "priority": priority,
            "description": description,
            "column": column,
            "created_at": now,
            "updated_at": now,
            "assigned_to": None,
            "status": "open",
            **extra,
        }
        self._tasks[task_id] = task
        self._columns[column].append(task_id)
        logger.info("Task %s created in column '%s': %s", task_id, column, title)
        return task

    def move_task(
        self, task_id: str, from_column: str, to_column: str
    ) -> Optional[Dict[str, Any]]:
        """Move a task from one column to another.

        Args:
            task_id: the task to move.
            from_column: current column.
            to_column: target column.

        Returns:
            Updated task dict, or None if the move is invalid.
        """
        if task_id not in self._tasks:
            logger.warning("Task %s not found", task_id)
            return None

        if from_column not in self._columns:
            logger.warning("Invalid from_column: %s", from_column)
            return None

        if to_column not in self._columns:
            logger.warning("Invalid to_column: %s", to_column)
            return None

        # Validate transition
        allowed = VALID_TRANSITIONS.get(from_column, [])
        if to_column not in allowed and to_column != from_column:
            logger.warning(
                "Invalid transition: %s → %s (allowed from %s: %s)",
                from_column,
                to_column,
                from_column,
                ", ".join(allowed),
            )
            return None

        # Remove from source column
        if task_id in self._columns[from_column]:
            self._columns[from_column].remove(task_id)

        # Add to target
        if task_id not in self._columns[to_column]:
            self._columns[to_column].append(task_id)

        # Update task
        self._tasks[task_id]["column"] = to_column
        self._tasks[task_id]["updated_at"] = time.time()

        if to_column == "done":
            self._tasks[task_id]["status"] = "done"
            self._tasks[task_id]["completed_at"] = time.time()
        elif self._tasks[task_id]["status"] == "done":
            self._tasks[task_id]["status"] = "open"
            self._tasks[task_id].pop("completed_at", None)

        logger.info(
            "Task %s moved: %s → %s", task_id, from_column, to_column
        )
        return self._tasks[task_id]

    def assign_task(self, task_id: str, agent_id: str) -> Optional[Dict[str, Any]]:
        """Assign a task to an agent.

        Args:
            task_id: the task to assign.
            agent_id: the agent identifier.

        Returns:
            Updated task dict, or None if not found.
        """
        if task_id not in self._tasks:
            logger.warning("Task %s not found for assignment", task_id)
            return None

        self._tasks[task_id]["assigned_to"] = agent_id
        self._tasks[task_id]["updated_at"] = time.time()
        logger.info("Task %s assigned to %s", task_id, agent_id)
        return self._tasks[task_id]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return a single task by ID."""
        return self._tasks.get(task_id)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the system entirely.

        Returns:
            True if deleted, False if not found.
        """
        if task_id not in self._tasks:
            return False
        # Remove from column
        for col in self._columns.values():
            if task_id in col:
                col.remove(task_id)
        del self._tasks[task_id]
        logger.info("Task %s deleted", task_id)
        return True

    def get_tasks_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Return all tasks assigned to a specific agent."""
        return [
            t for t in self._tasks.values() if t.get("assigned_to") == agent_id
        ]

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def column_counts(self) -> Dict[str, int]:
        return {col: len(tasks) for col, tasks in self._columns.items()}


# ── Module-level singleton ──

command_center = CommandCenter()
