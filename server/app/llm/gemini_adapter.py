from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Literal, Optional, Tuple
import re

from pydantic import BaseModel, Field, validator
from google import genai
from google.genai import types

from app.settings import settings
from app.llm.gemini_keypool import GeminiKeyPool
from app.utils.arabic_duration_parser import parse_duration_minutes, strip_duration_phrase, extract_duration_minutes_and_clean
from app.utils.arabic_time_parser import extract_due_datetime_and_clean

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Data Models (structured output)
# ---------------------------------------------------------

Intent = Literal["create_task", "list_tasks", "update_task", "delete_task", "chat"]


class Due(BaseModel):
    kind: Literal["resolved", "missing", "none"] = "none"
    iso: Optional[str] = None
    confidence: float = 0.0


class IntentResult(BaseModel):
    intent: Intent
    title: Optional[str] = None
    due: Due = Field(default_factory=Due)
    duration_minutes: Optional[int] = Field(default=None, alias="duration_minutes")
    needs_clarification: bool = Field(default=False, alias="needsClarification")
    clarify_question: Optional[str] = Field(default=None, alias="clarifyQuestion")
    # delete flow extras
    title_query: Optional[str] = Field(default=None, alias="titleQuery")
    task_id: Optional[str] = Field(default=None, alias="taskId")
    needs_confirmation: bool = Field(default=False, alias="needsConfirmation")
    confirm_message: Optional[str] = Field(default=None, alias="confirmMessage")
    confidence: float = 0.0

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @validator("title", "title_query", pre=True)
    def _strip_title(cls, v):
        return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------
# System Prompt
# ---------------------------------------------------------

_SYSTEM_PROMPT = """
أنت محلل نوايا لتطبيق مهام.
أعد ONLY JSON مطابق للمخطط أدناه بدون أي نص زائد.

SCHEMA:
{
  "intent": "create_task" | "list_tasks" | "update_task" | "delete_task" | "chat",
  "title": string|null,
  "due": { "kind": "resolved" | "missing" | "none", "iso": string|null, "confidence": number },
  "duration_minutes": number|null,
  "needsClarification": boolean,
  "clarifyQuestion": string|null,
  "titleQuery": string|null,
  "taskId": string|null,
  "needsConfirmation": boolean,
  "confirmMessage": string|null
}

قواعد:
- عبارات المدة (لمدة/مدة/مدتها/مدته/فترة) تُحوَّل إلى duration_minutes فقط ولا تعتبر موعداً.
- عبارات الزمن/الموعد (اليوم، بكرة، بعد ساعتين، بعد أسبوع، الساعة 6...) تخص due فقط.
- “بعد أسبوع” = موعد نسبي (due) وليس مدة. “لمدة أسبوع” = مدة فقط.
- إذا لم يذكر وقت إطلاقاً → due.kind="none" ولا تطلب توضيح.
- إذا ذكر اليوم بلا وقت واضح → due.kind="missing" و needsClarification=true مع سؤال واحد قصير.
- مع أفعال الحذف (احذف/شيل/امسح/حذف/الغِ) حدد intent="delete_task" ولا تعيد create_task.
- لا تُدخل المدة في العنوان؛ اجعل العنوان مختصراً وواضحاً (<=60 حرف) بلا أوامر.
- الرد يجب أن يكون JSON فقط.
""".strip()


# ---------------------------------------------------------
# KeyPool init
# ---------------------------------------------------------
_key_pool: Optional[GeminiKeyPool] = None
try:
    _key_pool = GeminiKeyPool.from_env()
except Exception as e:
    logger.warning(f"Failed to initialize GeminiKeyPool: {e}. Gemini calls will likely fail.")

_AVAILABLE_MODELS: list[str] = []


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _response_schema() -> Dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "intent": {
                "type": "STRING",
                "enum": ["create_task", "list_tasks", "update_task", "delete_task", "chat"],
            },
            "title": {"type": "STRING", "nullable": True},
            "due": {
                "type": "OBJECT",
                "properties": {
                    "kind": {"type": "STRING", "enum": ["resolved", "missing", "none"]},
                    "iso": {"type": "STRING", "nullable": True},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["kind", "confidence"],
            },
            "duration_minutes": {"type": "NUMBER", "nullable": True},
            "needsClarification": {"type": "BOOLEAN"},
            "clarifyQuestion": {"type": "STRING", "nullable": True},
            "titleQuery": {"type": "STRING", "nullable": True},
            "taskId": {"type": "STRING", "nullable": True},
            "needsConfirmation": {"type": "BOOLEAN"},
            "confirmMessage": {"type": "STRING", "nullable": True},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["intent", "needsClarification", "needsConfirmation", "confidence"],
    }


