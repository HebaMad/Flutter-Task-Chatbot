from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.types import ErrorResponse, ErrorBody
from app.i18n.messages import msg


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _get_dialect(request: Request) -> str:
    return getattr(request.state, "dialect", "pal")


def json_error(request: Request, status_code: int, code: str, message_key: str) -> JSONResponse:
    request_id = _get_request_id(request)
    dialect = _get_dialect(request)

    payload = ErrorResponse(
        error=ErrorBody(
            code=code,  # type: ignore
            message=msg(dialect, message_key),
            requestId=request_id,
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    # Do not leak internal validation details; use localized message
    return json_error(request, 400, "invalid_request", "ERR_INVALID_REQUEST")


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return json_error(request, 500, "internal_error", "ERR_INTERNAL")
