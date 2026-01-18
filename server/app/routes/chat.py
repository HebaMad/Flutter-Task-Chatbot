from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.types import ChatRequest, ChatResponse
from app.i18n.messages import msg
from app.llm.intent_chain import interpret_intent_with_langchain

router = APIRouter()


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    # store for logs + localized errors
    request.state.user_id = req.userId
    request.state.dialect = req.dialect

    # if client sends requestId, prefer it (over header-generated)
    if req.requestId:
        request.state.request_id = req.requestId

    rid = request.state.request_id

    # Day 3: interpret intent placeholder (Day 4 will become real LangChain)
    intent_result = interpret_intent_with_langchain(req.message)


    # Reply: stub (localized)
    reply_text = msg(req.dialect, "STUB_OK")

    # If clarify, return localized clarification prompt
    needs_clarify = intent_result.intent == "clarify"
    if needs_clarify:
        reply_text = msg(req.dialect, "AMBIGUOUS_PICK_ONE")

    return ChatResponse(
        reply=reply_text,
        actions=[],
        needsClarification=needs_clarify,
        candidates=[],
        billing={"tokensSpent": 0, "balance": 0},
        requestId=rid,
    )
