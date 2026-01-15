from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


Dialect = Literal["pal", "egy", "khg"]


class ChatRequest(BaseModel):
    userId: str
    message: str
    timezone: str
    conversationId: Optional[str] = None
    requestId: Optional[str] = None
    dialect: Dialect = "pal"


class BillingInfo(BaseModel):
    tokensSpent: int = 0
    balance: int = 0


class Candidate(BaseModel):
    taskId: str
    title: str
    dueAt: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    needsClarification: bool = False
    candidates: List[Candidate] = Field(default_factory=list)
    billing: BillingInfo = Field(default_factory=BillingInfo)
    requestId: str


class ErrorBody(BaseModel):
    code: Literal[
        "invalid_request",
        "unauthorized",
        "internal_error",
        "rate_limited",
        "insufficient_tokens",
    ]
    message: str
    requestId: str


class ErrorResponse(BaseModel):
    error: ErrorBody
