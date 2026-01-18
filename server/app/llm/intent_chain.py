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

You MUST output a JSON object matching the format instructions.

INTENTS:
- create_task: user asks to add/create a task (Arabic: ضيف/أضف مهمة, English: create/add a task)
- update_task: user asks to change a task
- delete_task: user asks to delete/remove a task
- complete_task: user marks a task done
- list_tasks: user asks to show tasks
- clarify: ONLY when the user intent is unclear OR missing REQUIRED info

REQUIRED for create_task:
- If the message contains a task title (name/what to do), DO NOT ask to clarify.
- Put the title in entities.title.
- If there is a time/date phrase, put it in entities.due_text as text (no need to parse exact date now).

Examples:
User: "Create a task called Review NLP tomorrow at 7pm"
Assistant JSON:
{{"intent":"create_task","confidence":0.85,"entities":{{"title":"Review NLP","due_text":"tomorrow at 7pm"}},"clarification":null}}

User: "ضيف مهمة اسمها مراجعة NLP بكرة الساعة 7"
Assistant JSON:
{{"intent":"create_task","confidence":0.85,"entities":{{"title":"مراجعة NLP","due_text":"بكرة الساعة 7"}},"clarification":null}}

User: "اعرض مهامي"
Assistant JSON:
{{"intent":"list_tasks","confidence":0.9,"entities":{{}},"clarification":null}}

User: "ضيف مهمة"
Assistant JSON:
{{"intent":"clarify","confidence":0.4,"entities":{{}},"clarification":"شو اسم المهمة؟"}}
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

    try:
        return chain.invoke(
            {
                "message": message,
                "format_instructions": _parser.get_format_instructions(),
            }
        )
    except Exception as e:
        # Log the error and return a clarify intent
        import traceback
        error_msg = str(e)
        
        # Check for API key errors - reset chain to force reload on next call
        if "API key" in error_msg or "API_KEY" in error_msg or "expired" in error_msg.lower() or "INVALID_ARGUMENT" in error_msg:
            global _chain
            _chain = None  # Reset chain to force reload with new settings
            # Reload settings from .env file
            from app.config import load_settings
            import app.config
            app.config.settings = load_settings()
            clarification_msg = "مفتاح API منتهي الصلاحية أو غير صحيح. يرجى تحديث المفتاح في ملف .env وإعادة المحاولة"
        else:
            clarification_msg = "حدث خطأ في معالجة الرسالة. حاول مرة أخرى."
        
        traceback.print_exc()
        return IntentResult(
            intent="clarify",
            confidence=0.0,
            entities={"raw": message, "error": error_msg},
            clarification=clarification_msg,
        )
