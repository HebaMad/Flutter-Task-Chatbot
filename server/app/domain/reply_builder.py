from __future__ import annotations

from app.i18n.messages import msg

def build_reply(action: dict, dialect: str) -> str:
    a_type = action.get("type")

    if a_type == "task_created":
        task = action.get("task", {})
        title = task.get("title", msg("task_default_title", dialect))
        due = task.get("due_text")
        if due:
            return msg("task_created_with_due", dialect).format(title=title, due=due)
        return msg("task_created", dialect).format(title=title)

    if a_type == "tasks_list":
        tasks = action.get("tasks", [])
        if not tasks:
            return msg("tasks_empty", dialect)

        lines = []
        for i, t in enumerate(tasks, start=1):
            title = t.get("title", msg("task_default_title", dialect))
            due = t.get("due_text")
            lines.append(f"{i}) {title}" + (f" — {due}" if due else ""))
        return msg("tasks_list_header", dialect) + "\n" + "\n".join(lines)

    if a_type == "clarify":
        # لو فيه رسالة جاهزة من action استخدميها، وإلا msg
        return action.get("message") or msg("clarify", dialect)

    if a_type == "not_implemented":
        return msg("not_implemented", dialect)

    return msg("ok", dialect)
