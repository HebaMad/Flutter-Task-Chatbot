from __future__ import annotations

import json
import time
from typing import Callable

from fastapi import Request


async def log_middleware(request: Request, call_next: Callable):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - start) * 1000)

    log_obj = {
        "path": request.url.path,
        "method": request.method,
        "status": response.status_code,
        "requestId": getattr(request.state, "request_id", None),
        "userId": getattr(request.state, "user_id", None),
        "dialect": getattr(request.state, "dialect", None),
        "latencyMs": elapsed_ms,
    }
    print(json.dumps(log_obj, ensure_ascii=False))
    return response