def _list_models(api_key: str) -> list[str]:
    try:
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        names = [m.name for m in models if getattr(m, "supported_generation_methods", None)]
        return names
    except Exception as e:
        logger.error(f"List models failed: {e}")
        return []


def _extract_title_hint(text: str) -> Optional[str]:
    import re

    hint = (text or "").strip()
    lead_patterns = [
        r"^احذف\s*",
        r"^أحذف\s*",
        r"^حذف\s*",
        r"^امسح\s*",
        r"^شيل\s*",
        r"^اشطب\s*",
        r"^الغ\s*",
        r"^ألغي\s*",
        r"^بدي\s+",
        r"^بدّي\s+",
        r"^ذكّرني\s+ب?\s*",
        r"^ذكرني\s+ب?\s*",
        r"^لازم\s+",
        r"^مهمة\s*[:\-]?\s*",
        r"^موعد\s*[:\-]?\s*",
    ]
    for pat in lead_patterns:
        hint = re.sub(pat, "", hint, flags=re.IGNORECASE).strip()
    if len(hint) > 60:
        hint = hint[:60].strip()
    return hint or None


def _iso_from_ts(ts: int, timezone: str) -> str:
    try:
        import pytz

        tz = pytz.timezone(timezone)
    except Exception:
        tz = None
    dt = datetime.fromtimestamp(ts, tz) if tz else datetime.fromtimestamp(ts)
    return dt.isoformat()


def _clean_title(text: str) -> str:
    if not text:
        return ""
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        due_dt, cleaned = extract_due_datetime_and_clean(text, "UTC", now)
        duration, cleaned = extract_duration_minutes_and_clean(cleaned)
        cleaned = _extract_title_hint(cleaned) or cleaned
        prefixes = ["بدي", "بدّي", "أضف", "ضيف", "اضف", "سجل", "سجلي", "اعمل", "خلينا", "مهمة", "task", "لو سمحت", "ممكن"]
        for p in prefixes:
            cleaned = re.sub(rf"^{re.escape(p)}\\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\\s+", " ", cleaned).strip(" -،،,:")
        if len(cleaned) > 60:
            cleaned = cleaned[:60].strip()
        return cleaned
    except Exception:
        return text.strip()


def rule_based_extract(message: str, timezone: str) -> IntentResult:
    """
    Lightweight Arabic heuristic extractor used when Gemini is unavailable.
    """
    text = message.strip()
    lower = text.lower()

    delete_triggers = ["احذف", "حذف", "امسح", "شيل", "اشطب", "الغ", "إلغاء مهمة", "delete", "remove"]
    create_triggers = ["بدي", "بدّي", "ذكرني", "ذكّرني", "ذكّر", "ذكر", "لازم", "مهمة", "موعد", "تذكير", "حجز", "اضف", "ضيف", "سجل", "create", "add"]
    list_triggers = ["مهامي", "شو مهامي", "اعرض المهام", "ورجيني مهامي", "ما هي المهام", "شو عندي"]

    # Duration detection and clean title
    duration_minutes, cleaned_after_duration = extract_duration_minutes_and_clean(text)

    # Due extraction
    from datetime import timezone as _tz
    now = datetime.now(_tz.utc)
    due_dt, cleaned_title = extract_due_datetime_and_clean(cleaned_after_duration, timezone, now)

    # Delete intent first to avoid misclassification
    if any(k in lower for k in delete_triggers):
        query = _extract_title_hint(text)
        needs_clarify = not bool(query)
        confirm_msg = f"بدك أحذف: {query} ؟ (نعم/لا)" if query else None
        return IntentResult(
            intent="delete_task",
            title_query=query or None,
            needs_clarification=needs_clarify,
            clarify_question="أكيد—أي مهمة بدك تحذف؟ اكتب كلمة من عنوانها." if needs_clarify else None,
            needs_confirmation=bool(query),
            confirm_message=confirm_msg,
            confidence=0.62,
        )

    # Detect list intent
    if any(k in lower for k in list_triggers):
        return IntentResult(
            intent="list_tasks",
            title=None,
            due=Due(kind="none", iso=None, confidence=0.0),
            duration_minutes=duration_minutes,
            needs_clarification=False,
            clarify_question=None,
            needs_confirmation=False,
            confidence=0.5,
        )

    # Detect create intent
    is_create = any(k in lower for k in create_triggers) or bool(duration_minutes) or bool(due_dt)
    intent = "create_task" if is_create else "chat"

    title = _clean_title(cleaned_title if intent == "create_task" else text) if intent == "create_task" else None

    # Time detection for due using extracted due_dt
    due_kind = "none"
    due_iso = None
    due_conf = 0.0
    if due_dt:
        due_kind = "resolved"
        due_iso = due_dt.isoformat()
        due_conf = 0.6
    else:
        import re
        has_day_word = bool(re.search(r"اليوم|بكرة|غدا|غداً|بعد بكرة|لبكرة", lower))
        has_time = bool(re.search(r"الساعة|صباح|مساء|am|pm|:\\d", lower))
        if has_day_word and not has_time:
            due_kind = "missing"

    needs_clarify = intent == "create_task" and due_kind == "missing"
    clarify_question = "تمام—إمتى بدك أذكّرك؟" if needs_clarify else None

    return IntentResult(
        intent=intent,
        title=title or None,
        due=Due(kind=due_kind, iso=due_iso, confidence=due_conf),
        duration_minutes=duration_minutes,
        needs_clarification=needs_clarify,
        clarify_question=clarify_question,
        needs_confirmation=False,
        confidence=0.45 if intent == "create_task" else 0.3,
    )


