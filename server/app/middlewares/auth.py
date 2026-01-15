from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import json_error


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Protect chat endpoint (Day 3)
        if request.url.path.startswith("/v1/chat"):
            auth = request.headers.get("authorization")
            if not auth:
                return json_error(request, 401, "unauthorized", "ERR_UNAUTHORIZED")

        return await call_next(request)
