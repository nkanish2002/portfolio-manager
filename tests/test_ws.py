"""WebSocket service tests — manager lifecycle, subscriptions, batch broadcast,
and the WS route handler (auth, subscribe, price updates).

Strategy:
  * Unit tests for ``WebSocketManager`` with mocked WebSocket objects.
  * Handler-level tests for the WS route using mock WebSockets (avoids
    TestClient event loop conflicts with asyncpg).
"""

from __future__ import annotations

import asyncio
import secrets
import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from portfolio_manager.services.data_feed import PriceQuote
from portfolio_manager.services.ws_service import WebSocketManager

# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _make_mock_ws() -> AsyncMock:
    """Create a mock WebSocket with send_json as AsyncMock."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


async def _get_valid_token(client: AsyncClient) -> str:
    """Register a user and return a valid JWT token."""
    email = f"ws-{uuid.uuid4().hex[:8]}@example.com"
    password = secrets.token_urlsafe(12)

    reg = await client.post("/auth/jwt/register", json={"email": email, "password": password})
    assert reg.status_code == 201, reg.text

    login = await client.post("/auth/jwt/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


# ═══════════════════════════════════════════════════════════════════════════════
#  Unit tests — WebSocketManager (mocked WebSockets)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def manager():
    """Fresh WebSocketManager for each test (not the module singleton)."""
    m = WebSocketManager(poll_interval=0.1)
    return m


class TestWebSocketManager:
    """Tests for the WebSocketManager class."""

    @pytest.mark.asyncio
    async def test_add_and_remove_client(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"

        await manager.add_client(cid, ws)
        assert manager.client_count == 1
        assert cid in manager._clients

        manager.remove_client(cid)
        assert manager.client_count == 0
        assert cid not in manager._clients

    @pytest.mark.asyncio
    async def test_subscribe_and_symbol_index(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)

        symbols = manager.subscribe(cid, ["aapl", "TSLA"])
        assert symbols == ["AAPL", "TSLA"]
        assert manager.subscription_count == 2
        assert cid in manager._symbol_subscribers["AAPL"]
        assert cid in manager._symbol_subscribers["TSLA"]

    @pytest.mark.asyncio
    async def test_subscribe_normalizes_symbols(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)

        symbols = manager.subscribe(cid, ["  aapl  ", "", "GOOG"])
        # Empty string is skipped
        assert symbols == ["AAPL", "GOOG"]

    @pytest.mark.asyncio
    async def test_remove_client_cleans_subscriptions(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)
        manager.subscribe(cid, ["AAPL"])

        assert manager.subscription_count == 1
        manager.remove_client(cid)
        assert manager.subscription_count == 0
        assert "AAPL" not in manager._symbol_subscribers

    @pytest.mark.asyncio
    async def test_broadcast_batch_filters_by_subscription(self, manager: WebSocketManager):
        ws1 = await _make_mock_ws()
        ws2 = await _make_mock_ws()
        cid1 = "c1"
        cid2 = "c2"
        await manager.add_client(cid1, ws1)
        await manager.add_client(cid2, ws2)
        manager.subscribe(cid1, ["AAPL"])
        manager.subscribe(cid2, ["TSLA"])

        updates = [
            {"symbol": "AAPL", "price": 150.0, "prev": 149.0},
            {"symbol": "TSLA", "price": 250.0, "prev": 248.0},
            {"symbol": "GOOG", "price": 300.0, "prev": 299.0},  # nobody subscribed
        ]
        await manager.broadcast_batch(updates)

        # c1 subscribed to AAPL only
        ws1.send_json.assert_called_once()
        msg1 = ws1.send_json.call_args[0][0]
        assert msg1["type"] == "batch"
        assert len(msg1["updates"]) == 1
        assert msg1["updates"][0]["symbol"] == "AAPL"

        # c2 subscribed to TSLA only
        ws2.send_json.assert_called_once()
        msg2 = ws2.send_json.call_args[0][0]
        assert msg2["type"] == "batch"
        assert len(msg2["updates"]) == 1
        assert msg2["updates"][0]["symbol"] == "TSLA"

    @pytest.mark.asyncio
    async def test_broadcast_batch_removes_failed_clients(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)
        manager.subscribe(cid, ["AAPL"])

        # Simulate send failure
        ws.send_json.side_effect = Exception("connection lost")

        await manager.broadcast_batch([{"symbol": "AAPL", "price": 150.0}])

        # Client should be removed
        assert manager.client_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_batch_no_clients_is_noop(self, manager: WebSocketManager):
        """No crash when there are no connected clients."""
        await manager.broadcast_batch([{"symbol": "AAPL", "price": 150.0}])

    @pytest.mark.asyncio
    async def test_broadcast_batch_no_updates_is_noop(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)
        manager.subscribe(cid, ["AAPL"])

        await manager.broadcast_batch([])
        ws.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_json_to_unknown_client(self, manager: WebSocketManager):
        """Sending to a non-existent client is a no-op."""
        await manager.send_json("nonexistent", {"type": "ping"})

    @pytest.mark.asyncio
    async def test_start_and_stop(self, manager: WebSocketManager):
        await manager.start()
        assert manager.is_running
        await asyncio.sleep(0.05)
        await manager.stop()
        assert not manager.is_running

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, manager: WebSocketManager):
        await manager.start()
        await manager.start()  # should be no-op
        assert manager.is_running
        await manager.stop()

    @pytest.mark.asyncio
    async def test_stop_closes_all_clients(self, manager: WebSocketManager):
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)

        await manager.start()
        await asyncio.sleep(0.05)
        await manager.stop()

        ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_loop_runs_while_subscribed(self, manager: WebSocketManager, monkeypatch):
        """Poll loop iterates while running with subscriptions."""
        poll_count = 0

        async def fake_poll():
            nonlocal poll_count
            poll_count += 1

        monkeypatch.setattr(manager, "_poll_once", fake_poll)

        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)
        manager.subscribe(cid, ["AAPL"])

        await manager.start()
        await asyncio.sleep(0.35)  # poll_interval is 0.1s
        await manager.stop()

        assert poll_count >= 2  # at least 2-3 polls in 0.35s

    @pytest.mark.asyncio
    async def test_poll_once_broadcasts_initial_and_changes(self, manager: WebSocketManager, monkeypatch):
        """_poll_once broadcasts the first quote, then only on price changes.

        Regression: the original implementation read ``price_cache`` *after*
        ``data_feed.get_price`` (which writes the cache), so the change check
        always compared a quote against itself and never broadcast anything.
        """
        prices = iter([100.0, 100.0, 105.0])

        class FakeFeed:
            async def get_price(self, symbol: str) -> PriceQuote | None:
                try:
                    return PriceQuote(symbol=symbol, price=next(prices), prev_close=99.0)
                except StopIteration:
                    return None

        monkeypatch.setattr("portfolio_manager.services.ws_service.data_feed", FakeFeed())

        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)
        manager.subscribe(cid, ["AAPL"])

        # 1st poll: first quote (100.0) → broadcast (prev falls back to prev_close)
        await manager._poll_once()
        assert ws.send_json.call_count == 1
        batch = ws.send_json.call_args.args[0]
        assert batch["type"] == "batch"
        assert batch["updates"][0]["symbol"] == "AAPL"
        assert batch["updates"][0]["price"] == 100.0
        assert batch["updates"][0]["prev"] == 99.0  # prev_close on first broadcast

        # 2nd poll: same price (100.0) → no broadcast (change detection)
        await manager._poll_once()
        assert ws.send_json.call_count == 1

        # 3rd poll: price changed (105.0) → broadcast, prev = last seen (100.0)
        await manager._poll_once()
        assert ws.send_json.call_count == 2
        batch = ws.send_json.call_args.args[0]
        assert batch["updates"][0]["price"] == 105.0
        assert batch["updates"][0]["prev"] == 100.0  # last broadcast price

    @pytest.mark.asyncio
    async def test_unsubscribe_drops_orphaned_symbol_state(self, manager: WebSocketManager):
        """Unsubscribing the last subscriber clears the reverse + last-sent state."""
        ws = await _make_mock_ws()
        cid = "client-1"
        await manager.add_client(cid, ws)
        manager.subscribe(cid, ["AAPL", "TSLA"])
        manager._last_sent["AAPL"] = 100.0

        removed = manager.unsubscribe(cid, ["aapl"])
        assert removed == ["AAPL"]
        assert "AAPL" not in manager._subscriptions[cid]
        assert "AAPL" not in manager._symbol_subscribers
        assert "AAPL" not in manager._last_sent
        assert "TSLA" in manager._symbol_subscribers  # still subscribed


# ═══════════════════════════════════════════════════════════════════════════════
#  Auth tests — WS route _authenticate_ws helper
# ═══════════════════════════════════════════════════════════════════════════════

class MockWebSocket:
    """Minimal async WebSocket mock for testing the route handler."""

    def __init__(self):
        self.accepted = False
        self.sent: list[dict] = []
        self.received: list[str] = []
        self.close_code: int | None = None
        self._closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)

    async def receive_text(self) -> str:
        if not self.received:
            from starlette.websockets import WebSocketDisconnect
            raise WebSocketDisconnect()
        return self.received.pop(0)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self._closed = True
        self.close_code = code

    def get_sent(self, type_: str | None = None) -> list[dict]:
        if type_ is None:
            return self.sent
        return [m for m in self.sent if m.get("type") == type_]


class TestWebSocketAuth:
    """Test JWT authentication for the WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_missing_token_closes_with_401(self):
        from portfolio_manager.routes.ws import _authenticate_ws

        ws = MockWebSocket()
        result = await _authenticate_ws(ws, None)

        assert not result
        assert ws.accepted
        assert ws.close_code == 401
        errors = ws.get_sent("error")
        assert len(errors) == 1
        assert "Missing token" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_invalid_token_closes_with_401(self):
        from portfolio_manager.routes.ws import _authenticate_ws

        ws = MockWebSocket()
        result = await _authenticate_ws(ws, "not-a-valid-jwt")

        assert not result
        assert ws.accepted
        assert ws.close_code == 401
        errors = ws.get_sent("error")
        assert len(errors) == 1
        assert "Invalid or expired" in errors[0]["message"]

    @pytest.mark.asyncio
    async def test_valid_token_succeeds(self, client):
        """A JWT from a real login passes auth."""
        from portfolio_manager.routes.ws import _authenticate_ws

        token = await _get_valid_token(client)

        ws = MockWebSocket()
        result = await _authenticate_ws(ws, token)

        assert result
        # On success, _authenticate_ws does NOT call accept() or close()
        # — the caller (handler) does accept() after auth returns True
        assert not ws._closed
        # The handler would call accept() after this

    @pytest.mark.asyncio
    async def test_expired_token_fails(self):
        """An expired JWT fails auth."""
        import time

        import jwt as pyjwt

        from portfolio_manager.auth import get_jwt_strategy
        from portfolio_manager.routes.ws import _authenticate_ws

        strategy = get_jwt_strategy()
        # Create a token that expired 1 second ago
        payload = {
            "sub": str(uuid.uuid4()),
            "aud": strategy.token_audience,
            "exp": int(time.time()) - 1,  # already expired
        }
        expired_token = pyjwt.encode(payload, strategy.secret, algorithm=strategy.algorithm)

        ws = MockWebSocket()
        result = await _authenticate_ws(ws, expired_token)

        assert not result
        assert ws.close_code == 401
        errors = ws.get_sent("error")
        assert len(errors) == 1
        assert "Invalid or expired" in errors[0]["message"]