# ---------------------------------------------------------
# Main interpret function
# ---------------------------------------------------------

def interpret_intent(message: str, timezone: str, now_iso: str) -> Tuple[IntentResult, Dict[str, Any]]:
    """
    Interpret intent using Gemini with structured output; falls back to rule-based extractor.
    Returns (IntentResult, debug_meta)
    """
    debug_meta = {
        "llm_used": "gemini",
        "model": settings.gemini_model,
        "keys_count": len(_key_pool.keys) if _key_pool else 0,
        "attempted_keys": 0,
        "used_key_index": -1,
        "last_error_type": None,
        "last_error_message": None,
        "tokens_source": "gemini",
    }

    if not _key_pool:
        res = rule_based_extract(message, timezone)
        debug_meta.update({
            "llm_used": "fallback_rule",
            "tokens_source": "rule_based",
        })
        return res, debug_meta

    max_attempts = len(_key_pool.keys)
    attempts = 0
    last_error = None
    schema = _response_schema()

    model_to_use = settings.gemini_model

    while attempts < max_attempts:
        attempts += 1
        key = _key_pool.next_key()
        debug_meta["attempted_keys"] = attempts

        try:
            key_index = _key_pool.keys.index(key)
        except ValueError:
            key_index = -1

        try:
            client = genai.Client(api_key=key)
            # Validate model availability once per attempt
            global _AVAILABLE_MODELS
            if not _AVAILABLE_MODELS:
                _AVAILABLE_MODELS = _list_models(key)
            if model_to_use not in _AVAILABLE_MODELS and _AVAILABLE_MODELS:
                # fallback to a flash-like model if present
                fallback = next((m for m in _AVAILABLE_MODELS if "flash" in m), _AVAILABLE_MODELS[0])
                debug_meta["model_substitution"] = {"from": model_to_use, "to": fallback}
                model_to_use = fallback

            payload = f"tz={timezone}\nnow={now_iso}\nmessage: {message}"
            response = client.models.generate_content(
                model=model_to_use,
                contents=payload,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.1,
                    top_p=0.7,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )

            if not response.text:
                raise ValueError("Empty response from Gemini")

            data = json.loads(response.text)
            result = IntentResult(**data)
            debug_meta["used_key_index"] = key_index
            return result, debug_meta

        except Exception as e:
            last_error = e
            err_msg = str(e).lower()
            if "not found" in err_msg and "model" in err_msg:
                debug_meta["last_error_type"] = "model_not_found"
                debug_meta["last_error_message"] = str(e)[:160]
                res = rule_based_extract(message, timezone)
                debug_meta.update({"llm_used": "fallback_rule", "tokens_source": "rule_based"})
                # Surface issue only in debug metadata; don't force clarification on the user
                return res, debug_meta
            is_retryable = any(
                k in err_msg
                for k in (
                    "429",
                    "resource exhausted",
                    "503",
                    "service unavailable",
                    "internal server error",
                    "timed out",
                    "deadline exceeded",
                    "aborted",
                )
            )

            error_type = "unknown"
            if "429" in err_msg or "resource exhausted" in err_msg:
                error_type = "quota"
            elif "timed out" in err_msg or "deadline exceeded" in err_msg:
                error_type = "timeout"
            elif "401" in err_msg or "unauthorized" in err_msg:
                error_type = "auth"
            elif "invalid argument" in err_msg or "400" in err_msg:
                error_type = "client_error"

            debug_meta["last_error_type"] = error_type
            debug_meta["last_error_message"] = str(e)[:160]

            _key_pool.cool_down(key)
            if is_retryable:
                time.sleep(0.5)
                continue
            continue

    # All keys failed -> rule-based fallback
    logger.error(f"All Gemini attempts failed. Last error: {last_error}")
    res = rule_based_extract(message, timezone)
    debug_meta.update(
        {
            "llm_used": "fallback_rule",
            "tokens_source": "rule_based",
        }
    )
    return res, debug_meta
