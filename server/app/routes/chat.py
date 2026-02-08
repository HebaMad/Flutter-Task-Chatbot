from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Request

from app.core.types import ChatRequest, ChatResponse
from app.domain.executor import execute_intent
from app.domain.reply_builder import build_reply
from app.domain.tasks import TaskStore
from app.domain import conversation_state
from app.utils.arabic_duration_parser import strip_duration_phrase, parse_duration_minutes, extract_duration_minutes_and_clean
from app.utils.arabic_time_parser import extract_due_datetime_and_clean
from app.llm.gemini_adapter import interpret_intent
from app.settings import settings

router = APIRouter()
store = TaskStore()
logger = logging.getLogger(__name__)

STRONG_MATCH_THRESHOLD = 0.80
MIN_MATCH_THRESHOLD = 0.65
DELETE_QUERY_PROMPT = "أي مهمة بدك تحذف؟ اكتب جزء من عنوانها."
NO_MATCH_PROMPT = "ما لقيت مهمة بهالكلمة. جرّب كلمة ثانية."
CANCEL_PROMPT = "تم الإلغاء."
LAST_ERROR = {}


def _detect_list_scope(message: str) -> tuple[str, str]:
    """Return (status, scope) based on message hints."""
    lower = message.lower()
    status = "todo"
    scope = "all"
    if "اليوم" in lower or "اليوم" in message:
        scope = "today"
    if "منجزة" in lower or "مخلصة" in lower or "منجّزة" in lower:
        status = "done"
    if "الكل" in lower or "الجميع" in lower:
        status = "all"
    return status, scope


def _is_yes(message: str) -> bool:
    lower = message.strip().lower()
    return lower in {"نعم", "اي", "أيوه", "ايوه", "ايوة", "أيوة", "yes", "تمام", "اكيد", "أكيد", "طبعا", "طبعاً"}


def _is_no(message: str) -> bool:
    lower = message.strip().lower()
    return lower in {"لا", "لاء", "مش", "cancel", "إلغاء", "الغاء", "لا بلاش", "مو"}


def _is_cancel(message: str) -> bool:
    return _is_no(message)


def _parse_choice(message: str, max_n: int) -> int | None:
    import re

    match = re.search(r"(\d+)", message)
    if not match:
        return None
    idx = int(match.group(1))
    return idx if 1 <= idx <= max_n else None


def _score_candidates(user_id: str, query: str):
    matches = store.fuzzy_search_tasks(user_id, query, limit=5, status="all", scope="all")
    candidates = []
    for task, sim, overlap in matches:
        if sim < MIN_MATCH_THRESHOLD and overlap < 1:
            continue
        candidates.append({"taskId": task.id, "title": task.title, "score": round(sim, 3)})
    return candidates


def _format_candidates_message(candidates):
    lines = ["لقيت أكثر من مهمة. اختاري رقم:"]
    for idx, c in enumerate(candidates, start=1):
        lines.append(f"{idx}) {c['title']}")
    return "\n".join(lines)


