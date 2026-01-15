from __future__ import annotations

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel

# MVP intents
Intent = Literal[
    "create_task",
    "update_task",
    "delete_task",
    "complete_task",
    "list_tasks",
    "clarify",
]


class IntentResult(BaseModel):
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    clarification: Optional[str] = None


def interpret_intent_with_langchain(message: str) -> IntentResult:
    """
    Day 3: placeholder logic (keeps API working).
    Day 4: replace with LangChain ChatPromptTemplate + structured output.
    """
    text = message.strip().lower()

    if text.startswith(("ضيف", "add", "create")):
        return IntentResult(intent="create_task", confidence=0.4, entities={"raw": message})
    if text.startswith(("احذف", "delete", "remove")):
        return IntentResult(intent="delete_task", confidence=0.4, entities={"raw": message})
    if text.startswith(("عدّل", "عدل", "update", "edit")):
        return IntentResult(intent="update_task", confidence=0.4, entities={"raw": message})
    if text.startswith(("كمّل", "كمل", "done", "complete")):
        return IntentResult(intent="complete_task", confidence=0.4, entities={"raw": message})
    if text.startswith(("اعرض", "show", "list")):
        return IntentResult(intent="list_tasks", confidence=0.4, entities={"raw": message})

    return IntentResult(
        intent="clarify",
        confidence=0.0,
        entities={"raw": message},
        clarification="Need more details",
    )
