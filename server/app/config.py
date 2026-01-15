from __future__ import annotations

import os
from pydantic import BaseModel


class Settings(BaseModel):
    # General
    app_name: str = "AI Tasks Chatbot"
    default_dialect: str = "pal"

    # Gemini (Google AI Studio)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"


def load_settings() -> Settings:
    """
    Gemini Developer API:
    - GOOGLE_API_KEY is preferred
    - GEMINI_API_KEY is accepted as fallback
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    return Settings(
        gemini_api_key=api_key,
        gemini_model=model,
    )


settings = load_settings()