def build_error_response(request_id: str, exc: Exception, error_code: str = "UNKNOWN"):
    meta = {"ok": False, "error_code": error_code}
    if settings.debug:
        meta["debug"] = {
            "exception": exc.__class__.__name__,
            "message": str(exc),
            "requestId": request_id,
        }
    safe_reply = "صار خطأ داخلي بسيط. جرّبي مرة ثانية."
    return {
        "reply": safe_reply,
        "actions": [{"type": "message", "payload": {"message": safe_reply}}],
        "needsClarification": False,
        "candidates": [],
        "billing": {"tokensSpent": 0, "balance": 0},
        "requestId": request_id,
        "meta": meta,
    }


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    dialect = "pal"  # fixed dialect for now
    request.state.user_id = req.userId
    request.state.dialect = dialect

    rid = req.requestId or getattr(request.state, "request_id", None) or ""

    conv_key = req.conversationId or req.requestId or req.userId
    state = conversation_state.get_state(conv_key)

    action = None
    debug_meta = {
        "llm_used": None,
        "model": settings.gemini_model,
        "attempted_keys": 0,
        "keys_count": 0,
        "used_key_index": -1,
        "tokens_source": None,
    }
    timezone = req.timezone or "UTC"
    try:
        import pytz

        now_iso = datetime.now(pytz.timezone(timezone)).isoformat()
    except Exception:
        now_iso = datetime.utcnow().isoformat()

    text_message = req.message.strip()

    def _parse_due_message(message: str):
        now_dt = datetime.fromisoformat(now_iso)
        due_dt, _ = extract_due_datetime_and_clean(message, timezone, now_dt)
        return due_dt

    def search_and_prompt(query: str):
        cands = _score_candidates(req.userId, query)
        if not cands:
            conversation_state.update_state(
                conv_key,
                mode="delete",
                step="ask_query",
                delete_query=None,
                candidates=[],
                selected_task_id=None,
            )
            return {"type": "clarify", "payload": {"message": NO_MATCH_PROMPT}}

        strong_single = len(cands) == 1 and cands[0]["score"] >= STRONG_MATCH_THRESHOLD
        if strong_single:
            sel = cands[0]
            conversation_state.update_state(
                conv_key,
                mode="delete",
                step="confirm",
                delete_query=query,
                candidates=[sel],
                selected_task_id=sel["taskId"],
            )
            return {
                "type": "clarify",
                "payload": {
                    "message": f"بدك أحذف: {sel['title']} ؟ (نعم/لا)",
                    "candidates": [sel],
                    "needsConfirmation": True,
                },
            }

        conversation_state.update_state(
            conv_key,
            mode="delete",
            step="show_candidates",
            delete_query=query,
            candidates=cands,
            selected_task_id=None,
        )
        return {
            "type": "clarify",
            "payload": {"message": _format_candidates_message(cands), "candidates": cands},
        }

    def handle_delete_flow(user_message: str):
        if _is_cancel(user_message):
            conversation_state.clear_delete_state(conv_key)
            return {"type": "clarify", "payload": {"message": CANCEL_PROMPT}}

        if state.step in (None, "ask_query"):
            return search_and_prompt(user_message)

        if state.step == "show_candidates":
            import re
            cleaned = re.sub(r"^اختيار\s*[:：]?\s*", "", user_message.strip(), flags=re.IGNORECASE)
            choice = _parse_choice(cleaned, len(state.candidates or []))
            selected = None
            if choice:
                selected = (state.candidates or [])[choice - 1]
            else:
                # direct title/text match among current candidates only
                for cand in state.candidates or []:
                    if cleaned.lower() == cand.get("title", "").lower():
                        selected = cand
                        break
            if selected:
                conversation_state.update_state(
                    conv_key,
                    mode="delete",
                    step="confirm",
                    selected_task_id=selected.get("taskId"),
                    candidates=[selected],
                )
                return {
                    "type": "clarify",
                    "payload": {
                        "message": f"بدك أحذف: {selected.get('title', '')} ؟ (نعم/لا)",
                        "candidates": [selected],
                        "needsConfirmation": True,
                    },
                }
            # no match, repeat options once
            return {
                "type": "clarify",
                "payload": {"message": _format_candidates_message(state.candidates), "candidates": state.candidates},
            }

        if state.step == "confirm":
            if _is_yes(user_message):
                task_id = state.selected_task_id
                if task_id:
                    action_del = execute_intent(
                        store=store,
                        user_id=req.userId,
                        intent="delete_task",
                        entities={"task_id": task_id, "confirmed": True},
                    )
                else:
                    action_del = {"type": "clarify", "payload": {"message": DELETE_QUERY_PROMPT}}
                conversation_state.clear_delete_state(conv_key)
                return action_del
            if _is_no(user_message):
                conversation_state.clear_delete_state(conv_key)
                return {"type": "clarify", "payload": {"message": CANCEL_PROMPT}}
            return {"type": "clarify", "payload": {"message": "بس أكد: نعم أو لا"}}

        conversation_state.clear_delete_state(conv_key)
        return {"type": "clarify", "payload": {"message": DELETE_QUERY_PROMPT}}

    try:
        # ---- 1) Handle ongoing delete flow ----
        pending_op = getattr(state, "pending_op", {}) or {}
        if pending_op.get("type") == "delete_task":
            stage = pending_op.get("stage") or state.step
            candidates_state = pending_op.get("candidates") or state.candidates or []

            def set_pending(stage, candidates=None, selected=None, query=None):
                conversation_state.set_delete_pending(
                    conv_key,
                    candidates=candidates or candidates_state,
                    stage=stage,
                    selected=selected,
                    query=query or pending_op.get("query"),
                )

            if stage in (None, "awaiting_query", "ask_query"):
                # treat current message as query
                cands = _score_candidates(req.userId, text_message)
                if not cands:
                    set_pending("awaiting_query", [])
                    action = {
                        "type": "clarify",
                        "payload": {"message": "ما لقيت مهمة مشابهة… اكتب كلمة أدق من العنوان"},
                    }
                elif len(cands) == 1 and cands[0]["score"] >= STRONG_MATCH_THRESHOLD:
                    sel = cands[0]
                    set_pending("awaiting_confirm", [sel], sel["taskId"], text_message)
                    action = {
                        "type": "clarify",
                        "payload": {"message": f"تأكيد: أحذف مهمة '{sel['title']}'؟ (نعم/لا)", "candidates": [sel]},
                    }
                else:
                    set_pending("awaiting_choice", cands, query=text_message)
                    action = {
                        "type": "clarify",
                        "payload": {"message": _format_candidates_message(cands), "candidates": cands},
                    }
                debug_meta.update({"llm_used": "delete_flow", "stage": "awaiting_query"})

            elif stage == "awaiting_choice":
                import re

                cleaned = re.sub(r"^اختيار\s*[:：]?\s*", "", text_message.strip(), flags=re.IGNORECASE)
                choice = _parse_choice(cleaned, len(candidates_state))
                selected = None
                if choice:
                    selected = candidates_state[choice - 1]
                else:
                    for cand in candidates_state:
                        if cleaned.lower() in cand.get("title", "").lower():
                            selected = cand
                            break
                if selected:
                    set_pending("awaiting_confirm", [selected], selected.get("taskId"))
                    action = {
                        "type": "clarify",
                        "payload": {
                            "message": f"تأكيد: أحذف مهمة '{selected.get('title','')}'؟ (نعم/لا)",
                            "candidates": [selected],
                        },
                    }
                else:
                    # repeat once
                    set_pending("awaiting_choice", candidates_state)
                    action = {
                        "type": "clarify",
                        "payload": {"message": _format_candidates_message(candidates_state), "candidates": candidates_state},
                    }
                debug_meta.update({"llm_used": "delete_flow", "stage": "awaiting_choice"})

            elif stage == "awaiting_confirm":
                if _is_yes(text_message):
                    task_id = pending_op.get("selected_task_id") or state.selected_task_id
                    if task_id:
                        action = execute_intent(
                            store=store,
                            user_id=req.userId,
                            intent="delete_task",
                            entities={"task_id": task_id, "confirmed": True},
                        )
                        # include title if we have it
                        if pending_op.get("candidates"):
                            action.setdefault("payload", {})["title"] = pending_op["candidates"][0].get("title")
                    else:
                        action = {"type": "clarify", "payload": {"message": DELETE_QUERY_PROMPT}}
                    conversation_state.clear_delete_state(conv_key)
                elif _is_no(text_message):
                    conversation_state.clear_delete_state(conv_key)
                    action = {"type": "clarify", "payload": {"message": CANCEL_PROMPT}}
                else:
                    action = {"type": "clarify", "payload": {"message": "بس جاوب نعم أو لا للتأكيد"}}
                debug_meta.update({"llm_used": "delete_flow", "stage": "awaiting_confirm"})

        # ---- 2) Handle pending clarification (legacy create) ----
        if not action and state.pending and state.pending_intent == "create_task":
            if state.expected_field == "dueAt":
                parsed_due_dt = _parse_due_message(text_message)
                if parsed_due_dt is None:
                    action = {"type": "clarify", "payload": {"message": state.entities.get("clarify_question") or "تمام—إمتى بدك أذكّرك؟"}}
                else:
                    entities = state.entities.copy()
                    try:
                        entities["due_at"] = int(parsed_due_dt.timestamp())
                    except Exception:
                        entities["due_at"] = None
                    action = execute_intent(
                        store=store,
                        user_id=req.userId,
                        intent="create_task",
                        entities=entities,
                    )
                    conversation_state.clear_state(conv_key)
                debug_meta.update({"llm_used": "pending_followup", "tokens_source": "none"})

        # ---- 3) Fresh message -> LLM + fallback rule extractor ----
        if not action:
            intent_result, debug_meta = interpret_intent(req.message, timezone, now_iso)

            if intent_result.intent == "delete_task":
                # initialize pending
                conversation_state.set_delete_pending(conv_key, stage="awaiting_query")
                query = (intent_result.title_query or "").strip()
                if not query:
                    action = {
                        "type": "clarify",
                        "payload": {"message": intent_result.clarify_question or DELETE_QUERY_PROMPT},
                    }
                else:
                    cands = _score_candidates(req.userId, query)
                    if not cands:
                        conversation_state.set_delete_pending(conv_key, stage="awaiting_query", candidates=[])
                        action = {
                            "type": "clarify",
                            "payload": {"message": "ما لقيت مهمة مشابهة… اكتب كلمة أدق من العنوان"},
                        }
                    elif len(cands) == 1 and cands[0]["score"] >= STRONG_MATCH_THRESHOLD:
                        sel = cands[0]
                        conversation_state.set_delete_pending(conv_key, stage="awaiting_confirm", candidates=[sel], selected=sel["taskId"], query=query)
                        action = {
                            "type": "clarify",
                            "payload": {"message": f"تأكيد: أحذف مهمة '{sel['title']}'؟ (نعم/لا)", "candidates": [sel]},
                        }
                    else:
                        conversation_state.set_delete_pending(conv_key, stage="awaiting_choice", candidates=cands, query=query)
                        action = {
                            "type": "clarify",
                            "payload": {"message": _format_candidates_message(cands), "candidates": cands},
                        }

            elif intent_result.intent == "create_task":
                raw_title = (intent_result.title or intent_result.title_query or "").strip()
                duration_minutes, after_duration = extract_duration_minutes_and_clean(raw_title)
                now_dt = datetime.fromisoformat(now_iso)
                due_dt, cleaned_title = extract_due_datetime_and_clean(after_duration, timezone, now_dt)
                title = cleaned_title
                if not title:
                    action = {"type": "clarify", "payload": {"key": "clarify_missing_title"}}
                else:
                    entities = {"title": title}
                    if due_dt:
                        try:
                            entities["due_at"] = int(due_dt.timestamp())
                        except Exception:
                            entities["due_at"] = None
                    if duration_minutes is not None:
                        entities["duration_minutes"] = duration_minutes

                    action = execute_intent(
                        store=store,
                        user_id=req.userId,
                        intent="create_task",
                        entities=entities,
                    )
                    conversation_state.clear_state(conv_key)

            elif intent_result.intent == "list_tasks":
                status, scope = _detect_list_scope(req.message)
                entities = {"status": status, "scope": scope, "timezone": timezone}
                action = execute_intent(
                    store=store,
                    user_id=req.userId,
                    intent="list_tasks",
                    entities=entities,
                )

            elif intent_result.intent == "update_task":
                action = execute_intent(
                    store=store,
                    user_id=req.userId,
                    intent="update_task",
                    entities={"task_title": intent_result.title_query},
                )

            else:
                msg = intent_result.clarify_question or "ممكن توضح أكثر؟"
                action = {"type": "clarify", "payload": {"message": msg}}

        # ---- 4) Finalize response ----
        reply = build_reply(action, dialect)
        needs_clarification = action.get("type") == "clarify"
        payload = action.get("payload") or {}
        candidates = [
            {
                "taskId": c.get("taskId") or c.get("id"),
                "title": c.get("title", ""),
                "score": c.get("score"),
            }
            for c in (payload.get("candidates", []) if needs_clarification else [])
            if (c.get("taskId") or c.get("id"))
        ]

        meta = debug_meta or {}

        logging.info(
            f"REQ:{rid} intent:{debug_meta.get('llm_used')} action:{action.get('type')}"
        )

        return {
            "reply": reply,
            "actions": [action],
            "needsClarification": needs_clarification,
            "candidates": candidates,
            "billing": {"tokensSpent": 0, "balance": 0},
            "requestId": rid,
            "meta": {**meta, "ok": True},
        }

    except Exception as exc:
        error_code = "UNKNOWN"
        LAST_ERROR.update({
            "ok": False,
            "error_code": error_code,
            "error_message": str(exc),
            "exception_class": exc.__class__.__name__,
            "requestId": rid,
        })
        logging.error(f"Chat handler error rid={rid}: {exc}", exc_info=True)
        return build_error_response(rid, exc, error_code)
