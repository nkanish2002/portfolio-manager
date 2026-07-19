"""Analytics route tests — risk, allocations, chart endpoints, basket analytics."""

from __future__ import annotations


async def _seed_portfolio_with_positions(
    auth_client, make_portfolio, make_asset, *, positions: list[tuple[str, float, float, float]]
):
    """Create a portfolio + positions. Each tuple: (symbol, qty, cost, price)."""
    pf = await make_portfolio(name="Analytics")
    for symbol, qty, cost, price in positions:
        asset = await make_asset(symbol=symbol, sector=f"Sector-{symbol}", region="United States")
        r = await auth_client.post(
            f"/api/v1/portfolios/{pf['id']}/positions",
            json={"asset_id": str(asset.id), "quantity": str(qty),
                  "avg_cost_basis": str(cost), "current_price": str(price)},
        )
        assert r.status_code == 201, r.text
    return pf


class TestAllocations:
    async def test_allocation_by_sector_sums_to_one(self, auth_client, make_portfolio, make_asset):
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset,
            positions=[("AAPL", 10, 100, 200), ("MSFT", 5, 100, 100), ("XOM", 2, 100, 300)],
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/analytics/allocations")
        assert r.status_code == 200, r.text
        body = r.json()
        assert {"by_sector", "by_region", "by_asset_class", "by_basket", "nav"}.issubset(body)
        total = sum(body["by_sector"].values())
        assert abs(total - 1.0) < 1e-6  # all sectors sum to 100%
        # nav = 2000 (10*200) + 500 (5*100) + 600 (2*300) = 3100
        assert abs(body["nav"] - 3100.0) < 1e-6

    async def test_allocation_chart_slices(self, auth_client, make_portfolio, make_asset):
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset,
            positions=[("AAPL", 10, 100, 200), ("MSFT", 5, 100, 100)],
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/charts/allocation?group_by=sector")
        assert r.status_code == 200
        slices = r.json()["slices"]
        assert len(slices) == 2
        assert abs(sum(s["pct"] for s in slices) - 1.0) < 1e-6


class TestRiskAndCharts:
    async def test_risk_endpoint_returns_metrics(self, auth_client, make_portfolio, make_asset, fake_data_feed):
        # give two assets deterministic rising prices for a NAV series
        fake_data_feed.add_history("AAPL", [100, 101, 102, 103, 104])
        fake_data_feed.add_history("MSFT", [50, 51, 52, 53, 54])
        fake_data_feed.add_history("SPY", [400, 402, 404, 406, 408])
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset,
            positions=[("AAPL", 10, 100, 104), ("MSFT", 20, 50, 54)],
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/analytics/risk?benchmark=SPY")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["benchmark"] == "SPY"
        metrics = body["metrics"]
        assert {"sharpe", "sortino", "max_drawdown", "var_95_parametric", "var_95_historical",
                "calmar", "ulcer_index", "annualized_return"}.issubset(metrics)
        assert {"beta", "alpha", "treynor"}.issubset(metrics)  # benchmark present
        for v in metrics.values():
            assert isinstance(v, (int, float))

    async def test_nav_chart_series(self, auth_client, make_portfolio, make_asset, fake_data_feed):
        fake_data_feed.add_history("AAPL", [100, 110, 105])
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset, positions=[("AAPL", 10, 100, 105)]
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/charts/nav")
        assert r.status_code == 200
        series = r.json()["series"]
        assert len(series) == 3
        assert all("date" in p and "nav" in p for p in series)
        # nav at each date = 10 shares * close
        assert series[0]["nav"] == pytest.approx(1000.0)
        assert series[1]["nav"] == pytest.approx(1100.0)

    async def test_drawdown_chart(self, auth_client, make_portfolio, make_asset, fake_data_feed):
        fake_data_feed.add_history("AAPL", [100, 120, 90, 110])
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset, positions=[("AAPL", 10, 100, 110)]
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/charts/drawdown")
        assert r.status_code == 200
        body = r.json()
        assert len(body["series"]) == 4
        assert body["max_drawdown"] <= 0.0
        # the deepest drawdown: 120 → 90 = -25%
        assert body["max_drawdown"] == pytest.approx(-0.25, abs=1e-6)

    async def test_monthly_returns_chart(self, auth_client, make_portfolio, make_asset, fake_data_feed):
        # ~2 months of daily data (Jan + into Feb) so there are >=2 month-buckets
        prices = [100 + i for i in range(35)]
        fake_data_feed.add_history("AAPL", prices)
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset, positions=[("AAPL", 10, 100, 134)]
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/charts/monthly-returns")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body["series"], list)
        if body["series"]:
            assert "month" in body["series"][0] and "return" in body["series"][0]

    async def test_benchmark_comparison_chart(self, auth_client, make_portfolio, make_asset, fake_data_feed):
        fake_data_feed.add_history("AAPL", [100, 110, 121])
        fake_data_feed.add_history("SPY", [400, 420, 440])
        pf = await _seed_portfolio_with_positions(
            auth_client, make_portfolio, make_asset, positions=[("AAPL", 10, 100, 121)]
        )
        r = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/charts/benchmark-comparison?benchmark=SPY")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["benchmark"] == "SPY"
        assert "comparison" in body
        assert {"tracking_error", "information_ratio"}.issubset(body["comparison"])
        assert len(body["series"]) == 3
        # both normalized to 1.0 at start
        assert body["series"][0]["portfolio"] == pytest.approx(1.0)
        assert body["series"][0]["benchmark"] == pytest.approx(1.0)

    async def test_empty_portfolio_returns_empty_series(self, auth_client, make_portfolio):
        pf = await make_portfolio(name="Empty")
        nav = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/charts/nav")
        assert nav.json()["series"] == []
        risk = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/analytics/risk")
        assert risk.status_code == 200


class TestBasketAnalytics:
    async def test_basket_analytics_aggregates(self, auth_client, make_account, make_basket, make_portfolio, make_asset):
        basket = await make_basket(name="HB")
        pf1 = await make_portfolio(basket_id=basket["id"], name="P1")
        pf2 = await make_portfolio(basket_id=basket["id"], name="P2")
        for pf, symbol, qty, cost, price in [
            (pf1, "AAPL", 10, 100, 200),
            (pf2, "MSFT", 5, 100, 150),
        ]:
            asset = await make_asset(symbol=symbol, sector="Tech")
            r = await auth_client.post(
                f"/api/v1/portfolios/{pf['id']}/positions",
                json={"asset_id": str(asset.id), "quantity": str(qty),
                      "avg_cost_basis": str(cost), "current_price": str(price)},
            )
            assert r.status_code == 201, r.text
        r = await auth_client.get(f"/api/v1/baskets/{basket['id']}/analytics")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["basket_name"] == "HB"
        assert body["portfolio_count"] == 2
        assert body["position_count"] == 2
        # nav = 10*200 + 5*150 = 2000 + 750 = 2750
        assert abs(body["nav"] - 2750.0) < 1e-6
        assert abs(sum(body["allocation_by_sector"].values()) - 1.0) < 1e-6


# `pytest` is used via pytest.approx in some asserts above
import pytest  # noqa: E402
