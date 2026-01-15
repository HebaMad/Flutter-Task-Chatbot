from __future__ import annotations

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Accept request id from header if present; otherwise generate one
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        return await call_next(request)
