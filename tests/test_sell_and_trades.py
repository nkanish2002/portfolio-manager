"""Integration tests for sell endpoint and trade audit trail."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from portfolio_manager.database import Base, get_db
from portfolio_manager.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def client():
    """Create test client with isolated in-memory DB."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


class TestSellEndpoint:
    """Integration tests for the sell position endpoint."""

    async def test_full_sell(self, client: AsyncClient) -> None:
        """Sell entire position — position should be removed."""
        # Create portfolio
        portfolio = await client.post("/api/v1/portfolios/", json={
            "name": "Test Portfolio",
            "currency": "USD",
        })
        assert portfolio.status_code == 201
        portfolio_id = portfolio.json()["id"]

        # Create position via positions endpoint (handles asset creation + transaction)
        pos = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 100, "price": 150.0},
        )
        assert pos.status_code == 201, f"Position creation failed: {pos.text}"

        # Sell all 100 shares at $160
        sell = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "AAPL", "quantity": 100, "price": 160.0, "fees": 5, "notes": "Full exit"},
        )
        assert sell.status_code == 201, f"Sell failed: {sell.text}"
        data = sell.json()
        assert data["status"] == "sold"
        assert data["symbol"] == "AAPL"
        assert data["quantity_sold"] == 100
        assert data["price"] == 160.0
        assert data["realized_pnl"] == 16000 - (150 * 100) - 5  # 995
        assert data["remaining_quantity"] == 0

        # Verify position was removed
        positions = await client.get(f"/api/v1/portfolios/{portfolio_id}/positions")
        assert positions.json() == []

        # Verify transaction was recorded
        trades = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades")
        assert trades.status_code == 200, f"Trades query failed: {trades.text}"
        trade_list = trades.json()
        sell_trades = [t for t in trade_list if t["type"] == "SELL"]
        assert len(sell_trades) == 1
        assert sell_trades[0]["symbol"] == "AAPL"
        assert sell_trades[0]["p_and_l"] == 995

    async def test_partial_sell(self, client: AsyncClient) -> None:
        """Sell half of a position — position should remain with reduced qty."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        # Create position
        pos = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "TSLA", "quantity": 100, "price": 200.0},
        )
        assert pos.status_code == 201

        # Sell 40 shares at $210
        sell = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "TSLA", "quantity": 40, "price": 210.0, "fees": 3},
        )
        assert sell.status_code == 201, f"Sell failed: {sell.text}"
        data = sell.json()
        assert data["quantity_sold"] == 40
        assert data["remaining_quantity"] == 60
        assert data["realized_pnl"] == (210 * 40) - (200 * 40) - 3  # 397

        # Verify position still exists with 60 shares
        positions = await client.get(f"/api/v1/portfolios/{portfolio_id}/positions")
        pos_list = positions.json()
        assert len(pos_list) == 1
        assert pos_list[0]["quantity"] == 60

    async def test_sell_more_than_position(self, client: AsyncClient) -> None:
        """Trying to sell more than we own should return 400."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "MSFT", "quantity": 10, "price": 300.0},
        )

        sell = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "MSFT", "quantity": 20, "price": 310.0},
        )
        assert sell.status_code == 400, f"Expected 400, got {sell.status_code}: {sell.text}"
        err = sell.json().get("error", {})
        assert "Cannot sell" in err.get("message", sell.json().get("detail", ""))

    async def test_sell_nonexistent_position(self, client: AsyncClient) -> None:
        """Selling a symbol that isn't in the portfolio returns 404."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        sell = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "XYZ", "quantity": 1, "price": 10.0},
        )
        assert sell.status_code == 404


class TestTradeAuditTrail:
    """Integration tests for the trade audit trail API."""

    async def test_trades_list(self, client: AsyncClient) -> None:
        """Get all trades for a portfolio."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        # Create positions (creates BUY transactions)
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 50, "price": 100.0},
        )

        # Sell some (creates SELL transaction)
        sell = await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "AAPL", "quantity": 10, "price": 110.0},
        )
        assert sell.status_code == 201

        trades = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades")
        assert trades.status_code == 200, f"Trades failed: {trades.text}"
        trade_list = trades.json()
        assert len(trade_list) == 2
        types = {t["type"] for t in trade_list}
        assert "BUY" in types
        assert "SELL" in types

    async def test_trades_filter_by_type(self, client: AsyncClient) -> None:
        """Filter trades by type (BUY/SELL)."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 50, "price": 100.0},
        )
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "AAPL", "quantity": 10, "price": 110.0},
        )

        buys = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades", params={"trade_type": "BUY"})
        assert buys.status_code == 200, f"Buys query failed: {buys.text}"
        assert all(t["type"] == "BUY" for t in buys.json())

        sells = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades", params={"trade_type": "SELL"})
        assert sells.status_code == 200, f"Sells query failed: {sells.text}"
        assert all(t["type"] == "SELL" for t in sells.json())

    async def test_trades_filter_by_symbol(self, client: AsyncClient) -> None:
        """Filter trades by symbol."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 50, "price": 100.0},
        )
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "MSFT", "quantity": 20, "price": 300.0},
        )

        aapl_trades = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades", params={"symbol": "AAPL"})
        assert aapl_trades.status_code == 200, f"AAPL query failed: {aapl_trades.text}"
        assert all(t["symbol"] == "AAPL" for t in aapl_trades.json())

        msft_trades = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades", params={"symbol": "MSFT"})
        assert msft_trades.status_code == 200, f"MSFT query failed: {msft_trades.text}"
        assert all(t["symbol"] == "MSFT" for t in msft_trades.json())

    async def test_trade_summary(self, client: AsyncClient) -> None:
        """Get trade summary with realized P&L."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 100, "price": 100.0},
        )
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions/sell",
            json={"symbol": "AAPL", "quantity": 50, "price": 90.0},
        )

        summary = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades/summary")
        assert summary.status_code == 200, f"Summary failed: {summary.text}"
        data = summary.json()
        assert data["total_trades"] == 2
        assert data["total_buys"] == 1
        assert data["total_sells"] == 1
        assert data["realized_loss"] == 500  # (100-90) * 50
        assert data["net_realized_p_and_l"] == -500

    async def test_trades_sort_by_date_desc(self, client: AsyncClient) -> None:
        """Trades should be sorted by date descending by default."""
        portfolio = await client.post("/api/v1/portfolios/", json={"name": "Test", "currency": "USD"})
        portfolio_id = portfolio.json()["id"]

        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 10, "price": 100.0},
        )
        await client.post(
            f"/api/v1/portfolios/{portfolio_id}/positions",
            json={"symbol": "AAPL", "quantity": 20, "price": 110.0},
        )

        trades = await client.get(f"/api/v1/portfolios/{portfolio_id}/trades", params={"sort_by": "date", "sort_order": "desc"})
        assert trades.status_code == 200, f"Sort query failed: {trades.text}"
        trade_list = trades.json()
        assert len(trade_list) == 2
        assert trade_list[0]["transaction_date"] >= trade_list[1]["transaction_date"]
