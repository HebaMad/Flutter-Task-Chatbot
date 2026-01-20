from dataclasses import dataclass

from fastapi.testclient import TestClient
from app.main import app

import app.routes.chat as chat_route
from app.domain.tasks import TaskStore
import inspect

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
    s = TaskStore()
    monkeypatch.setattr(chat_route, "store", s)
    return s

def test_day7_complete_task_by_id(monkeypatch):
    store = _reset_store(monkeypatch)
    t = store.create_task("u1", "مهمة للتجربة", None)

    def fake_interpret(_message: str):
        return FakeIntentResult(intent="complete_task", entities={"task_id": t.id})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret)

    r = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r.status_code == 200
    body = r.json()

    import inspect
    src = inspect.getsource(chat_route.execute_intent)
    print("HAS complete_task BRANCH?", 'intent == "complete_task"' in src)
    print(src)




    print("EXECUTE_INTENT FILE:", inspect.getsourcefile(chat_route.execute_intent))
    print("EXECUTE_INTENT MODULE:", chat_route.execute_intent.__module__)
    print("ACTION:", body["actions"][0])

    assert body["actions"][0]["type"] == "complete_task"
    assert body["actions"][0]["payload"]["ok"] is True
    assert body["actions"][0]["payload"]["task"]["completed"] is True

def test_day7_complete_task_without_id_multiple_candidates(monkeypatch):
    store = _reset_store(monkeypatch)
    store.create_task("u1", "قراءة كتاب", None)
    store.create_task("u1", "قراءة مقال", None)

    def fake_interpret(_message: str):
        return FakeIntentResult(intent="complete_task", entities={"taskRef": {"title": "قراءة"}})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret)

    r = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["needsClarification"] is True
    assert body["actions"][0]["type"] == "clarify"
    assert len(body["candidates"]) == 2
    assert "taskId" in body["candidates"][0]
