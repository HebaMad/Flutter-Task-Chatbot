from dataclasses import dataclass

from fastapi.testclient import TestClient
from app.main import app

import app.routes.chat as chat_route
from app.domain.tasks import TaskStore

client = TestClient(app)

VALID_BODY = {
    "userId": "u1",
    "message": "hello",
    "timezone": "Asia/Hebron",
    "dialect": "pal",
}

@dataclass
class FakeIntentResult:
    intent: str
    entities: dict

def _auth_headers():
    return {"Authorization": "Bearer x"}

def _reset_store(monkeypatch):
    monkeypatch.setattr(chat_route, "store", TaskStore())

def test_day7_update_without_id_multiple_candidates(monkeypatch):
    _reset_store(monkeypatch)
    # Seed tasks
    chat_route.store.create_task("u1", "اجتماع الفريق", None)
    chat_route.store.create_task("u1", "اجتماع العميل", None)

    def fake_interpret(_message: str):
        return FakeIntentResult(intent="update_task", entities={"taskRef": {"title": "اجتماع"}, "title": "اجتماع (محدث)"})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret)

    r = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r.status_code == 200
    body = r.json()
    action = body["actions"][0]
    print("ACTION:", action)
    print("ACTION_PAYLOAD:", action.get("payload"))
    print("ACTION_CANDS:", (action.get("payload") or {}).get("candidates"))
    print("BODY_CANDS:", body.get("candidates"))


    assert body["needsClarification"] is True
    assert body["actions"][0]["type"] == "clarify"
    assert len(body["candidates"]) == 2

def test_delete_without_id_single_match_executes(monkeypatch):
    _reset_store(monkeypatch)
    t = chat_route.store.create_task("u1", "اشتري حليب", None)

    def fake_interpret(_message: str):
        return FakeIntentResult(intent="delete_task", entities={"taskRef": {"title": "حليب"}})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret)

    r = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r.status_code == 200
    action = r.json()["actions"][0]
    assert action["type"] == "delete_task"
    assert action["payload"]["ok"] is True
    # confirm removed
    assert chat_route.store.get_task("u1", t.id) is None
