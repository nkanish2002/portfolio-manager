"""WebSocket manager — live price streaming with background yfinance polling.

Architecture:
  * ``WebSocketManager`` tracks connected clients and their symbol subscriptions.
  * A single background task polls ``data_feed`` every ``WS_POLL_INTERVAL_SECONDS``
    (default 5 s). Changed prices are batch-pushed to every subscribed client.
  * The existing ``price_cache`` is shared between REST and WebSocket layers so
    cache hits reduce yfinance calls.
  * Auth is via JWT passed as ``?token=<jwt>`` on the WS URL (headers are not
    reliable for WebSocket upgrades across all browsers/proxies).

Public surface (per PLAN Segment 4.1):
  * ``ws_manager: WebSocketManager`` — module-level singleton
  * ``ws_manager.start()`` / ``ws_manager.stop()`` — called from lifespan
  * ``ws_manager.broadcast_batch(updates)`` — called from the poll loop
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import structlog

from portfolio_manager.config import settings
from portfolio_manager.services.data_feed import data_feed

log = structlog.get_logger()


# ── WebSocketManager ─────────────────────────────────────────────────────────

class WebSocketManager:
    """Manages WebSocket connections, subscriptions, and the background poller.

    Thread-safe for the single-event-loop async context (no external threads).
    """

    def __init__(
        self,
        *,
        poll_interval: float | None = None,
    ) -> None:
        self._poll_interval = poll_interval or settings.WS_POLL_INTERVAL_SECONDS
        # client_id → websocket
        self._clients: dict[str, Any] = {}
        # client_id → set of symbols
        self._subscriptions: dict[str, set[str]] = {}
        # global symbol → set of client_ids (reverse index)
        self._symbol_subscribers: dict[str, set[str]] = {}
        # symbol → last price we broadcast (for change detection)
        self._last_sent: dict[str, float] = {}
        self._poll_task: asyncio.Task | None = None
        self._running = False

    # ── lifecycle ──────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start the background poll loop."""
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(
            self._poll_loop(),
            name="ws_price_poller",
        )
        log.info("WebSocket price poller started", interval=self._poll_interval)

    async def stop(self) -> None:
        """Stop the poll loop and disconnect all clients."""
        self._running = False
        if self._poll_task is not None:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
            self._poll_task = None

        # Disconnect all clients gracefully
        for ws in list(self._clients.values()):
            with contextlib.suppress(Exception):
                await ws.close(code=1001, reason="Server shutting down")

        self._clients.clear()
        self._subscriptions.clear()
        self._symbol_subscribers.clear()
        self._last_sent.clear()
        log.info("WebSocket price poller stopped")

    # ── connection management ──────────────────────────────────────────

    async def add_client(self, client_id: str, websocket: Any) -> None:
        """Register a new WebSocket connection."""
        self._clients[client_id] = websocket
        self._subscriptions[client_id] = set()
        log.debug("Client connected", client_id=client_id, total=len(self._clients))

    def remove_client(self, client_id: str) -> None:
        """Unregister a client and clean up its subscriptions."""
        ws = self._clients.pop(client_id, None)
        if ws is not None:
            log.debug("Client disconnected", client_id=client_id)

        symbols = self._subscriptions.pop(client_id, set())
        for sym in symbols:
            self._forget_if_orphaned(sym, client_id)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def subscription_count(self) -> int:
        return len(self._symbol_subscribers)

    # ── subscription API ───────────────────────────────────────────────

    def subscribe(self, client_id: str, symbols: list[str]) -> list[str]:
        """Subscribe a client to one or more symbols.

        Returns the normalized (upper-cased) list of symbols subscribed to.
        """
        normalized: list[str] = []
        for sym in symbols:
            sym_norm = sym.strip().upper()
            if not sym_norm:
                continue
            if client_id not in self._subscriptions:
                self._subscriptions[client_id] = set()
            self._subscriptions[client_id].add(sym_norm)
            if sym_norm not in self._symbol_subscribers:
                self._symbol_subscribers[sym_norm] = set()
            self._symbol_subscribers[sym_norm].add(client_id)
            normalized.append(sym_norm)
        return normalized

    def unsubscribe(self, client_id: str, symbols: list[str]) -> list[str]:
        """Unsubscribe a client from one or more symbols.

        Returns the normalized (upper-cased) list of symbols that were removed.
        Symbols with no remaining subscribers are dropped from the reverse
        index and from the change-detection cache.
        """
        normalized: list[str] = []
        client_subs = self._subscriptions.get(client_id)
        for sym in symbols:
            sym_norm = sym.strip().upper()
            if not sym_norm:
                continue
            if client_subs is not None:
                client_subs.discard(sym_norm)
            self._forget_if_orphaned(sym_norm, client_id)
            normalized.append(sym_norm)
        return normalized

    def _forget_if_orphaned(self, symbol: str, client_id: str) -> None:
        """Remove ``symbol`` from the reverse index if no clients remain."""
        subscribers = self._symbol_subscribers.get(symbol)
        if subscribers is None:
            return
        subscribers.discard(client_id)
        if not subscribers:
            self._symbol_subscribers.pop(symbol, None)
            self._last_sent.pop(symbol, None)

    # ── message sending ────────────────────────────────────────────────

    async def send_json(self, client_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to a single client."""
        ws = self._clients.get(client_id)
        if ws is None:
            return
        try:
            await ws.send_json(message)
        except Exception:  # noqa: BLE001
            self.remove_client(client_id)

    async def broadcast_batch(self, updates: list[dict[str, Any]]) -> None:
        """Broadcast a batch of price updates to all subscribed clients.

        Each client receives *only* the symbols it subscribed to.
        """
        if not updates or not self._clients:
            return

        for client_id, ws in list(self._clients.items()):
            subs = self._subscriptions.get(client_id)
            if not subs:
                continue
            # Filter to this client's subscriptions
            client_updates = [u for u in updates if u["symbol"] in subs]
            if not client_updates:
                continue
            try:
                await ws.send_json({
                    "type": "batch",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "updates": client_updates,
                })
            except Exception:  # noqa: BLE001
                self.remove_client(client_id)

    # ── background poll loop ───────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Poll yfinance for subscribed symbols and broadcast changes."""
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001
                log.warning("WS poll error", exc_info=True)

            # Sleep in small increments so we can react to cancellation quickly
            sleep_steps = max(1, int(self._poll_interval * 10))
            step = self._poll_interval / sleep_steps
            for _ in range(sleep_steps):
                if not self._running:
                    break
                await asyncio.sleep(step)

    async def _poll_once(self) -> None:
        """Fetch prices for all subscribed symbols and push changes.

        Change detection compares the freshly-fetched price against the last
        price we broadcast for that symbol (``_last_sent``), *not* against the
        shared ``price_cache``. ``data_feed.get_price`` is cache-aware: on a hit
        it returns the cached quote, and on a miss it writes the new quote back
        into the cache — so reading the cache right after ``get_price`` would
        always yield the same ``.price`` and suppress every update. The
        per-symbol ``_last_sent`` map is the correct reference for "what did the
        client already see".
        """
        if not self._symbol_subscribers:
            return

        symbols = list(self._symbol_subscribers.keys())
        if not symbols:
            return

        updates: list[dict[str, Any]] = []
        for sym in symbols:
            quote = await data_feed.get_price(sym)
            if quote is None:
                continue

            last = self._last_sent.get(sym)
            if last is not None and last == quote.price:
                continue  # no change since last broadcast

            # "prev" is the last price the client saw, falling back to the
            # instrument's previous close on the very first broadcast.
            prev_price = last if last is not None else quote.prev_close
            updates.append({
                "symbol": quote.symbol,
                "price": quote.price,
                "prev": prev_price,
                "change": quote.change,
                "change_pct": quote.change_pct,
            })
            self._last_sent[sym] = quote.price

        if updates:
            await self.broadcast_batch(updates)


# ── Module-level singleton ─────────────────────────────────────────────────

ws_manager = WebSocketManager()
