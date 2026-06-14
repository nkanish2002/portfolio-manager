"""WebSocket endpoint integration tests."""

import pytest
from starlette.testclient import TestClient

from portfolio_manager.main import app


@pytest.mark.asyncio
async def test_ws_connects():
    """Test that the WebSocket endpoint accepts connections."""

    with TestClient(app) as client:
        with client.websocket_connect("/ws/quotes") as ws:
            # Should receive a 'connected' message
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert "client_id" in data


@pytest.mark.asyncio
async def test_ws_subscribe():
    """Test subscribing to symbols."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/quotes") as ws:
            # Receive connected message
            ws.receive_json()

            # Subscribe to symbols
            ws.send_json({"type": "subscribe", "symbols": ["AAPL", "TSLA"]})

            # Should receive subscribed message
            data = ws.receive_json()
            assert data["type"] == "subscribed"
            assert set(data["symbols"]) == {"AAPL", "TSLA"}
