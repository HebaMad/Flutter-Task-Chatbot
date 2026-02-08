from fastapi import APIRouter
from app.settings import settings
from app.routes import chat

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/v1/health")
def health_v1():
    return {
        "ok": True,
        "version": "1.0.0",
        "llm_enabled": bool(settings.gemini_api_key) and not settings.mock_llm,
    }

@router.get("/v1/debug/last-error")
def last_error():
    return chat.LAST_ERROR or {"ok": True}
