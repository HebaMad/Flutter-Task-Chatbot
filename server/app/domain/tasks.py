from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from uuid import uuid4


@dataclass
class Task:
    id: str
    title: str
    due_text: str | None
    completed: bool = False


class TaskStore:
    """
    In-memory task storage.
    Scoped per userId.
    """

    def __init__(self):
        self._tasks: Dict[str, List[Task]] = {}

    def create_task(self, user_id: str, title: str, due_text: str | None) -> Task:
        task = Task(
            id=str(uuid4()),
            title=title,
            due_text=due_text,
        )
        self._tasks.setdefault(user_id, []).append(task)
        return task

    def list_tasks(self, user_id: str) -> List[Task]:
        return self._tasks.get(user_id, [])
