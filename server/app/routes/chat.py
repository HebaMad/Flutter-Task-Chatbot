from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.types import ChatRequest, ChatResponse
from app.domain.executor import execute_intent
from app.domain.reply_builder import build_reply
from app.domain.tasks import TaskStore
from app.llm.intent_chain import interpret_intent_with_langchain

router = APIRouter()

# In-memory store (Day 5)
store = TaskStore()


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    # store for logs + localized errors
    request.state.user_id = req.userId
    request.state.dialect = req.dialect

    # if client sends requestId, prefer it
    if req.requestId:
        request.state.request_id = req.requestId

    # safe request id (works in tests too)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-Id") or ""

    # Interpret (LLM interprets)
    intent_result = interpret_intent_with_langchain(req.message)

    # Execute (Backend executes)
    action = execute_intent(
        store=store,
        user_id=req.userId,
        intent=intent_result.intent,
        entities=intent_result.entities,
    )

    # Reply (based on action)
    reply = build_reply(action, req.dialect)

    needs_clarification = (
        intent_result.intent == "clarify" or action.get("type") == "clarify"
    )

    return {
    "reply": reply,
    "actions": [action],          # ✅ List
    "needsClarification": needs_clarification,
    "candidates": [],             # ✅ List
    "billing": {
        "tokensSpent": 0,
        "balance": 0
    },
    "requestId": rid
}

