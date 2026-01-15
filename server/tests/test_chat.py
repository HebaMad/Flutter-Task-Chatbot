from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

VALID_BODY = {
    "userId": "u1",
    "message": "hello",
    "timezone": "Asia/Hebron",
    "dialect": "pal",
}

def test_chat_unauthorized():
    r = client.post("/v1/chat", json=VALID_BODY)
    assert r.status_code == 401
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "unauthorized"
    assert "requestId" in body["error"]
    assert isinstance(body["error"]["message"], str)

def test_chat_invalid_request_missing_fields():
    r = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer x"},
        json={"userId": "u1", "message": "hello"}  # missing timezone
    )
    assert r.status_code in (400, 422)
    body = r.json()
    # If unified handler -> error shape
    if "error" in body:
        assert body["error"]["code"] == "invalid_request"
        assert "requestId" in body["error"]

def test_chat_success_pal_reply():
    r = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer x"},
        json=VALID_BODY
    )
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body
    assert "requestId" in body
    assert body["needsClarification"] in (True, False)

def test_chat_dialect_changes_reply():
    r1 = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer x"},
        json={**VALID_BODY, "dialect": "pal"}
    )
    r2 = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer x"},
        json={**VALID_BODY, "dialect": "egy"}
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["reply"] != r2.json()["reply"]
