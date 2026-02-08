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




def execute_intent(*, store: TaskStore, user_id: str, intent: str, entities: dict, clarification: str | None = None) -> dict:
    # ---- CLARIFY ----
    if intent == "clarify":
        return {
            "type": "clarify",
            "payload": {"message": clarification or "ممكن توضح أكتر؟"}
        }

    # ---- CREATE ----
    if intent == "create_task":
        title = (entities.get("title") or "").strip()
        due_at = entities.get("due_at")
        description = entities.get("description")
        priority = entities.get("priority", "medium")
        duration_minutes = entities.get("duration_minutes")

        if not title:
            return {"type": "clarify", "payload": {"key": "clarify_missing_title"}}

        try:
            task = store.create_task(
                user_id, 
                title=title, 
                description=description, 
                due_at=due_at, 
                priority=priority,
                source="chat",
                duration_minutes=duration_minutes,
            )
            return {"type": "create_task", "payload": {"task": task.__dict__}}
        except Exception as exc:
            return {"type": "message", "payload": {"message": "تعذر حفظ المهمة حالياً."}}

    # ---- LIST ----
    if intent == "list_tasks":
        status = entities.get("status", "todo")
        scope = entities.get("scope", "all")
        timezone = entities.get("timezone", "UTC")
        try:
            tasks = [t.__dict__ for t in store.list_tasks(user_id, status=status, scope=scope, timezone=timezone)]
            return {"type": "list_tasks", "payload": {"tasks": tasks}}
        except Exception:
            return {"type": "message", "payload": {"message": "تعذر قراءة المهام حالياً."}}

    # ---- UPDATE (with disambiguation) ----
    if intent == "update_task":
        task_id = entities.get("task_id")
        patch = entities.get("patch") or {}
        title_patch = patch.get("title", entities.get("title"))
        duration_minutes = patch.get("duration_minutes", entities.get("duration_minutes"))

        due_at = entities.get("due_at")
        description = entities.get("description")
        priority = entities.get("priority")
        status = entities.get("status")

        if not task_id:
            q = _title_query_from_entities(entities)
            if not q:
                return {
                    "type": "clarify",
                    "payload": {"key": "clarify_update_which_task"},
                }

            matches = store.search_tasks(user_id, q, limit=5)

            if len(matches) == 0:
                return {
                    "type": "clarify",
                    "payload": {"key": "clarify_task_not_found"},
                }

            if len(matches) > 1:
                return {
                    "type": "clarify",
                    "payload": {
                        "key": "clarify_multiple_matches",
                        "candidates": [{"taskId": t.id, "title": t.title} for t in matches],
                    },
                }

            # 1 match -> نفّذ مباشرة
            task_id = matches[0].id

        try:
            task = store.update_task(
                user_id,
                task_id,
                title=title_patch,
                description=description,
                due_at=due_at,
                priority=priority,
                status=status,
                duration_minutes=duration_minutes,
            )
        except Exception:
            task = None

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
                    "payload": {"key": "clarify_complete_which_task"},
                }

            matches = store.search_tasks(user_id, q, limit=5)

            if len(matches) == 0:
                return {
                    "type": "clarify",
                    "payload": {"key": "clarify_task_not_found"},
                }

            if len(matches) > 1:
                return {
                    "type": "clarify",
                    "payload": {
                        "key": "clarify_multiple_matches",
                        "candidates": [{"taskId": t.id, "title": t.title} for t in matches],
                    },
                }

            task_id = matches[0].id

        try:
            task = store.update_task(user_id, task_id, status="done")
        except Exception:
            task = None

        if not task:
            return {
                "type": "complete_task",
                "payload": {"ok": False, "reason": "not_found", "task_id": task_id},
            }

        return {"type": "complete_task", "payload": {"ok": True, "task": task.__dict__}}



    # ---- DELETE (confirmation required) ----
    if intent == "delete_task":
        task_id = entities.get("task_id") or entities.get("taskId")
        confirmed = entities.get("confirmed", False)

        if not task_id:
            return {
                "type": "clarify",
                "payload": {"key": "clarify_delete_which_task"},
            }

        if not confirmed:
            title = entities.get("title") or entities.get("task_title")
            confirm_message = entities.get("confirm_message") or f"Ø¨Ø¯Ùƒ Ø£Ø­Ø°Ù: {title or task_id}ØŸ (Ù†Ø¹Ù…/Ù„Ø§)"
            return {
                "type": "clarify",
                "payload": {
                    "message": confirm_message,
                    "task_id": task_id,
                    "needsConfirmation": True,
                },
            }

        try:
            ok = store.delete_task(user_id, task_id)
        except Exception:
            ok = False
        return {"type": "delete_task", "payload": {"ok": ok, "task_id": task_id}}

    # ---- FALLBACK ----
    return {"type": "not_implemented", "payload": {"intent": intent}}
