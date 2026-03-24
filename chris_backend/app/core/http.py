from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.api_errors import ApiError

logger = logging.getLogger("chris_backend")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_request_id(request: Request) -> str:
    # Middleware guarantees it exists, but keep a safe fallback for edge paths.
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) and rid else "unknown"


def _error_payload(*, code: str, message: str, details: Any | None) -> dict[str, Any]:
    return {
        "error": {"code": code, "message": message, "details": details},
        "timestamp": _now_iso(),
    }


# PUBLIC_INTERFACE
def parse_cors_origins(*, raw: str | None, fallback_origin: str | None) -> list[str]:
    """
    Parse CORS origins configuration.

    Contract
    --------
    Inputs:
        - raw: comma-separated list of origins (or "*" for allow-all)
        - fallback_origin: a single origin used when raw is not provided (e.g. REACT_APP_FRONTEND_URL)

    Output:
        - List[str] for FastAPI CORSMiddleware.allow_origins

    Invariants:
        - If any origin is "*", returns ["*"].
        - Whitespace-only entries are ignored.
    """
    if raw is None or not raw.strip():
        if fallback_origin and fallback_origin.strip():
            return [fallback_origin.strip()]
        return ["*"]

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if any(p == "*" for p in parts):
        return ["*"]
    return parts


# PUBLIC_INTERFACE
def add_request_id_middleware(app: FastAPI) -> None:
    """
    Add a request-id middleware.

    Contract
    --------
    Inputs:
        - FastAPI app

    Outputs / Side effects:
        - Adds `request.state.request_id`
        - Adds `X-Request-Id` response header
        - Accepts caller-provided `X-Request-Id` or generates a UUIDv4
    """

    @app.middleware("http")
    async def _request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response


# PUBLIC_INTERFACE
def add_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers to ensure consistent error responses.

    Error response contract (all errors)
    -----------------------------------
    {
      "error": { "code": str, "message": str, "details": any|null },
      "timestamp": ISO8601,
      "request_id": str
    }

    Notes
    -----
    - ApiError is the canonical domain error type.
    - FastAPI/Starlette validation and HTTP exceptions are mapped into the same envelope.
    - Unhandled exceptions become a 500 with a stable code.
    """

    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError):
        rid = _get_request_id(request)
        payload = _error_payload(code=exc.code, message=exc.message, details=exc.details)
        payload["request_id"] = rid
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
            headers={"X-Request-Id": rid},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError):
        rid = _get_request_id(request)
        payload = _error_payload(
            code="validation_error",
            message="Request validation failed.",
            details=exc.errors(),
        )
        payload["request_id"] = rid
        return JSONResponse(
            status_code=422,
            content=payload,
            headers={"X-Request-Id": rid},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
        rid = _get_request_id(request)

        # Starlette uses `detail` for message; sometimes callers pass dicts.
        details: Any | None = None
        message = "HTTP error"
        code = "http_error"

        if isinstance(exc.detail, dict):
            # If upstream provided structured detail, keep it as "details".
            details = exc.detail
            message = str(exc.detail.get("message") or exc.detail.get("detail") or exc.detail)
            code = str(exc.detail.get("code") or code)
        else:
            message = str(exc.detail)

        payload = _error_payload(code=code, message=message, details=details)
        payload["request_id"] = rid
        return JSONResponse(
            status_code=int(exc.status_code),
            content=payload,
            headers={"X-Request-Id": rid},
        )

    @app.exception_handler(ValueError)
    async def _value_error_handler(request: Request, exc: ValueError):
        rid = _get_request_id(request)
        payload = _error_payload(code="invalid_request", message=str(exc), details=None)
        payload["request_id"] = rid
        return JSONResponse(status_code=400, content=payload, headers={"X-Request-Id": rid})

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        rid = _get_request_id(request)
        # Log full exception for long-term debuggability; keep response safe for clients.
        logger.exception("Unhandled exception (request_id=%s): %s", rid, exc)
        payload = _error_payload(
            code="internal_error",
            message="Internal server error.",
            details=None,
        )
        payload["request_id"] = rid
        return JSONResponse(status_code=500, content=payload, headers={"X-Request-Id": rid})
