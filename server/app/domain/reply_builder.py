from __future__ import annotations

from app.i18n.messages import msg


def build_reply(action: dict, dialect: str) -> str:
    t = action.get("type")
    payload = action.get("payload") or {}

    if t == "create_task":
        return msg("task_created", dialect)

    if t == "list_tasks":
        return msg("tasks_list", dialect)

    if t == "update_task":
        # لو في not found
        if payload.get("ok") is False and payload.get("reason") == "not_found":
            return msg("not_found", dialect)
        return msg("task_updated", dialect)

    if t == "delete_task":
        # لو فشل الحذف (not found)
        if payload.get("ok") is False:
            return msg("not_found", dialect)
        return msg("task_deleted", dialect)

    if t == "not_implemented":
        return msg("not_implemented", dialect)

    if t == "clarify":
        # إذا فيه رسالة مخصّصة من executor
        custom = payload.get("message")
        return custom or msg("clarify", dialect)


    if t == "complete_task":
        return msg("task_completed", dialect)
