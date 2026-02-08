from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Literal, List

@dataclass
class ConversationState:
    pending: bool = False
    pending_intent: Optional[str] = None
    expected_field: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    pending_op: Dict[str, Any] = field(default_factory=dict)  # e.g., delete_task flow
    # legacy delete fields (kept for backward compatibility)
    mode: Optional[str] = None
    step: Optional[str] = None
    delete_query: Optional[str] = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected_task_id: Optional[str] = None

# In-memory store
_store: Dict[str, ConversationState] = {}

def get_state(key: str) -> ConversationState:
    # Cleanup old states (> 30 mins)
    now = time.time()
    if key in _store:
        if now - _store[key].created_at > 1800:
            del _store[key]
    
    if key not in _store:
        _store[key] = ConversationState()
    return _store[key]

def clear_state(key: str):
    if key in _store:
        del _store[key]

def update_state(key: str, **kwargs):
    state = get_state(key)
    for k, v in kwargs.items():
        if hasattr(state, k):
            setattr(state, k, v)
    state.created_at = time.time() # Refresh TTL


def clear_delete_state(key: str):
    state = get_state(key)
    state.pending_op = {}
    state.mode = None
    state.step = None
    state.delete_query = None
    state.candidates = []
    state.selected_task_id = None
    state.created_at = time.time()


def set_delete_pending(key: str, *, candidates=None, stage="awaiting_query", selected=None, query=None):
    state = get_state(key)
    state.pending_op = {
        "type": "delete_task",
        "candidates": candidates or [],
        "stage": stage,
        "selected_task_id": selected,
        "query": query,
    }
    state.mode = "delete"
    state.step = stage
    state.candidates = candidates or []
    state.selected_task_id = selected
    state.delete_query = query
    state.created_at = time.time()
