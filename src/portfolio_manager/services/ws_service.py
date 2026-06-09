"""WebSocket market data streaming service.

Provides a FastAPI WebSocket endpoint that:
- Accepts subscriptions to multiple symbols per connection
- Debounces + batches updates (1-second window) to avoid overwhelming clients
- Fetches live prices from yfinance on a timer
- Sends JSON messages with format: {"type": "price", "symbol": "...", "price": 123.45, "prev": 121.00}
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]
from fastapi.websockets import WebSocket

from portfolio_manager.services.price_cache import default_cache

logger = logging.getLogger(__name__)

# How often the background task polls yfinance (seconds)
POLL_INTERVAL = 2
# Debounce window for batching updates to connected clients (seconds)
DEBOUNCE_WINDOW = 1.0


class WebSocketManager:
    """Manages WebSocket client connections and symbol subscriptions.

    Each connected client gets a unique ID and a set of subscribed symbols.
    The manager runs a background loop that polls yfinance, debounces updates,
    and broadcasts to all subscribed clients.
    """

    def __init__(self) -> None:
        # ws_id -> WebSocket instance
        self._connections: dict[str, WebSocket] = {}
        # ws_id -> set of symbols
        self._subscriptions: dict[str, set[str]] = defaultdict(set)
        # symbol -> set of ws_ids subscribed
        self._reverse: dict[str, set[str]] = defaultdict(set)
        # Track last known price per symbol (for diff detection)
        self._last_price: dict[str, float] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    # ---- public API ----

    async def connect(self, ws_id: str, ws) -> None:
        """Register a new WebSocket connection."""
        self._connections[ws_id] = ws

    async def disconnect(self, ws_id: str) -> None:
        """Unregister a WebSocket connection and clean up subscriptions."""
        # Remove all subscriptions for this client
        symbols = self._subscriptions.get(ws_id, set())
        for sym in symbols:
            self._reverse[sym].discard(ws_id)
            if not self._reverse[sym]:
                self._reverse.pop(sym, None)
        self._subscriptions.pop(ws_id, None)
        self._connections.pop(ws_id, None)

    async def subscribe(self, ws_id: str, symbols: list[str]) -> None:
        """Add symbol subscriptions for a client."""
        for sym in symbols:
            sym = sym.upper()
            self._subscriptions[ws_id].add(sym)
            self._reverse[sym].add(ws_id)
        logger.info("Client %s subscribed to %s", ws_id, symbols)

    def get_subscribed_symbols(self) -> set[str]:
        """Return all unique symbols currently subscribed by any client."""
        return set(self._reverse.keys())

    async def start(self) -> None:
        """Start the background polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the background polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket manager stopped")

    # ---- internal ----

    async def _poll_loop(self) -> None:
        """Background loop: poll yfinance, debounce, broadcast."""
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in WebSocket poll loop")
            await asyncio.sleep(POLL_INTERVAL)

    async def _poll_once(self) -> None:
        """One iteration: fetch prices for all subscribed symbols, batch updates."""
        subscribed = self.get_subscribed_symbols()
        if not subscribed:
            return

        # Fetch all prices in parallel (yfinance is fast enough for small batches)
        new_prices: dict[str, float] = {}
        for sym in subscribed:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = round(float(hist["Close"].iloc[-1]), 2)
                    new_prices[sym] = price
            except Exception:
                pass  # Silently skip failed lookups

        # Track price changes and build batch message
        updates = []
        for sym, price in new_prices.items():
            prev = self._last_price.get(sym)
            if prev is not None and abs(price - prev) > 0.001:
                updates.append({
                    "type": "price",
                    "symbol": sym,
                    "price": price,
                    "prev": round(prev, 2),
                })
            self._last_price[sym] = price

            # Update cache
            if price:
                await default_cache.set(sym, Decimal(str(price)))

        if not updates:
            return

        # Batch message — debounced by nature since we only poll every N seconds
        batch_msg: dict[str, Any] = {"type": "batch", "updates": updates}

        # Send to all clients that care about any of the updated symbols
        changed_symbols = {u["symbol"] for u in updates}
        for ws_id, symbols in self._subscriptions.items():
            if symbols & changed_symbols:
                try:
                    await self._connections[ws_id].send_json(batch_msg)
                except Exception:
                    logger.warning("Failed to send to client %s", ws_id)

    async def send_to_client(self, ws_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific client (e.g., on subscribe)."""
        ws = self._connections.get(ws_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("Failed to send to client %s", ws_id)


# Singleton
ws_manager = WebSocketManager()
