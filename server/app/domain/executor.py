from __future__ import annotations

from typing import Any, Dict

from app.domain.tasks import TaskStore


def execute_intent(
    *,
    store: TaskStore,
    user_id: str,
    intent: str,
    entities: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executes supported intents and returns an action payload.
    This is the "Backend executes" part.
    """
    if intent == "create_task":
        title = (entities.get("title") or "").strip()
        due_text = entities.get("due_text")

        if not title:
            return {
                "type": "clarify",
                "message": "شو اسم المهمة؟",
            }

        task = store.create_task(user_id=user_id, title=title, due_text=due_text)
        return {
            "type": "task_created",
            "task": {
                "id": task.id,
                "title": task.title,
                "due_text": task.due_text,
                "completed": task.completed,
            },
        }

    if intent == "list_tasks":
        tasks = store.list_tasks(user_id=user_id)
        return {
            "type": "tasks_list",
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "due_text": t.due_text,
                    "completed": t.completed,
                }
                for t in tasks
            ],
        }

    # Not implemented yet (Day 6/7)
    return {
        "type": "not_implemented",
        "intent": intent,
    }
