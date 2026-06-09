"""Custom exception classes and FastAPI global error handlers.

Provides a consistent JSON error response format across all routes:

    {
        "error": {
            "code": "PORTFOLIO_NOT_FOUND",
            "message": "Portfolio 'My Fund' not found",
            "detail": null,
            "path": "/api/v1/portfolios/123"
        }
    }

In DEBUG mode, the `detail` field includes the full traceback for
easier development. In production it is omitted.
"""

from __future__ import annotations

import logging
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from portfolio_manager.config import settings  # type: ignore[import-untyped]

logger = logging.getLogger("portfolio_manager.errors")


# ──────────────────────────── Custom Exceptions ───────────────────────────────

@dataclass
class AppException(Exception):
    """Base exception for all domain-specific errors.

    Subclasses should set `status_code` and optionally override `detail`.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"
    detail: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass
class NotFoundError(AppException):
    status_code: int = status.HTTP_404_NOT_FOUND
    code: str = "NOT_FOUND"


@dataclass
class ConflictError(AppException):
    status_code: int = status.HTTP_409_CONFLICT
    code: str = "CONFLICT"


@dataclass
class ValidationError(AppException):
    status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    code: str = "VALIDATION_ERROR"


@dataclass
class UnauthorizedError(AppException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    code: str = "UNAUTHORIZED"


@dataclass
class ForbiddenError(AppException):
    status_code: int = status.HTTP_403_FORBIDDEN
    code: str = "FORBIDDEN"


@dataclass
class ServiceUnavailableError(AppException):
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    code: str = "SERVICE_UNAVAILABLE"


# ──────────────────────────── Error Response Builder ──────────────────────────

def _build_error_body(exc: AppException, request: Request, debug: bool) -> dict[str, Any]:
    """Build the canonical error JSON body."""
    body: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "path": str(request.url.path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    if exc.detail is not None:
        body["error"]["detail"] = exc.detail

    if exc.extra:
        body["error"]["extra"] = exc.extra

    if debug:
        body["error"]["debug"] = {
            "traceback": traceback.format_exc(),
            "stack": (
                [str(f) for f in traceback.extract_tb(sys.exc_info()[2])]
                if sys.exc_info()[2]
                else None
            ),
        }

    return body


# ──────────────────────────── FastAPI Handlers ────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app.

    Call once during app startup (or at module level).
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "[%s] %s — %s (code=%s)",
            exc.status_code,
            exc.code,
            exc.message,
            request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_body(exc, request, debug=settings.debug),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Normalize FastAPI's built-in HTTPException to our canonical format."""
        # Map common HTTPException detail strings to typed error codes
        detail = exc.detail or ""
        code = "HTTP_ERROR"
        message = str(detail)

        if "not found" in detail.lower() or "Not Found" in detail:
            code = "NOT_FOUND"
        elif "already exists" in detail.lower() or "conflict" in detail.lower():
            code = "CONFLICT"
        elif exc.status_code == 400:
            code = "BAD_REQUEST"
        elif exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 422:
            code = "VALIDATION_ERROR"

        logger.warning(
            "[%s] HTTPException — %s (code=%s)",
            exc.status_code,
            message,
            request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "path": str(request.url.path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "[%s] Validation error on %s — %d issue(s)",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            request.url.path,
            len(exc.errors()),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request body contains invalid fields",
                    "detail": exc.errors(),
                    "path": str(request.url.path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.error(
            "[%s] DB integrity violation on %s — %s",
            status.HTTP_409_CONFLICT,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "code": "CONFLICT",
                    "message": "A resource with this identifier already exists",
                    "detail": str(exc.orig) if exc.orig else None,
                    "path": str(request.url.path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError):
        logger.error(
            "[%s] DB operational error on %s — %s",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Database connection failed",
                    "path": str(request.url.path),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "[%s] Unhandled exception on %s — %s: %s",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            request.url.path,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_build_error_body(
                AppException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    code="INTERNAL_ERROR",
                    message=str(exc) if settings.debug else "An unexpected error occurred",
                ),
                request,
                debug=settings.debug,
            ),
        )
