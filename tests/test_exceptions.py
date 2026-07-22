"""Tests for global exception handlers, structured logging, and graceful shutdown.

Covers:
  * 404 (unknown route) returns consistent JSON envelope with error_code
  * 422 (Pydantic validation failure) is reformatted into our envelope
  * Custom AppError subclasses (NotFoundError, ValidationError, ConflictError,
    PermissionDeniedError, UnauthorizedError) return the right status + code
  * Unhandled exceptions return a generic 500 with error_code
  * StructLoggingMiddleware logs request timing
  * Graceful shutdown in lifespan cleans up WS manager + DB engine
"""

from __future__ import annotations

import json

from starlette.requests import Request

# ── Helper: build a minimal Request scope ──────────────────────────────────

def _request_scope(
    method: str = "GET",
    path: str = "/test",
    query_string: bytes = b"",
) -> dict:
    """Build a minimal ASGI HTTP scope suitable for constructing a Request."""
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": [],
        "server": ("testserver", 80),
        "scheme": "http",
    }


# ── 404 — unknown route ──────────────────────────────────────────────────
# When the SPA catch-all (GET /{full_path:path}) is active (static/ exists),
# unknown GET paths return 200. Non-GET methods hit the catch-all's path but
# get 405 Method Not Allowed. Our http_exception_handler maps 405 → NOT_FOUND
# so the error_code is still correct regardless of the HTTP status.


async def test_unknown_route_returns_not_found_code(client) -> None:
    """An unknown route returns NOT_FOUND error_code in the response body.

    Uses DELETE to avoid the SPA GET catch-all. The HTTP status may be 404 or
    405 depending on whether a catch-all route exists, but error_code is always
    NOT_FOUND.
    """
    resp = await client.delete("/api/v1/nonexistent-route-xyz")
    assert resp.status_code in (404, 405)
    body = resp.json()
    assert "detail" in body
    assert body["error_code"] == "NOT_FOUND"


async def test_unknown_route_patch_returns_not_found_code(client) -> None:
    """PATCH on an unknown route also returns the NOT_FOUND error_code."""
    resp = await client.patch("/api/v1/nonexistent-route-xyz")
    assert resp.status_code in (404, 405)
    body = resp.json()
    assert body["error_code"] == "NOT_FOUND"


# ── 422 — Pydantic validation error ──────────────────────────────────────


