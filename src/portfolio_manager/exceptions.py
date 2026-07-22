"""Custom exceptions, global exception handlers, and structured logging configuration.

All API errors return a consistent JSON envelope:
    { "detail": "<human-readable message>", "error_code": "<machine-readable code>" }

Structured logging uses ``structlog`` with JSON output, timestamps, log level,
and the caller's module name. The ``structlog`` configuration is applied once at
import time via ``configure_structlog()`` so every call to
``structlog.get_logger()`` produces properly formatted records.
"""

from __future__ import annotations

import sys
from enum import StrEnum
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# ── Error codes ────────────────────────────────────────────────────────────


class ErrorCode(StrEnum):
    """Machine-readable error codes returned in the ``error_code`` field."""

    not_found = "NOT_FOUND"
    validation_error = "VALIDATION_ERROR"
    conflict = "CONFLICT"
    permission_denied = "PERMISSION_DENIED"
    unauthorized = "UNAUTHORIZED"
    internal_error = "INTERNAL_ERROR"


# ── Custom exception classes ───────────────────────────────────────────────


class AppError(Exception):
    """Base application error.

    Attributes
    ----------
    detail : str
        Human-readable error message returned to the client.
    error_code : ErrorCode
        Machine-readable code.
    status_code : int
        HTTP status code.
    """

    def __init__(
        self,
        *,
        detail: str,
        error_code: ErrorCode,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, *, detail: str = "Resource not found") -> None:
        super().__init__(
            detail=detail,
            error_code=ErrorCode.not_found,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationError(AppError):
    """Business-level validation failure (distinct from FastAPI's 422)."""

    def __init__(self, *, detail: str = "Validation failed") -> None:
        super().__init__(
            detail=detail,
            error_code=ErrorCode.validation_error,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ConflictError(AppError):
    """Request conflicts with current state (e.g. duplicate resource)."""

    def __init__(self, *, detail: str = "Resource conflict") -> None:
        super().__init__(
            detail=detail,
            error_code=ErrorCode.conflict,
            status_code=status.HTTP_409_CONFLICT,
        )


class PermissionDeniedError(AppError):
    """User lacks permission for the requested action."""

    def __init__(self, *, detail: str = "Permission denied") -> None:
        super().__init__(
            detail=detail,
            error_code=ErrorCode.permission_denied,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class UnauthorizedError(AppError):
    """Authentication required or invalid credentials."""

    def __init__(self, *, detail: str = "Unauthorized") -> None:
        super().__init__(
            detail=detail,
            error_code=ErrorCode.unauthorized,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


# ── Structured logging configuration ───────────────────────────────────────

def configure_structlog() -> None:
    """Configure structlog for JSON-structured logging.

    Output format (per line):
        {"timestamp": "...", "logger": "module.name", "level": "info", "event": "...", ...}
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.LogfmtRenderer()
            if _is_dev_mode()
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_logger().level  # type: ignore[union-attr]
            if hasattr(structlog.get_logger(), "level")
            else 20  # default INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def _is_dev_mode() -> bool:
    """Return True when running in a dev environment (logfmt is more readable)."""
    try:
        from portfolio_manager.config import settings
        return settings.get("DEBUG", False)
    except Exception:
        return False  # default to JSON when config is not available


# ── HTTP Exception Handlers ────────────────────────────────────────────────


def _error_response(
    *,
    detail: str,
    error_code: str,
    status_code: int,
) -> JSONResponse:
    """Create a consistent JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_code": error_code},
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> Response:
    """Handle Starlette / FastAPI HTTPException with consistent envelope.

    This catches standard HTTPException (404, 403, etc.) and reformats the
    response body into our standard ``{detail, error_code}`` shape.
    """
    log = structlog.get_logger()
    log.info(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        method=request.method,
        path=str(request.url.path),
    )
    # Map common status codes to error codes
    code_map: dict[int, str] = {
        400: ErrorCode.validation_error,
        401: ErrorCode.unauthorized,
        403: ErrorCode.permission_denied,
        404: ErrorCode.not_found,
        405: ErrorCode.not_found,
        409: ErrorCode.conflict,
        422: ErrorCode.validation_error,
    }
    error_code = code_map.get(exc.status_code, ErrorCode.internal_error)
    return _error_response(
        detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
        error_code=error_code,
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> Response:
    """Handle FastAPI RequestValidationError (Pydantic 422) with consistent envelope.

    Collates all field errors into a single readable message.
    """
    log = structlog.get_logger()
    log.info(
        "validation_error",
        errors=len(exc.errors()),
        method=request.method,
        path=str(request.url.path),
    )
    messages: list[str] = []
    for err in exc.errors():
        loc = " -> ".join(str(p) for p in err.get("loc", ()))
        msg = err.get("msg", "")
        messages.append(f"{loc}: {msg}" if loc else msg)
    detail = "; ".join(messages) if messages else "Validation failed"
    return _error_response(
        detail=detail,
        error_code=ErrorCode.validation_error,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def app_error_handler(
    request: Request,
    exc: AppError,
) -> Response:
    """Handle our custom ``AppError`` subclasses."""
    log = structlog.get_logger()
    log.warning(
        "app_error",
        error_code=exc.error_code.value,
        detail=exc.detail,
        method=request.method,
        path=str(request.url.path),
    )
    return _error_response(
        detail=exc.detail,
        error_code=exc.error_code.value,
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> Response:
    """Catch-all: any unhandled exception returns a generic 500.

    The actual error is logged with full traceback for debugging.
    """
    log = structlog.get_logger()
    log.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        method=request.method,
        path=str(request.url.path),
        exc_info=True,
    )
    return _error_response(
        detail="Internal server error",
        error_code=ErrorCode.internal_error,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ── Middleware ─────────────────────────────────────────────────────────────


class StructLoggingMiddleware:
    """ASGI middleware that adds structured request/response timing.

    Logs every request with: method, path, status_code, duration_ms,
    and optional ``client`` info. Errors (status >= 400) are logged at
    ``warning`` level, successes at ``info`` level.
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        log = structlog.get_logger()
        request: Request = Request(scope)
        method = request.method
        path = str(request.url.path)

        # Skip health checks and static assets from verbose logging
        if path.startswith(("/health", "/static", "/favicon")):
            await self.app(scope, receive, send)
            return

        start = __import__("time").monotonic()

        # Intercept the response status code
        status_code: int = 200

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((__import__("time").monotonic() - start) * 1000, 1)
            log.warning(
                "request_error",
                method=method,
                path=path,
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = round((__import__("time").monotonic() - start) * 1000, 1)
        level = "warning" if status_code >= 400 else "info"
        getattr(log, level)(
            "request_complete",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
        )


# ── Registration helper ────────────────────────────────────────────────────


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers and middleware on a FastAPI app."""
    # Apply structlog configuration (once, idempotent thanks to cache)
    configure_structlog()

    # Add structured logging middleware (outermost = first in / last out)
    app.add_middleware(StructLoggingMiddleware)

    # Exception handlers (most specific first)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
