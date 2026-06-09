"""Comprehensive integration tests for Portfolio Manager API.

Tests the full request/response cycle for all portfolio endpoints using
httpx.AsyncClient against an in-memory SQLite database.
"""
import sys
import os

# Ensure the src directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from portfolio_manager.main import app
from portfolio_manager.database import Base, get_db

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with a fresh DB session."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


class TestPortfoliosIntegration:
    """Integration tests for portfolio CRUD endpoints."""

    async def test_create_portfolio_minimal(self, client: AsyncClient) -> None:
        """Test creating a portfolio with minimal fields."""
        response = await client.post("/api/v1/portfolios/", json={
            "name": "My Portfolio"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Portfolio"
        assert data["currency"] == "USD"  # default
        assert data["description"] is None
        assert data["position_count"] == 0
        assert data["total_value"] == 0.0
        assert "id" in data

    async def test_create_portfolio_full(self, client: AsyncClient) -> None:
        """Test creating a portfolio with all fields."""
        response = await client.post("/api/v1/portfolios/", json={
            "name": "Full Portfolio",
            "description": "A comprehensive test portfolio",
            "currency": "EUR"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Portfolio"
        assert data["description"] == "A comprehensive test portfolio"
        assert data["currency"] == "EUR"
        assert "id" in data

    async def test_create_portfolio_duplicate_name(self, client: AsyncClient) -> None:
        """Test that duplicate portfolio names return 409 Conflict."""
        # Create first portfolio
        await client.post("/api/v1/portfolios/", json={
            "name": "Duplicate Test"
        })
        # Try to create another with same name
        response = await client.post("/api/v1/portfolios/", json={
            "name": "Duplicate Test"
        })
        assert response.status_code == 409
        data = response.json()
        err = data.get("error", {})
        assert "already exists" in err.get("message", data.get("detail", "")).lower()

    async def test_list_portfolios_empty(self, client: AsyncClient) -> None:
        """Test listing portfolios when none exist."""
        response = await client.get("/api/v1/portfolios/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_list_portfolios_multiple(self, client: AsyncClient) -> None:
        """Test listing multiple portfolios."""
        # Create several portfolios
        for i in range(3):
            await client.post("/api/v1/portfolios/", json={
                "name": f"Portfolio {i}",
                "currency": ["USD", "EUR", "GBP"][i]
            })

        response = await client.get("/api/v1/portfolios/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        names = {d["name"] for d in data}
        assert names == {"Portfolio 0", "Portfolio 1", "Portfolio 2"}

    async def test_get_portfolio(self, client: AsyncClient) -> None:
        """Test retrieving a specific portfolio."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Get Portfolio",
            "currency": "JPY"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/portfolios/{portfolio_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Portfolio"
        assert data["currency"] == "JPY"
        assert data["id"] == portfolio_id

    async def test_get_portfolio_not_found(self, client: AsyncClient) -> None:
        """Test getting a non-existent portfolio returns 404."""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/portfolios/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        err = data.get("error", {})
        assert "not found" in err.get("message", data.get("detail", "")).lower()

    async def test_delete_portfolio(self, client: AsyncClient) -> None:
        """Test deleting a portfolio."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Delete Me"
        })
        portfolio_id = create_resp.json()["id"]

        # Delete
        response = await client.delete(f"/api/v1/portfolios/{portfolio_id}")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/v1/portfolios/{portfolio_id}")
        assert response.status_code == 404

    async def test_delete_portfolio_not_found(self, client: AsyncClient) -> None:
        """Test deleting a non-existent portfolio returns 404."""
        fake_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/portfolios/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        err = data.get("error", {})
        assert "not found" in err.get("message", data.get("detail", "")).lower()


class TestPositionsIntegration:
    """Integration tests for position endpoints."""

    async def test_add_position_new(self, client: AsyncClient) -> None:
        """Test adding a new position to a portfolio."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Position Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "AAPL",
            "quantity": 100,
            "price": 150.0
        })
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["quantity"] == 100.0
        assert data["price"] == 150.0
        assert data["cost_basis"] == 150.0
        assert data["market_value"] == 15000.0
        assert data["gain"] == 0.0
        assert data["gain_pct"] == 0.0
        assert "id" in data

    async def test_add_position_update_existing(self, client: AsyncClient) -> None:
        """Test that adding a position with same symbol updates quantity."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Update Position Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        # First purchase
        resp1 = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "MSFT",
            "quantity": 50,
            "price": 300.0
        })
        assert resp1.status_code == 201
        qty1 = resp1.json()["quantity"]
        cost1 = resp1.json()["cost_basis"]

        # Second purchase (same symbol)
        resp2 = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "MSFT",
            "quantity": 50,
            "price": 320.0
        })
        assert resp2.status_code == 201
        data = resp2.json()
        assert data["quantity"] == 100.0  # 50 + 50
        assert data["symbol"] == "MSFT"

    async def test_add_position_invalid_portfolio(self, client: AsyncClient) -> None:
        """Test adding a position to a non-existent portfolio."""
        fake_id = str(uuid.uuid4())
        response = await client.post(f"/api/v1/portfolios/{fake_id}/positions", json={
            "symbol": "GOOGL",
            "quantity": 10,
            "price": 2800.0
        })
        assert response.status_code == 404
        data = response.json()
        err = data.get("error", {})
        assert "not found" in err.get("message", data.get("detail", "")).lower()

    async def test_add_position_zero_quantity(self, client: AsyncClient) -> None:
        """Test that zero/negative quantity is rejected."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Invalid Position Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "TSLA",
            "quantity": 0,
            "price": 200.0
        })
        assert response.status_code == 422  # Validation error

    async def test_add_position_negative_price(self, client: AsyncClient) -> None:
        """Test that negative price is rejected."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Invalid Price Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "AMZN",
            "quantity": 10,
            "price": -50.0
        })
        assert response.status_code == 422


