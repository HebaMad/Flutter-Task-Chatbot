from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from app.services.firestore_client import get_db
from firebase_admin import firestore as fb_fs
from app.utils.text_matcher import is_relevant, candidate_score

@dataclass
class Task:
    id: str
    title: str
    status: str  # todo | done
    dueAt: Optional[int] = None  # epoch seconds or timestamp
    description: Optional[str] = None
    priority: str = "medium"
    createdAt: Optional[int] = None
    updatedAt: Optional[int] = None
    source: str = "ui"
    durationMinutes: Optional[int] = None

class TaskStore:
    """
    Firestore task storage.
    Scoped per userId: users/{userId}/tasks/{taskId}
    """

    def __init__(self):
        pass

    def _get_collection(self, user_id: str):
        db = get_db()
        return db.collection("users").document(user_id).collection("tasks")

    def create_task(
        self,
        user_id: str,
        title: str,
        description: str = None,
        due_at: int = None,
        priority: str = "medium",
        source: str = "ui",
        duration_minutes: Optional[int] = None,
    ) -> Task:
        coll = self._get_collection(user_id)
        doc_ref = coll.document()
        
        task_data = {
            "title": title,
            "description": description,
            "dueAt": due_at,
            "priority": priority,
            "status": "todo",
            "source": source,
            "durationMinutes": duration_minutes,
            "createdAt": fb_fs.SERVER_TIMESTAMP,
            "updatedAt": fb_fs.SERVER_TIMESTAMP
        }
        doc_ref.set(task_data)
        
        return Task(
            id=doc_ref.id, 
            title=title, 
            status="todo", 
            description=description, 
            dueAt=due_at, 
            priority=priority,
            source=source,
            durationMinutes=duration_minutes,
        )

    def list_tasks(
        self, 
        user_id: str, 
        status: str = "todo", 
        scope: str = "all", 
        timezone: str = "UTC"
    ) -> List[Task]:
        coll = self._get_collection(user_id)
        
        # Base query
        query = coll
        
        # Filter by status
        if status != "all":
            query = query.where("status", "==", status)
            
        # Execute query
        docs = query.stream()
        
        tasks: List[Task] = []
        for doc in docs:
            tasks.append(self._map_to_task(doc.id, doc.to_dict()))
            
        # Filter by scope (in memory/python because firestore range queries on multiple fields are tricky without composite indexes)
        if scope == "today":
            from datetime import datetime
            import pytz
            try:
                tz = pytz.timezone(timezone)
            except:
                tz = pytz.UTC
            
            now = datetime.now(tz)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999).timestamp()
            
            filtered_tasks = []
            for t in tasks:
                if t.dueAt and start_of_day <= t.dueAt <= end_of_day:
                    filtered_tasks.append(t)
            return filtered_tasks
            
        return tasks

    def _map_to_task(self, doc_id: str, data: dict) -> Task:
        # Helper to convert Firestore dict to Task object
        # Handle timestamps (Firestore Timestamp objects)
        created_at = data.get("createdAt")
        if hasattr(created_at, "timestamp"):
            created_at = int(created_at.timestamp())
        
        updated_at = data.get("updatedAt")
        if hasattr(updated_at, "timestamp"):
            updated_at = int(updated_at.timestamp())

        due_at = data.get("dueAt")
        if hasattr(due_at, "timestamp"):
            due_at = int(due_at.timestamp())

        duration_minutes = data.get("durationMinutes")
        if hasattr(duration_minutes, "timestamp"):
            # safeguard; should not happen
            duration_minutes = int(duration_minutes.timestamp())

        return Task(
            id=doc_id,
            title=data.get("title", ""),
            status=data.get("status", "todo"),
            description=data.get("description"),
            dueAt=due_at,
            priority=data.get("priority", "medium"),
            createdAt=created_at,
            updatedAt=updated_at,
            source=data.get("source", "ui"),
            durationMinutes=duration_minutes,
        )

    def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        coll = self._get_collection(user_id)
        doc = coll.document(task_id).get()
        
        if not doc.exists:
            return None
            
        return self._map_to_task(doc.id, doc.to_dict())

    def update_task(
        self,
        user_id: str,
        task_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        due_at: int | None = None,
        priority: str | None = None,
        status: str | None = None,
        duration_minutes: int | None = None,
    ) -> Optional[Task]:
        coll = self._get_collection(user_id)
        doc_ref = coll.document(task_id)
        
        update_data = {"updatedAt": fb_fs.SERVER_TIMESTAMP}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if due_at is not None:
            update_data["dueAt"] = due_at
        if priority is not None:
            update_data["priority"] = priority
        if status is not None:
            update_data["status"] = status
        if duration_minutes is not None:
            update_data["durationMinutes"] = duration_minutes
            
        doc_ref.update(update_data)
        return self.get_task(user_id, task_id)

    def delete_task(self, user_id: str, task_id: str) -> bool:
        coll = self._get_collection(user_id)
        doc_ref = coll.document(task_id)
        
        if not doc_ref.get().exists:
            return False
            
        doc_ref.delete()
        return True

    def search_tasks(self, user_id: str, query: str, *, limit: int = 5) -> List[Task]:
        q = (query or "").strip().lower()
        if not q:
            return []

        try:
            all_tasks = self.list_tasks(user_id)
        except Exception:
            return []
        matches = []
        for t in all_tasks:
            if q in t.title.lower():
                matches.append(t)
            if len(matches) >= limit:
                break
        return matches

    def fuzzy_search_tasks(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 5,
        status: str = "all",
        scope: str = "all",
    ) -> List[Tuple[Task, float, int]]:
        """
        Relevance-based fuzzy search.
        Returns list of (Task, similarity, overlap) sorted by overlap then similarity.
        """
        q = (query or "").strip()
        if not q:
            return []

        try:
            tasks = self.list_tasks(user_id, status=status, scope=scope)
        except Exception:
            return []
        scored: List[Tuple[Task, float, int]] = []
        for t in tasks:
            ok, overlap, sim = is_relevant(q, t.title, min_overlap=1, min_sim=0.65)
            if not ok:
                continue
            scored.append((t, sim, overlap))

        scored.sort(key=lambda item: (item[2], item[1]), reverse=True)
        return scored[:limit]
