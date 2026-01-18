from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env specifically from the server folder
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"  # server/.env
load_dotenv(dotenv_path=str(ENV_PATH), override=True)


class Settings(BaseModel):
    # General
    app_name: str = "AI Tasks Chatbot"
    default_dialect: str = "pal"

    # Gemini (Google AI Studio)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"


def _env(name: str) -> str:
    v = os.getenv(name, "")
    return v.strip().lstrip("\ufeff")  # removes BOM if present


def load_settings() -> Settings:
    # Reload .env file to get latest values
    load_dotenv(dotenv_path=str(ENV_PATH), override=True)
    api_key = _env("GOOGLE_API_KEY") or _env("GEMINI_API_KEY") or ""
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return Settings(gemini_api_key=api_key, gemini_model=model)


settings = load_settings()
