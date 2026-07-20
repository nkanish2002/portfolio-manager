"""WebSocket endpoint for live price streaming.

Auth: JWT passed as ``?token=<jwt>`` on the WS URL. The token is validated
using the same JWT strategy that protects REST routes.

Protocol (per PLAN Section 6):

    Client → Server:  { "type": "subscribe", "symbols": ["AAPL", "TSLA"] }
    Server → Client:  { "type": "connected", "client_id": "abc123" }
    Server → Client:  { "type": "subscribed", "symbols": ["AAPL", "TSLA"] }
    Server → Client:  { "type": "batch", "updates": [
        { "symbol": "AAPL", "price": 198.50, "prev": 197.80 },
    ], "timestamp": "2026-07-19T12:00:00Z" }

Disconnect: Server sends nothing special — client detects close.
"""

from __future__ import annotations

import json
import uuid

import jwt as pyjwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.status import HTTP_401_UNAUTHORIZED

from portfolio_manager.auth import get_jwt_strategy
from portfolio_manager.services.data_feed import price_cache
from portfolio_manager.services.ws_service import ws_manager

router = APIRouter(tags=["websocket"])


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> bool:
    """Validate JWT token from the query string.

    Accepts the connection (before validation) so the WebSocket handshake
    completes, then checks the token. Returns True if authenticated.
    """
    if token is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Missing token parameter"})
        await websocket.close(code=HTTP_401_UNAUTHORIZED)
        return False

    try:
        strategy = get_jwt_strategy()
        payload = pyjwt.decode(
            token,
            strategy.secret,
            algorithms=[strategy.algorithm],
            options={"verify_aud": True, "verify_exp": True},
            audience=strategy.token_audience,
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token: missing subject")
    except Exception:  # noqa: BLE001
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Invalid or expired token"})
        await websocket.close(code=HTTP_401_UNAUTHORIZED)
        return False

    return True


@router.websocket("/ws/quotes")
async def websocket_quotes(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT access token"),
) -> None:
    """Live price streaming endpoint.

    Client subscribes to symbols and receives batch price updates
    at the configured poll interval (default 5 s).
    """
    # ── Auth ──────────────────────────────────────────────────────────
    if not await _authenticate_ws(websocket, token):
        return  # already closed

    # ── Accept and register ───────────────────────────────────────────
    await websocket.accept()
    client_id = str(uuid.uuid4())
    await ws_manager.add_client(client_id, websocket)

    # Send connected acknowledgement
    await ws_manager.send_json(client_id, {
        "type": "connected",
        "client_id": client_id,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await ws_manager.send_json(client_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = message.get("type")

            if msg_type == "subscribe":
                symbols = message.get("symbols", [])
                if not isinstance(symbols, list):
                    await ws_manager.send_json(client_id, {
                        "type": "error",
                        "message": "\"symbols\" must be a list",
                    })
                    continue

                normalized = ws_manager.subscribe(client_id, symbols)

                # Push an immediate snapshot of current cached prices
                snapshot = []
                for sym in normalized:
                    cached = price_cache.get(sym)
                    if cached is not None:
                        snapshot.append({
                            "symbol": cached.symbol,
                            "price": cached.price,
                            "prev": cached.prev_close,
                            "change": cached.change,
                            "change_pct": cached.change_pct,
                        })

                await ws_manager.send_json(client_id, {
                    "type": "subscribed",
                    "symbols": normalized,
                    "snapshot": snapshot if snapshot else None,
                })

            elif msg_type == "unsubscribe":
                symbols = message.get("symbols", [])
                if not isinstance(symbols, list):
                    await ws_manager.send_json(client_id, {
                        "type": "error",
                        "message": "\"symbols\" must be a list",
                    })
                    continue
                ws_manager.unsubscribe(client_id, symbols)

            elif msg_type == "ping":
                await ws_manager.send_json(client_id, {"type": "pong"})

            else:
                await ws_manager.send_json(client_id, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.remove_client(client_id)