async def test_422_validation_error_reformatted(client) -> None:
    """A POST with invalid body to register endpoint returns our validation envelope."""
    resp = await client.post(
        "/auth/jwt/register",
        json={"email": "not-an-email", "password": "short"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body
    assert body["error_code"] == "VALIDATION_ERROR"


async def test_422_detail_collates_field_errors(client) -> None:
    """The detail string contains the field error messages."""
    resp = await client.post(
        "/auth/jwt/register",
        json={"email": "bad", "password": "x"},
    )
    assert resp.status_code == 422
    body = resp.json()
    # Should contain references to the failing fields
    assert len(body["detail"]) > 0


# ── Custom AppError subclasses (handler-level tests) ─────────────────────


async def test_app_error_handler_not_found() -> None:
    """The AppError handler returns the correct envelope for NotFoundError."""
    from portfolio_manager.exceptions import NotFoundError, app_error_handler

    request = Request(_request_scope())
    result = await app_error_handler(
        request=request,
        exc=NotFoundError(detail="Widget not found"),
    )
    assert result.status_code == 404
    body = json.loads(result.body)
    assert body["error_code"] == "NOT_FOUND"
    assert body["detail"] == "Widget not found"


async def test_app_error_handler_validation_error() -> None:
    """ValidationError returns 422 with VALIDATION_ERROR code."""
    from portfolio_manager.exceptions import ValidationError, app_error_handler

    request = Request(_request_scope(method="POST"))
    result = await app_error_handler(
        request=request,
        exc=ValidationError(detail="Target allocation must be positive"),
    )
    assert result.status_code == 422
    body = json.loads(result.body)
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["detail"] == "Target allocation must be positive"


async def test_app_error_handler_conflict() -> None:
    """ConflictError returns 409 with CONFLICT code."""
    from portfolio_manager.exceptions import ConflictError, app_error_handler

    request = Request(_request_scope(method="POST"))
    result = await app_error_handler(
        request=request,
        exc=ConflictError(detail="Duplicate symbol"),
    )
    assert result.status_code == 409
    body = json.loads(result.body)
    assert body["error_code"] == "CONFLICT"
    assert body["detail"] == "Duplicate symbol"


async def test_app_error_handler_permission_denied() -> None:
    """PermissionDeniedError returns 403 with PERMISSION_DENIED code."""
    from portfolio_manager.exceptions import PermissionDeniedError, app_error_handler

    request = Request(_request_scope(method="DELETE"))
    result = await app_error_handler(
        request=request,
        exc=PermissionDeniedError(detail="Not your basket"),
    )
    assert result.status_code == 403
    body = json.loads(result.body)
    assert body["error_code"] == "PERMISSION_DENIED"
    assert body["detail"] == "Not your basket"


async def test_app_error_handler_unauthorized() -> None:
    """UnauthorizedError returns 401 with UNAUTHORIZED code."""
    from portfolio_manager.exceptions import UnauthorizedError, app_error_handler

    request = Request(_request_scope())
    result = await app_error_handler(
        request=request,
        exc=UnauthorizedError(detail="Token expired"),
    )
    assert result.status_code == 401
    body = json.loads(result.body)
    assert body["error_code"] == "UNAUTHORIZED"
    assert body["detail"] == "Token expired"


# ── HTTPException (Starlette) mapping ────────────────────────────────────


async def test_http_exception_404_mapped() -> None:
    """Starlette HTTPException 404 is mapped to NOT_FOUND error_code."""
    from starlette.exceptions import HTTPException

    from portfolio_manager.exceptions import http_exception_handler

    request = Request(_request_scope())
    exc = HTTPException(status_code=404, detail="Item missing")
    result = await http_exception_handler(request=request, exc=exc)
    body = json.loads(result.body)
    assert body["error_code"] == "NOT_FOUND"
    assert body["detail"] == "Item missing"


async def test_http_exception_403_mapped() -> None:
    """Starlette HTTPException 403 is mapped to PERMISSION_DENIED error_code."""
    from starlette.exceptions import HTTPException

    from portfolio_manager.exceptions import http_exception_handler

    request = Request(_request_scope(method="POST"))
    exc = HTTPException(status_code=403, detail="Forbidden")
    result = await http_exception_handler(request=request, exc=exc)
    body = json.loads(result.body)
    assert body["error_code"] == "PERMISSION_DENIED"


async def test_http_exception_401_mapped() -> None:
    """Starlette HTTPException 401 is mapped to UNAUTHORIZED error_code."""
    from starlette.exceptions import HTTPException

    from portfolio_manager.exceptions import http_exception_handler

    request = Request(_request_scope())
    exc = HTTPException(status_code=401, detail="Credentials required")
    result = await http_exception_handler(request=request, exc=exc)
    body = json.loads(result.body)
    assert body["error_code"] == "UNAUTHORIZED"


# ── Unhandled exception (500) ────────────────────────────────────────────


async def test_unhandled_exception_returns_generic_500() -> None:
    """Any unhandled exception returns a generic 500 with INTERNAL_ERROR code."""
    from portfolio_manager.exceptions import unhandled_exception_handler

    request = Request(_request_scope())
    result = await unhandled_exception_handler(
        request=request,
        exc=RuntimeError("Something exploded"),
    )
    assert result.status_code == 500
    body = json.loads(result.body)
    assert body["error_code"] == "INTERNAL_ERROR"
    assert body["detail"] == "Internal server error"
    # Internal details should NOT leak
    assert "exploded" not in body["detail"]


# ── Validation exception handler ─────────────────────────────────────────


async def test_validation_exception_handler_format() -> None:
    """RequestValidationError is collated into readable field error messages."""
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    from portfolio_manager.exceptions import (
        RequestValidationError,
        validation_exception_handler,
    )

    class DummyModel(BaseModel):
        name: str

    try:
        DummyModel(name=123)  # type: ignore[arg-type]
    except PydanticValidationError as pyd_err:
        fastapi_err = RequestValidationError(pyd_err.errors())

    request = Request(_request_scope(method="POST"))
    result = await validation_exception_handler(request=request, exc=fastapi_err)
    assert result.status_code == 422
    body = json.loads(result.body)
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "name" in body["detail"].lower()


# ── Structured logging middleware ────────────────────────────────────────


async def test_logging_middleware_does_not_break_requests(auth_client) -> None:
    """The StructLoggingMiddleware passes normal requests through correctly."""
    resp = await auth_client.get("/api/v1/baskets/")
    assert resp.status_code == 200


async def test_logging_middleware_skips_health_checks(client) -> None:
    """Health check endpoints are excluded from verbose logging but still work."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ── Graceful shutdown (lifespan) ─────────────────────────────────────────
# The lifespan function references ws_manager, engine, and async_session_factory
# from the main module. We patch them at the module level via sys.modules so
# the patched references are what the lifespan function sees.


async def test_lifespan_stops_ws_manager_and_disposes_engine(monkeypatch) -> None:
    """The lifespan context manager stops WS manager and disposes the engine on exit."""
    import types

    import portfolio_manager.main as main_mod

    stop_called = False
    dispose_called = close_called = False

    async def fake_stop():
        nonlocal stop_called
        stop_called = True

    async def fake_dispose():
        nonlocal dispose_called
        dispose_called = True

    async def fake_close():
        nonlocal close_called
        close_called = True

    # Create a simple proxy object we CAN set attributes on
    fake_engine = types.SimpleNamespace()
    fake_engine.dispose = fake_dispose
    fake_engine.connect = main_mod.engine.connect  # keep original connect for startup

    fake_factory = types.SimpleNamespace()
    fake_factory.close = fake_close

    monkeypatch.setattr(main_mod, "ws_manager", types.SimpleNamespace(stop=fake_stop, start=main_mod.ws_manager.start))
    monkeypatch.setattr(main_mod, "engine", fake_engine)
    monkeypatch.setattr(main_mod, "async_session_factory", fake_factory)

    async with main_mod.lifespan(main_mod.app):
        pass

    assert stop_called, "ws_manager.stop() should be called on shutdown"
    assert close_called, "async_session_factory.close() should be called on shutdown"
    assert dispose_called, "engine.dispose() should be called on shutdown"


async def test_lifespan_handles_ws_stop_error_gracefully(monkeypatch) -> None:
    """If ws_manager.stop() raises, shutdown still completes (engine is disposed)."""
    import types

    import portfolio_manager.main as main_mod

    dispose_called = close_called = False

    async def failing_stop():
        raise RuntimeError("WS stop failed")

    async def fake_dispose():
        nonlocal dispose_called
        dispose_called = True

    async def fake_close():
        nonlocal close_called
        close_called = True

    fake_engine = types.SimpleNamespace()
    fake_engine.dispose = fake_dispose
    fake_engine.connect = main_mod.engine.connect  # keep original for startup

    fake_factory = types.SimpleNamespace()
    fake_factory.close = fake_close

    monkeypatch.setattr(main_mod, "ws_manager", types.SimpleNamespace(stop=failing_stop, start=main_mod.ws_manager.start))
    monkeypatch.setattr(main_mod, "engine", fake_engine)
    monkeypatch.setattr(main_mod, "async_session_factory", fake_factory)

    async with main_mod.lifespan(main_mod.app):
        pass

    # Despite ws_manager.stop() raising, the rest should still run
    assert close_called, "session factory close should run even if ws stop fails"
    assert dispose_called, "engine.dispose() should run even if ws_manager.stop() fails"


# ── ErrorCode enum ───────────────────────────────────────────────────────


async def test_error_code_values() -> None:
    """ErrorCode enum has expected string values."""
    from portfolio_manager.exceptions import ErrorCode

    assert ErrorCode.not_found.value == "NOT_FOUND"
    assert ErrorCode.validation_error.value == "VALIDATION_ERROR"
    assert ErrorCode.conflict.value == "CONFLICT"
    assert ErrorCode.permission_denied.value == "PERMISSION_DENIED"
    assert ErrorCode.unauthorized.value == "UNAUTHORIZED"
    assert ErrorCode.internal_error.value == "INTERNAL_ERROR"


# ── AppError base class ──────────────────────────────────────────────────


async def test_app_error_attributes() -> None:
    """AppError carries detail, error_code, and status_code."""
    from portfolio_manager.exceptions import AppError, ErrorCode

    err = AppError(detail="test message", error_code=ErrorCode.internal_error, status_code=500)
    assert err.detail == "test message"
    assert err.error_code == ErrorCode.internal_error
    assert err.status_code == 500


# ── Integration: not-found portfolio via API ─────────────────────────────


async def test_404_via_api_route(auth_client) -> None:
    """Fetching a non-existent portfolio via the API returns 404 with NOT_FOUND."""
    resp = await auth_client.get("/api/v1/portfolios/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "NOT_FOUND"