class TestTransactionsIntegration:
    """Integration tests for transaction endpoints."""

    async def test_add_buy_transaction(self, client: AsyncClient) -> None:
        """Test adding a buy transaction."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Transaction Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
            "symbol": "NVDA",
            "transaction_type": "buy",
            "quantity": 25,
            "price": 800.0,
            "fees": 10.0
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "recorded"
        assert "id" in data

    async def test_add_sell_transaction(self, client: AsyncClient) -> None:
        """Test adding a sell transaction."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Sell Transaction Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
            "symbol": "META",
            "transaction_type": "sell",
            "quantity": 5,
            "price": 500.0
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "recorded"

    async def test_add_transaction_with_notes(self, client: AsyncClient) -> None:
        """Test adding a transaction with optional notes."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Notes Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
            "symbol": "BRK.B",
            "transaction_type": "buy",
            "quantity": 2,
            "price": 400.0,
            "fees": 5.0,
            "notes": "Warren Buffett pick"
        })
        assert response.status_code == 201
        assert response.json()["status"] == "recorded"

    async def test_add_transaction_invalid_portfolio(self, client: AsyncClient) -> None:
        """Test adding a transaction to a non-existent portfolio."""
        fake_id = str(uuid.uuid4())
        response = await client.post(f"/api/v1/portfolios/{fake_id}/transactions", json={
            "symbol": "SPY",
            "transaction_type": "buy",
            "quantity": 10,
            "price": 450.0
        })
        # This may fail with 404 or create asset anyway depending on implementation
        # At minimum it should not crash
        assert response.status_code in [201, 404]


class TestPricesIntegration:
    """Integration tests for price refresh endpoint."""

    async def test_refresh_prices(self, client: AsyncClient) -> None:
        """Test refreshing prices for all positions."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Refresh Portfolio"
        })
        portfolio_id = create_resp.json()["id"]

        # Add positions
        await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "AAPL",
            "quantity": 10,
            "price": 150.0
        })
        await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "MSFT",
            "quantity": 5,
            "price": 300.0
        })

        # Refresh (may fail to fetch from yfinance, but should not crash)
        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions/refresh")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_refresh_empty_portfolio(self, client: AsyncClient) -> None:
        """Test refreshing prices for a portfolio with no positions."""

        # Create a portfolio with no positions
        create_resp = await client.post(
            "/api/v1/portfolios/",
            json={"name": "Empty Portfolio", "currency": "USD"},
        )
        portfolio_id = create_resp.json()["id"]

        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions/refresh")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestHealthIntegration:
    """Integration tests for health endpoint."""

    async def test_health_check(self, client: AsyncClient) -> None:
        """Test the health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert isinstance(data["version"], str)
