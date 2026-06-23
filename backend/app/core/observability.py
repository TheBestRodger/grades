from __future__ import annotations

import logging
import json
import sys
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


REQUEST_ID_HEADER = "X-Request-ID"
SLOW_REQUEST_THRESHOLD_MS = 1_000

logger = logging.getLogger("app.request")


class JsonRequestLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "event": record.getMessage(),
            "level": record.levelname.lower(),
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_request_logging() -> None:
    if getattr(logger, "_grades_mgtu_configured", False):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonRequestLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger._grades_mgtu_configured = True


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        request.state.request_id = request_id
        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            level = logging.WARNING if duration_ms >= SLOW_REQUEST_THRESHOLD_MS else logging.INFO
            logger.log(
                level,
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                },
            )
            if "response" in locals():
                response.headers[REQUEST_ID_HEADER] = request_id
