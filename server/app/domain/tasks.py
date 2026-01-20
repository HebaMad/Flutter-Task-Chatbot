from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
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
        task = Task(id=str(uuid4()), title=title, due_text=due_text)
        self._tasks.setdefault(user_id, []).append(task)
        return task

    def list_tasks(self, user_id: str) -> List[Task]:
        return self._tasks.get(user_id, [])

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        for t in self._tasks.get(user_id, []):
            if t.id == task_id:
                return t
        return None

    def update_task(
        self,
        user_id: str,
        task_id: str,
        *,
        title: str | None = None,
        due_text: str | None = None,
        completed: bool | None = None,
    ) -> Optional[Task]:
        t = self.get_task(user_id, task_id)
        if not t:
            return None

        if title is not None:
            t.title = title

        if due_text is not None:
            t.due_text = due_text

        if completed is not None:
            t.completed = completed

        return t

    def delete_task(self, user_id: str, task_id: str) -> bool:
        tasks = self._tasks.get(user_id, [])
        for i, t in enumerate(tasks):
            if t.id == task_id:
                del tasks[i]
                return True
        return False

    
    def search_tasks(self, user_id: str, query: str, *, limit: int = 5) -> List[Task]:
        q = (query or "").strip().lower()
        if not q:
            return []

        matches: List[Task] = []
        for t in self._tasks.get(user_id, []):
            if q in (t.title or "").lower():
                matches.append(t)
            if len(matches) >= limit:
                break

        return matches
