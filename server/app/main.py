from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.routes.health import router as health_router
from app.routes.chat import router as chat_router
from app.middlewares.request_id import RequestIdMiddleware
from app.middlewares.auth import AuthMiddleware
from app.core.logging import log_middleware
from app.core.errors import (
    validation_exception_handler,
    unhandled_exception_handler,
)

app = FastAPI(title="AI Tasks Chatbot")

# --- Middlewares ---
app.add_middleware(RequestIdMiddleware)
app.add_middleware(AuthMiddleware)
app.middleware("http")(log_middleware)

# --- Routes ---
app.include_router(health_router)
app.include_router(chat_router)

# --- Error Handlers ---
@app.exception_handler(RequestValidationError)
async def fastapi_validation_handler(request, exc: RequestValidationError):
    # unify FastAPI 422 into our localized 400
    return validation_exception_handler(
        request, ValidationError.from_exception_data("ValidationError", [])
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request, exc: ValidationError):
    return validation_exception_handler(request, exc)


@app.exception_handler(Exception)
async def any_exception_handler(request, exc: Exception):
    return unhandled_exception_handler(request, exc)
