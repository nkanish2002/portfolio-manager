"""End-to-end integration test — full user workflow (Segment 9.3 deliverable).

Exercises the complete application stack in-process via httpx ASGITransport
(no network server needed). Requires a running PostgreSQL
(``podman-compose up -d postgres``) with migrations applied
(``uv run alembic upgrade head``).

Workflow verified:
  1.  Health check (liveness + readiness)
  2.  Register user (auto-seeds 3 baskets)
  3.  Login (JWT)
  4.  User profile
  5.  Create account
  6.  Baskets auto-seeded (Super Stable / Stable Alpha / High Beta)
  7.  Create portfolio (linked to account + basket)
  8.  Buy AAPL 100 @ $150 (creates position)
  9.  Buy TSLA 50 @ $250
  10. List positions (2 created from buys)
  11. Sell 30 AAPL @ $160 (FIFO realized P&L = $300)
  12. Transaction history (3 transactions)
  13. Risk metrics (Sharpe, Sortino, VaR, Max DD, ...)
  14. Allocations (sector / region / asset class / basket)
  15. NAV chart
  16. Drawdown chart
  17. Allocation pie chart
  18. HTML report (downloadable, contains positions + risk section)
  19. List portfolios
  20. Update basket color

Run: ``uv run pytest tests/test_e2e.py -v``
(skipped automatically unless a live DB is reachable)
"""

from __future__ import annotations

import socket
import uuid

import httpx
import pytest

from portfolio_manager.config import settings
from portfolio_manager.main import app

pytestmark = pytest.mark.asyncio

EMAIL = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "E2ETestP@ss123!"


def _db_reachable_sync() -> bool:
    """Quick sync TCP probe of the configured Postgres host/port.

    Used only to decide whether to skip the E2E module (avoids running an
    async event loop at collection time).
    """
    from urllib.parse import urlparse

    try:
        url = urlparse(str(settings.DATABASE_URL).replace("+asyncpg", ""))
        host = url.hostname or "localhost"
        port = url.port or 5432
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:  # noqa: BLE001
        return False


# Skip the whole module when no live DB is available (CI without Postgres).
pytestmark = pytest.mark.skipif(
    not _db_reachable_sync(),
    reason="live PostgreSQL required for E2E (run: podman-compose up -d postgres)",
)


@pytest.fixture(scope="module")
async def client(test_db):
    from portfolio_manager.database import async_session_factory, engine

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    # Tear down: close the app's DB pool so the session-scoped test_db fixture
    # can DROP the test database at the end of the pytest session.
    import contextlib

    with contextlib.suppress(Exception):
        await async_session_factory.close()
    await engine.dispose()


async def test_full_e2e_workflow(client: httpx.AsyncClient) -> None:
    """Full register → login → trade → analytics → report workflow."""
    headers: dict[str, str] = {}

    def check(got, want, label: str) -> None:
        assert str(got) == str(want), f"{label}: got {got!r}, want {want!r}"

    # 1. Health
    r = await client.get("/health")
    assert r.status_code == 200
    check(r.json()["status"], "healthy", "health")

    r = await client.get("/health/db")
    assert r.status_code == 200
    check(r.json()["database"], "connected", "health/db")

    # 2. Register (auto-seeds 3 baskets)
    r = await client.post("/auth/jwt/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 201, r.text
    check(r.json()["email"], EMAIL, "register email")

    # 3. Login
    r = await client.post("/auth/jwt/login", data={"username": EMAIL, "password": PASSWORD})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token
    headers["Authorization"] = f"Bearer {token}"

    # 4. User profile
    r = await client.get("/users/me", headers=headers)
    assert r.status_code == 200
    check(r.json()["is_active"], True, "user active")

    # 5. Create account
    r = await client.post(
        "/api/v1/accounts/",
        headers=headers,
        json={"name": "Wacky", "institution": "Schwab", "account_number": "4242"},
    )
    assert r.status_code == 201, r.text
    account_id = r.json()["id"]

    # 6. Baskets auto-seeded
    r = await client.get("/api/v1/baskets/", headers=headers)
    assert r.status_code == 200
    baskets = r.json()
    check(len(baskets), 3, "3 baskets seeded")
    basket_id = [b["id"] for b in baskets if b["name"] == "High Beta"][0]

    # 7. Create portfolio
    r = await client.post(
        "/api/v1/portfolios/",
        headers=headers,
        json={"name": "Wacky PF", "account_id": account_id, "basket_id": basket_id},
    )
    assert r.status_code == 201, r.text
    portfolio_id = r.json()["id"]

    # 8. Buy AAPL 100 @ 150
    r = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={"symbol": "AAPL", "type": "buy", "quantity": 100, "price": 150.0},
    )
    assert r.status_code == 201, r.text
    check(r.json()["type"], "buy", "buy AAPL type")

    # 9. Buy TSLA 50 @ 250
    r = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={"symbol": "TSLA", "type": "buy", "quantity": 50, "price": 250.0},
    )
    assert r.status_code == 201, r.text

    # 10. List positions (2 from buys)
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/positions", headers=headers)
    assert r.status_code == 200
    check(len(r.json()), 2, "2 positions from buys")

    # 11. Sell 30 AAPL @ 160 (FIFO P&L)
    r = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={"symbol": "AAPL", "type": "sell", "quantity": 30, "price": 160.0},
    )
    assert r.status_code == 201, r.text
    check(r.json()["realized_gain"], "300.000000", "FIFO realized P&L = $300")

    # 12. Transaction history (3 transactions)
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/transactions", headers=headers)
    assert r.status_code == 200
    check(len(r.json()), 3, "3 transactions")

    # 13. Risk metrics
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/analytics/risk", headers=headers)
    assert r.status_code == 200, r.text
    metrics = r.json()["metrics"]
    assert "sharpe" in metrics and "sortino" in metrics and "var_95_parametric" in metrics

    # 14. Allocations
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/analytics/allocations", headers=headers)
    assert r.status_code == 200, r.text
    alloc = r.json()
    assert all(k in alloc for k in ("by_sector", "by_basket", "by_asset_class", "by_region"))

    # 15. NAV chart
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/charts/nav", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["series"]) > 0

    # 16. Drawdown chart
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/charts/drawdown", headers=headers)
    assert r.status_code == 200
    assert "max_drawdown" in r.json()

    # 17. Allocation pie
    r = await client.get(f"/api/v1/portfolios/{portfolio_id}/charts/allocation", headers=headers)
    assert r.status_code == 200
    assert "slices" in r.json()

    # 18. HTML report
    r = await client.get(f"/api/v1/reports/portfolio/{portfolio_id}", headers=headers)
    assert r.status_code == 200, r.text
    assert "Risk Metrics" in r.text, "report should contain Risk Metrics section"
    assert "AAPL" in r.text, "report should contain AAPL position"

    # 19. List portfolios
    r = await client.get("/api/v1/portfolios/", headers=headers)
    assert r.status_code == 200
    check(len(r.json()), 1, "1 portfolio")

    # 20. Update basket color
    r = await client.put(
        f"/api/v1/baskets/{basket_id}",
        headers=headers,
        json={"color": "#ff6b6b"},
    )
    assert r.status_code == 200, r.text
    check(r.json()["color"], "#ff6b6b", "basket color updated")
