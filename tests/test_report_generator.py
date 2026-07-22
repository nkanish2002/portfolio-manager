"""Tests for the report generation route — covers the bugs found in review.

Covers:
  * GET /api/v1/reports/portfolio/{id} returns HTML (not a crash)
  * The ``float(sum(...), Decimal("0"))`` TypeError (misplaced paren) is fixed
  * The ``portfolio.basket`` lazy-load MissingGreenlet crash is fixed
  * Negative P&L renders with a minus sign, positions P&L as currency
  * Auth + ownership enforcement
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


# ── Fixtures ────────────────────────────────────────────────────────────


async def _seed_portfolio_with_positions(
    client, make_account, make_portfolio, make_asset, db_session, *, with_basket: bool = True
):
    """Create an account, (optional) basket, portfolio, asset, and a position."""
    basket = None
    basket_id = None
    if with_basket:
        # Reuse the preset basket if seeded, else create one
        r = await client.get("/api/v1/baskets/")
        baskets = r.json()
        if baskets:
            basket = baskets[0]
            basket_id = basket["id"]
    account = await make_account()
    portfolio = await make_portfolio(account=account, basket_id=basket_id, name="Report PF")
    asset = await make_asset(symbol="AAPL", sector="Technology")

    from decimal import Decimal

    from portfolio_manager.models import Position

    pos = Position(
        portfolio_id=portfolio["id"],
        asset_id=asset.id,
        quantity=Decimal("10"),
        avg_cost_basis=Decimal("100"),
        current_price=Decimal("150"),
        market_value=Decimal("1500"),
        unrealized_gain=Decimal("500"),
        unrealized_gain_pct=Decimal("50.0000"),
    )
    db_session.add(pos)
    await db_session.commit()
    return portfolio, basket


# ── Report route ────────────────────────────────────────────────────────


class TestReportRoute:
    async def test_requires_auth(self, client):
        import uuid

        r = await client.get(f"/api/v1/reports/portfolio/{uuid.uuid4()}")
        assert r.status_code == 401

    async def test_invalid_portfolio_id(self, auth_client):
        r = await auth_client.get("/api/v1/reports/portfolio/not-a-uuid")
        assert r.status_code == 404

    async def test_portfolio_not_found(self, auth_client):
        import uuid

        r = await auth_client.get(f"/api/v1/reports/portfolio/{uuid.uuid4()}")
        assert r.status_code == 404

    async def test_report_html_generated(
        self, auth_client, make_account, make_portfolio, make_asset, db_session, fake_data_feed
    ):
        """End-to-end: report returns valid HTML without crashing.

        This exercises the two crash bugs:
          - ``float(sum(...), Decimal("0"))`` TypeError (misplaced paren)
          - ``portfolio.basket`` async lazy-load MissingGreenlet
        """
        pf, _basket = await _seed_portfolio_with_positions(
            auth_client, make_account, make_portfolio, make_asset, db_session
        )
        r = await auth_client.get(f"/api/v1/reports/portfolio/{pf['id']}")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("text/html")
        assert "attachment" in r.headers.get("content-disposition", "")
        body = r.text
        assert "<html" in body
        assert "Report PF" in body  # portfolio name
        # P&L column must be currency, not a percent
        assert "+$500.00" in body  # (10*150) - (10*100) = 500
        assert "+500.00%" not in body  # the old bug formatted $500 as +500.00%

    async def test_report_includes_basket_row(
        self, auth_client, make_account, make_portfolio, make_asset, db_session, fake_data_feed
    ):
        """Basket allocation section renders and accesses portfolio.basket eagerly."""
        pf, basket = await _seed_portfolio_with_positions(
            auth_client, make_account, make_portfolio, make_asset, db_session, with_basket=True
        )
        r = await auth_client.get(f"/api/v1/reports/portfolio/{pf['id']}")
        assert r.status_code == 200, r.text
        body = r.text
        assert "Basket Allocation" in body
        # the portfolio's basket name should appear somewhere
        assert basket is not None
        assert basket["name"] in body

    async def test_report_with_no_positions(self, auth_client, make_account, make_portfolio, fake_data_feed):
        """Empty portfolio still renders (no crash on empty sum)."""
        account = await make_account()
        pf = await make_portfolio(account=account, name="Empty PF")
        r = await auth_client.get(f"/api/v1/reports/portfolio/{pf['id']}")
        assert r.status_code == 200, r.text
        assert "Empty PF" in r.text
        assert "No positions" in r.text

    async def test_report_negative_pnl(
        self, auth_client, make_account, make_portfolio, make_asset, db_session, fake_data_feed
    ):
        """Negative P&L KPI must render with a minus sign (not as a positive)."""
        account = await make_account()
        pf = await make_portfolio(account=account, name="Loss PF")
        asset = await make_asset(symbol="LOSS")

        from decimal import Decimal

        from portfolio_manager.models import Position

        db_session.add(
            Position(
                portfolio_id=pf["id"],
                asset_id=asset.id,
                quantity=Decimal("10"),
                avg_cost_basis=Decimal("200"),
                current_price=Decimal("150"),
                market_value=Decimal("1500"),
                unrealized_gain=Decimal("-500"),
                unrealized_gain_pct=Decimal("-25.0000"),
            )
        )
        await db_session.commit()

        r = await auth_client.get(f"/api/v1/reports/portfolio/{pf['id']}")
        assert r.status_code == 200, r.text
        body = r.text
        # KPI shows -$500.00 (with minus), not $500.00
        assert "-$500.00" in body
        assert "+$500.00" not in body
        # position P&L column shows -$500.00
        assert "-$500.00" in body

    async def test_report_other_user_cannot_access(
        self, client, make_user, make_account, make_portfolio, fake_data_feed
    ):
        """A different user cannot generate a report for someone else's portfolio."""
        # owner creates portfolio (using the shared client which auth_client would set up)
        import secrets
        import uuid

        email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
        password = secrets.token_urlsafe(12)
        await client.post(
            "/auth/jwt/register",
            json={"email": email, "password": password, "display_name": "Owner"},
        )
        login = await client.post("/auth/jwt/login", data={"username": email, "password": password})
        client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})

        account = await make_account()
        pf = await make_portfolio(account=account, name="Secret PF")

        # second user takes over the shared client
        other = await make_user(display_name="Other")
        client.headers.update({"Authorization": f"Bearer {other['token']}"})
        r = await client.get(f"/api/v1/reports/portfolio/{pf['id']}")
        assert r.status_code == 404
