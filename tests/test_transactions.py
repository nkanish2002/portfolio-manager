"""Transaction route tests — record buy/sell, FIFO realized P&L, history."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


class TestTransactions:
    async def test_record_buy_creates_position(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="AAPL")
        pf = await make_portfolio()
        r = await auth_client.post(
            f"/api/v1/portfolios/{pf['id']}/transactions",
            json={
                "asset_id": str(asset.id),
                "type": "buy",
                "quantity": "10",
                "price": "100",
                "fees": "0",
                "trade_date": datetime.now(UTC).isoformat(),
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["realized_gain"] is None

        # position was created as a side effect
        positions = (await auth_client.get(f"/api/v1/portfolios/{pf['id']}/positions")).json()
        assert len(positions) == 1
        assert Decimal(positions[0]["quantity"]) == Decimal("10")
        assert Decimal(positions[0]["avg_cost_basis"]) == Decimal("100")

    async def test_fifo_realized_gain_on_sell(self, auth_client, make_account, make_portfolio, make_asset):
        # buy 10@100, buy 10@110, sell 5@120 → realized = $100
        asset = await make_asset(symbol="MSFT")
        pf = await make_portfolio()
        url = f"/api/v1/portfolios/{pf['id']}/transactions"

        async def txn(t, qty, price):
            r = await auth_client.post(url, json={
                "asset_id": str(asset.id), "type": t, "quantity": str(qty),
                "price": str(price), "trade_date": datetime.now(UTC).isoformat(),
            })
            assert r.status_code == 201, r.text
            return r.json()

        await txn("buy", 10, 100)
        await txn("buy", 10, 110)
        sell = await txn("sell", 5, 120)
        assert sell["realized_gain"] is not None
        assert Decimal(sell["realized_gain"]) == Decimal("100")

        # remaining position: 15 shares (20 - 5)
        positions = (await auth_client.get(f"/api/v1/portfolios/{pf['id']}/positions")).json()
        assert Decimal(positions[0]["quantity"]) == Decimal("15")

    async def test_transaction_history_filters(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="GOOG")
        pf = await make_portfolio()
        url = f"/api/v1/portfolios/{pf['id']}/transactions"

        for i, (t, qty, price) in enumerate([("buy", 10, 100), ("buy", 5, 110), ("sell", 3, 120)]):
            await auth_client.post(url, json={
                "asset_id": str(asset.id), "type": t, "quantity": str(qty),
                "price": str(price), "trade_date": datetime.now(UTC).isoformat(),
                "notes": f"t{i}",
            })

        all_txns = (await auth_client.get(url)).json()
        assert len(all_txns) == 3

        sells = (await auth_client.get(f"{url}?type=sell")).json()
        assert len(sells) == 1
        assert sells[0]["type"] == "sell"

        by_asset = (await auth_client.get(f"{url}?asset_id={asset.id}")).json()
        assert len(by_asset) == 3

    async def test_history_ordered_descending(self, auth_client, make_account, make_portfolio, make_asset):
        asset = await make_asset(symbol="TSLA")
        pf = await make_portfolio()
        url = f"/api/v1/portfolios/{pf['id']}/transactions"
        for price in (100, 110, 120):
            await auth_client.post(url, json={
                "asset_id": str(asset.id), "type": "buy", "quantity": "1",
                "price": str(price),
                "trade_date": datetime(2026, 1, price // 100 + 1, tzinfo=UTC).isoformat(),
            })
        txns = (await auth_client.get(url)).json()
        # ordered by trade_date desc
        assert Decimal(txns[0]["price"]) == Decimal("120")
        assert Decimal(txns[-1]["price"]) == Decimal("100")

    async def test_transactions_require_auth(self, client):
        assert (await client.get("/api/v1/portfolios/x/transactions")).status_code == 401
