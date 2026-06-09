"""WebSocket endpoint for real-time market data streaming.

Endpoint: ``ws://<host>/ws/quotes``

Protocol::

    # Client connects and subscribes:
    { "type": "subscribe", "symbols": ["AAPL", "TSLA", "BTC-USD"] }

    # Server sends updates when prices change:
    { "type": "batch", "updates": [
        { "type": "price", "symbol": "AAPL", "price": 182.50, "prev": 181.20 }
    ]}

    # Server sends connection ACK:
    { "type": "connected", "client_id": "abc123" }
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from portfolio_manager.services.ws_service import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/quotes")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket market data streaming."""
    client_id = uuid.uuid4().hex[:8]
    await websocket.accept()
    await ws_manager.connect(client_id, websocket)

    # Send connection acknowledgment
    await websocket.send_json({
        "type": "connected",
        "client_id": client_id,
    })

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type", "")

            if msg_type == "subscribe" and "symbols" in raw:
                await ws_manager.subscribe(client_id, raw["symbols"])
                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": raw["symbols"],
                })

            elif msg_type == "unsubscribe":
                if "symbols" in raw:
                    for sym in raw["symbols"]:
                        ws_manager._subscriptions[client_id].discard(sym.upper())
                await websocket.send_json({"type": "unsubscribed"})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
