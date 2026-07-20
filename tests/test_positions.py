"""Position route tests — add, list, refresh prices, move between baskets."""

from __future__ import annotations

from decimal import Decimal


class TestPositions:
    async def test_add_and_list_position(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="AAPL")
        pf = await make_portfolio()
        r = await auth_client.post(
            f"/api/v1/portfolios/{pf['id']}/positions",
            json={
                "asset_id": str(asset.id),
                "quantity": "10",
                "avg_cost_basis": "100",
                "current_price": "150",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert Decimal(body["quantity"]) == Decimal("10")
        assert Decimal(body["market_value"]) == Decimal("1500")
        assert Decimal(body["unrealized_gain"]) == Decimal("500")

        listing = await auth_client.get(f"/api/v1/portfolios/{pf['id']}/positions")
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        # The list endpoint joins the asset and exposes its ticker symbol so the
        # frontend WebSocket client can subscribe by symbol (not the asset UUID).
        assert listing.json()[0]["symbol"] == "AAPL"

    async def test_upsert_existing_position_updates_quantity(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="MSFT")
        pf = await make_portfolio()
        url = f"/api/v1/portfolios/{pf['id']}/positions"
        await auth_client.post(url, json={"asset_id": str(asset.id), "quantity": "10", "avg_cost_basis": "100", "current_price": "100"})
        r = await auth_client.post(url, json={"asset_id": str(asset.id), "quantity": "20", "avg_cost_basis": "110", "current_price": "120"})
        assert r.status_code == 201
        assert Decimal(r.json()["quantity"]) == Decimal("20")
        listing = await auth_client.get(url)
        assert len(listing.json()) == 1  # not duplicated (unique asset/portfolio)

    async def test_refresh_prices_updates_market_value(self, auth_client, make_account, make_portfolio, make_asset, fake_data_feed):
        asset = await make_asset(symbol="TSLA")
        pf = await make_portfolio()
        await auth_client.post(
            f"/api/v1/portfolios/{pf['id']}/positions",
            json={"asset_id": str(asset.id), "quantity": "10", "avg_cost_basis": "200", "current_price": "200"},
        )
        fake_data_feed.add_quote("TSLA", 250.0, prev_close=200.0)
        r = await auth_client.post(f"/api/v1/portfolios/{pf['id']}/positions/refresh")
        assert r.status_code == 200, r.text
        pos = r.json()[0]
        assert Decimal(pos["current_price"]) == Decimal("250")
        assert Decimal(pos["market_value"]) == Decimal("2500")
        assert Decimal(pos["unrealized_gain"]) == Decimal("500")  # (250-200)*10

    async def test_move_position_to_other_portfolio(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="GOOG")
        src = await make_portfolio(name="Src")
        target = await make_portfolio(name="Target")
        created = (await auth_client.post(
            f"/api/v1/portfolios/{src['id']}/positions",
            json={"asset_id": str(asset.id), "quantity": "5", "avg_cost_basis": "100", "current_price": "100"},
        )).json()

        r = await auth_client.post(
            f"/api/v1/portfolios/{src['id']}/positions/{created['id']}/move",
            json={"target_portfolio_id": target["id"]},
        )
        assert r.status_code == 200, r.text
        assert r.json()["portfolio_id"] == target["id"]

        # source portfolio now has no positions
        src_positions = (await auth_client.get(f"/api/v1/portfolios/{src['id']}/positions")).json()
        assert len(src_positions) == 0
        target_positions = (await auth_client.get(f"/api/v1/portfolios/{target['id']}/positions")).json()
        assert len(target_positions) == 1

    async def test_move_merges_into_existing_target_position(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="NVDA")
        src = await make_portfolio(name="Src")
        target = await make_portfolio(name="Target")
        # same asset in both
        await auth_client.post(
            f"/api/v1/portfolios/{src['id']}/positions",
            json={"asset_id": str(asset.id), "quantity": "10", "avg_cost_basis": "100", "current_price": "100"},
        )
        await auth_client.post(
            f"/api/v1/portfolios/{target['id']}/positions",
            json={"asset_id": str(asset.id), "quantity": "10", "avg_cost_basis": "120", "current_price": "120"},
        )
        src_pos = (await auth_client.get(f"/api/v1/portfolios/{src['id']}/positions")).json()[0]
        r = await auth_client.post(
            f"/api/v1/portfolios/{src['id']}/positions/{src_pos['id']}/move",
            json={"target_portfolio_id": target["id"]},
        )
        assert r.status_code == 200
        # merged: single position in target with summed qty
        target_positions = (await auth_client.get(f"/api/v1/portfolios/{target['id']}/positions")).json()
        assert len(target_positions) == 1
        assert Decimal(target_positions[0]["quantity"]) == Decimal("20")

    async def test_positions_require_auth(self, client):
        assert (await client.get("/api/v1/portfolios/x/positions")).status_code == 401
