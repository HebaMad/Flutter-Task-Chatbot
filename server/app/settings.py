from __future__ import annotations

import os
from pydantic import BaseModel

class Settings(BaseModel):
    # General
    app_name: str = "AI Tasks Chatbot"
    default_dialect: str = "pal"
    debug: bool = False

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    
    # Mock Mode (bypasses LLM)
    mock_llm: bool = False


def _env(name: str) -> str:
    v = os.getenv(name, "")
    return v.strip().lstrip("\ufeff")  # removes BOM if present


def load_settings() -> Settings:
    # Note: Environment loading is now handled strictly by app.config.env_loader in main.py
    # We do NOT load .env files here to avoid polluting the strict environment.
    
    gemini_key = _env("GOOGLE_API_KEY") or _env("GEMINI_API_KEY") or ""
    mock_llm = os.getenv("MOCK_LLM", "0").lower() in ("1", "true", "yes", "on")
    
    return Settings(
        gemini_api_key=gemini_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        mock_llm=mock_llm,
        debug=os.getenv("DEBUG", "0").lower() in ("1", "true", "yes", "on"),
    )


settings = load_settings()