# ═══════════════════════════════════════════════════════════════════════════════
#  Protocol tests — message exchange with ws_manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestWebSocketMessageProtocol:
    """Test the message exchange protocol using ws_manager directly.

    These tests bypass _authenticate_ws and use the manager's API directly
    to test subscription, broadcast, and cleanup logic.
    """

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        """Clean up clients after each test."""
        from portfolio_manager.services.ws_service import ws_manager
        initial = set(ws_manager._clients.keys())
        yield
        for cid in set(ws_manager._clients.keys()) - initial:
            ws_manager.remove_client(cid)
        if ws_manager.is_running:
            await ws_manager.stop()

    @pytest.mark.asyncio
    async def test_connect_and_subscribe(self):
        """Client connects, subscribes, receives acknowledgement."""
        from portfolio_manager.services.ws_service import ws_manager

        ws = MockWebSocket()
        client_id = str(uuid.uuid4())
        await ws_manager.add_client(client_id, ws)

        # Send connected message
        await ws_manager.send_json(client_id, {"type": "connected", "client_id": client_id})
        assert len(ws.get_sent("connected")) == 1

        # Subscribe
        symbols = ws_manager.subscribe(client_id, ["AAPL", "TSLA"])
        assert set(symbols) == {"AAPL", "TSLA"}

        # Send subscribed acknowledgement
        await ws_manager.send_json(client_id, {
            "type": "subscribed",
            "symbols": symbols,
            "snapshot": None,
        })
        assert len(ws.get_sent("subscribed")) == 1

        ws_manager.remove_client(client_id)

    @pytest.mark.asyncio
    async def test_ping_pong(self):
        """Ping → Pong message exchange."""
        from portfolio_manager.services.ws_service import ws_manager

        ws = MockWebSocket()
        client_id = str(uuid.uuid4())
        await ws_manager.add_client(client_id, ws)

        await ws_manager.send_json(client_id, {"type": "pong"})
        assert len(ws.get_sent("pong")) == 1

        ws_manager.remove_client(client_id)

    @pytest.mark.asyncio
    async def test_batch_broadcast_reaches_subscriber(self):
        """Broadcast reaches subscribed clients, not unsubscribed ones."""
        from portfolio_manager.services.ws_service import ws_manager

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        c1 = str(uuid.uuid4())
        c2 = str(uuid.uuid4())

        await ws_manager.add_client(c1, ws1)
        await ws_manager.add_client(c2, ws2)
        ws_manager.subscribe(c1, ["AAPL"])
        ws_manager.subscribe(c2, ["TSLA"])

        await ws_manager.broadcast_batch([
            {"symbol": "AAPL", "price": 175.0, "prev": 174.0, "change": 1.0, "change_pct": 0.57},
            {"symbol": "TSLA", "price": 250.0, "prev": 248.0, "change": 2.0, "change_pct": 0.81},
        ])

        # ws1 got AAPL only
        batches1 = ws1.get_sent("batch")
        assert len(batches1) == 1
        assert len(batches1[0]["updates"]) == 1
        assert batches1[0]["updates"][0]["symbol"] == "AAPL"
        assert "timestamp" in batches1[0]

        # ws2 got TSLA only
        batches2 = ws2.get_sent("batch")
        assert len(batches2) == 1
        assert batches2[0]["updates"][0]["symbol"] == "TSLA"

        ws_manager.remove_client(c1)
        ws_manager.remove_client(c2)

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self):
        """Client disconnecting removes all traces from the manager."""
        from portfolio_manager.services.ws_service import ws_manager

        ws = MockWebSocket()
        client_id = str(uuid.uuid4())
        await ws_manager.add_client(client_id, ws)
        ws_manager.subscribe(client_id, ["AAPL", "GOOG"])

        initial_count = ws_manager.client_count
        assert ws_manager.subscription_count >= 2

        ws_manager.remove_client(client_id)

        assert ws_manager.client_count == initial_count - 1
        # Both symbols should be cleaned up
        assert "AAPL" not in ws_manager._symbol_subscribers or client_id not in ws_manager._symbol_subscribers.get("AAPL", set())
        assert "GOOG" not in ws_manager._symbol_subscribers or client_id not in ws_manager._symbol_subscribers.get("GOOG", set())

    @pytest.mark.asyncio
    async def test_subscribe_with_cached_snapshot(self):
        """Cached prices are included in the snapshot."""
        from portfolio_manager.services.data_feed import price_cache
        from portfolio_manager.services.ws_service import ws_manager

        # Seed a cached price
        cached = PriceQuote(symbol="AAPL", price=175.50, prev_close=174.00, currency="USD")
        price_cache.set("AAPL", cached, ttl=60)

        try:
            ws = MockWebSocket()
            client_id = str(uuid.uuid4())
            await ws_manager.add_client(client_id, ws)
            ws_manager.subscribe(client_id, ["AAPL"])

            # Build snapshot as the handler does
            snapshot = []
            for sym in ["AAPL"]:
                c = price_cache.get(sym)
                if c is not None:
                    snapshot.append({
                        "symbol": c.symbol, "price": c.price,
                        "prev": c.prev_close, "change": c.change, "change_pct": c.change_pct,
                    })

            await ws_manager.send_json(client_id, {
                "type": "subscribed",
                "symbols": ["AAPL"],
                "snapshot": snapshot if snapshot else None,
            })

            subscribed = ws.get_sent("subscribed")
            assert len(subscribed) == 1
            assert subscribed[0]["snapshot"] is not None
            assert subscribed[0]["snapshot"][0]["price"] == 175.50

            ws_manager.remove_client(client_id)
        finally:
            price_cache.invalidate("AAPL")

    @pytest.mark.asyncio
    async def test_error_messages(self):
        """Error messages are properly sent to the client."""
        from portfolio_manager.services.ws_service import ws_manager

        ws = MockWebSocket()
        client_id = str(uuid.uuid4())
        await ws_manager.add_client(client_id, ws)

        await ws_manager.send_json(client_id, {"type": "error", "message": "Unknown message type: badtype"})
        await ws_manager.send_json(client_id, {"type": "error", "message": '"symbols" must be a list'})

        errors = ws.get_sent("error")
        assert len(errors) == 2
        assert "Unknown message type" in errors[0]["message"]
        assert "must be a list" in errors[1]["message"]

        ws_manager.remove_client(client_id)

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_symbol(self):
        """Client unsubscribing removes symbol from index."""
        from portfolio_manager.services.ws_service import ws_manager

        ws = MockWebSocket()
        client_id = str(uuid.uuid4())
        await ws_manager.add_client(client_id, ws)
        ws_manager.subscribe(client_id, ["AAPL", "TSLA"])

        assert len(ws_manager._subscriptions[client_id]) == 2

        # Simulate unsubscribe from AAPL (as the handler does)
        ws_manager._subscriptions.get(client_id, set()).discard("AAPL")
        subs = ws_manager._symbol_subscribers.get("AAPL")
        if subs:
            subs.discard(client_id)
            if not subs:
                ws_manager._symbol_subscribers.pop("AAPL", None)

        assert "AAPL" not in ws_manager._subscriptions[client_id]
        assert "TSLA" in ws_manager._subscriptions[client_id]

        ws_manager.remove_client(client_id)
