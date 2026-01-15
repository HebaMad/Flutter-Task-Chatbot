from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

Intent = Literal[
    "create_task",
    "update_task",
    "delete_task",
    "complete_task",
    "list_tasks",
    "clarify",
]


class IntentResult(BaseModel):
    intent: Intent = Field(..., description="The user intent")
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: Dict[str, Any] = Field(default_factory=dict)
    clarification: Optional[str] = None


_parser = PydanticOutputParser(pydantic_object=IntentResult)

_SYSTEM = """
You are an intent extractor for a task management app.
Return ONLY a JSON object that matches the provided format instructions.

Rules:
- If the message is ambiguous or missing required details, set intent="clarify"
  and write a short clarification question in clarification.
- Do NOT execute actions.
- Do NOT include extra keys.
- Keep entities minimal and relevant.
""".strip()

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM),
        ("human", "Message: {message}\n\n{format_instructions}"),
    ]
)

# Lazy chain init (prevents import-time crash during pytest collection)
_chain = None


def _get_chain():
    global _chain
    if _chain is not None:
        return _chain

    if not settings.gemini_api_key:
        # Don't build LLM chain without key
        return None

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,
    )

    _chain = _PROMPT | llm | _parser
    return _chain


def interpret_intent_with_langchain(message: str) -> IntentResult:
    chain = _get_chain()

    if chain is None:
        return IntentResult(
            intent="clarify",
            confidence=0.0,
            entities={"raw": message},
            clarification="Missing Gemini API key",
        )

    return chain.invoke(
        {
            "message": message,
            "format_instructions": _parser.get_format_instructions(),
        }
    )
