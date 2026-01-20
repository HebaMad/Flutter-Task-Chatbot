from __future__ import annotations

from app.domain.tasks import TaskStore



def _title_query_from_entities(entities: dict) -> str:
    # IMPORTANT:
    # في update_task، entities["title"] غالباً هو "العنوان الجديد" مش عنوان البحث
    task_ref = entities.get("taskRef") or {}
    return (
        (entities.get("task_title") or "").strip()
        or (task_ref.get("title") or "").strip()
    )




def execute_intent(*, store: TaskStore, user_id: str, intent: str, entities: dict) -> dict:
    # ---- CREATE ----
    if intent == "create_task":
        title = (entities.get("title") or "").strip()
        due_text = entities.get("due_text")

        if not title:
            return {"type": "clarify", "payload": {"message": "بدّي عنوان للمهمة."}}

        task = store.create_task(user_id, title=title, due_text=due_text)
        return {"type": "create_task", "payload": {"task": task.__dict__}}

    # ---- LIST ----
    if intent == "list_tasks":
        tasks = [t.__dict__ for t in store.list_tasks(user_id)]
        return {"type": "list_tasks", "payload": {"tasks": tasks}}

    # ---- UPDATE (with disambiguation) ----
    if intent == "update_task":
        task_id = entities.get("task_id")
        patch = entities.get("patch") or {}
        title_patch = patch.get("title", entities.get("title"))

        due_text = entities.get("due_text")
        completed = entities.get("completed")

 
        if not task_id:
            q = _title_query_from_entities(entities)
            if not q:
                return {
                    "type": "clarify",
                    "payload": {"message": "أي مهمة بدك تعدّلي؟ اعطيني عنوانها."},
                }

            matches = store.search_tasks(user_id, q, limit=5)

            if len(matches) == 0:
                return {
                    "type": "clarify",
                    "payload": {"message": "ما لقيت مهمة بهذا العنوان. شو اسمها بالضبط؟"},
                }

            if len(matches) > 1:
                return {
                    "type": "clarify",
                    "payload": {
                        "message": "في أكثر من مهمة بنفس الاسم، أي وحدة تقصدي؟",
                        "candidates": [{"taskId": t.id, "title": t.title} for t in matches],
                    },
                }

            # 1 match -> نفّذ مباشرة
            task_id = matches[0].id

        task = store.update_task(
            user_id,
            task_id,
            title=title_patch,
            due_text=due_text,
            completed=completed,
        )

        if not task:
            return {
                "type": "update_task",
                "payload": {"ok": False, "reason": "not_found", "task_id": task_id},
            }

        return {"type": "update_task", "payload": {"ok": True, "task": task.__dict__}}

    # ---- COMPLETE (with disambiguation) ----
    if intent == "complete_task":
        task_id = entities.get("task_id")

        if not task_id:
            q = _title_query_from_entities(entities)
            if not q:
                return {
                    "type": "clarify",
                    "payload": {"message": "أي مهمة خلصتيها؟ اعطيني عنوانها."},
                }

            matches = store.search_tasks(user_id, q, limit=5)

            if len(matches) == 0:
                return {
                    "type": "clarify",
                    "payload": {"message": "ما لقيت مهمة بهذا العنوان. شو اسمها بالضبط؟"},
                }

            if len(matches) > 1:
                return {
                    "type": "clarify",
                    "payload": {
                        "message": "في أكثر من مهمة بنفس الاسم، أي وحدة خلصتي؟",
                        "candidates": [{"taskId": t.id, "title": t.title} for t in matches],
                    },
                }

            task_id = matches[0].id

        task = store.update_task(user_id, task_id, completed=True)

        if not task:
            return {
                "type": "complete_task",
                "payload": {"ok": False, "reason": "not_found", "task_id": task_id},
            }

        return {"type": "complete_task", "payload": {"ok": True, "task": task.__dict__}}



    # ---- DELETE (with disambiguation) ----
    if intent == "delete_task":
        task_id = entities.get("task_id")

        if not task_id:
            q = _title_query_from_entities(entities)
            if not q:
                return {
                    "type": "clarify",
                    "payload": {"message": "أي مهمة بدك أحذف؟ اعطيني عنوانها."},
                }

            matches = store.search_tasks(user_id, q, limit=5)

            if len(matches) == 0:
                return {
                    "type": "clarify",
                    "payload": {"message": "ما لقيت مهمة بهذا العنوان. شو اسمها بالضبط؟"},
                }

            if len(matches) > 1:
                return {
                    "type": "clarify",
                    "payload": {
                        "message": "في أكثر من مهمة بنفس الاسم، أي وحدة بدك أحذف؟",
                         "candidates": [{"taskId": t.id, "title": t.title} for t in matches]
                    },
                }

            task_id = matches[0].id

        ok = store.delete_task(user_id, task_id)
        return {"type": "delete_task", "payload": {"ok": ok, "task_id": task_id}}

    # ---- FALLBACK ----
    return {"type": "not_implemented", "payload": {"intent": intent}}
