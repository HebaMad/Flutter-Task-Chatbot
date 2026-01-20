from dataclasses import dataclass

import app.routes.chat as chat_route
from app.domain.tasks import TaskStore
from fastapi.testclient import TestClient
from app.main import app

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
    # chat.py عندكم فيه store global
    monkeypatch.setattr(chat_route, "store", TaskStore())


def test_day6_create_task_action(monkeypatch):
    _reset_store(monkeypatch)

    def fake_interpret(_message: str):
        return FakeIntentResult(
            intent="create_task",
            entities={"title": "Buy milk", "due_text": "tomorrow 6pm"},
        )

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret)

    r = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r.status_code == 200

    body = r.json()
    assert body["actions"][0]["type"] == "create_task"
    assert "task" in body["actions"][0]["payload"]
    assert body["actions"][0]["payload"]["task"]["title"] == "Buy milk"


def test_day6_list_tasks_after_create(monkeypatch):
    _reset_store(monkeypatch)

    def fake_interpret_create(_message: str):
        return FakeIntentResult(
            intent="create_task",
            entities={"title": "Task 1", "due_text": None},
        )

    def fake_interpret_list(_message: str):
        return FakeIntentResult(intent="list_tasks", entities={})

    # 1) create
    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_create)
    r1 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r1.status_code == 200

    # 2) list
    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_list)
    r2 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r2.status_code == 200

    body = r2.json()
    assert body["actions"][0]["type"] == "list_tasks"
    tasks = body["actions"][0]["payload"]["tasks"]
    assert isinstance(tasks, list)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task 1"


def test_day6_update_task_changes_fields(monkeypatch):
    _reset_store(monkeypatch)

    # 1) create first task
    def fake_interpret_create(_message: str):
        return FakeIntentResult(
            intent="create_task",
            entities={"title": "Old title", "due_text": "today"},
        )

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_create)
    r1 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r1.status_code == 200
    created_task = r1.json()["actions"][0]["payload"]["task"]
    task_id = created_task["id"]

    # 2) update it
    def fake_interpret_update(_message: str):
        return FakeIntentResult(
            intent="update_task",
            entities={"task_id": task_id, "title": "New title", "due_text": "tomorrow"},
        )

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_update)
    r2 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r2.status_code == 200

    action = r2.json()["actions"][0]
    assert action["type"] == "update_task"
    assert action["payload"]["ok"] is True
    assert action["payload"]["task"]["id"] == task_id
    assert action["payload"]["task"]["title"] == "New title"
    assert action["payload"]["task"]["due_text"] == "tomorrow"


def test_day6_delete_task_removes_it(monkeypatch):
    _reset_store(monkeypatch)

    # 1) create
    def fake_interpret_create(_message: str):
        return FakeIntentResult(intent="create_task", entities={"title": "To delete", "due_text": None})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_create)
    r1 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r1.status_code == 200
    task_id = r1.json()["actions"][0]["payload"]["task"]["id"]

    # 2) delete
    def fake_interpret_delete(_message: str):
        return FakeIntentResult(intent="delete_task", entities={"task_id": task_id})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_delete)
    r2 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r2.status_code == 200
    action2 = r2.json()["actions"][0]
    assert action2["type"] == "delete_task"
    assert action2["payload"]["ok"] is True
    assert action2["payload"]["task_id"] == task_id

    # 3) list -> should be empty
    def fake_interpret_list(_message: str):
        return FakeIntentResult(intent="list_tasks", entities={})

    monkeypatch.setattr(chat_route, "interpret_intent_with_langchain", fake_interpret_list)
    r3 = client.post("/v1/chat", headers=_auth_headers(), json=VALID_BODY)
    assert r3.status_code == 200
    tasks = r3.json()["actions"][0]["payload"]["tasks"]
    assert tasks == []
