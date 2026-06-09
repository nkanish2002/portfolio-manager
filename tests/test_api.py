"""Tests for API endpoints using httpx.AsyncClient."""
import sys
import os
import uuid

# Ensure the src directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import asyncio
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
async def db_session():
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
class TestPortfoliosAPI:
    @pytest_asyncio.fixture
    async def client(self, db_session):
        """Create an async test client with a fresh DB session."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac
        app.dependency_overrides.clear()

    async def test_create_portfolio(self, client):
        response = await client.post("/api/v1/portfolios/", json={
            "name": "Test Portfolio",
            "description": "A test portfolio",
            "currency": "USD"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Portfolio"
        assert data["currency"] == "USD"
        assert data["position_count"] == 0
        assert data["total_value"] == 0.0

    async def test_list_portfolios(self, client):
        # Create a portfolio first
        await client.post("/api/v1/portfolios/", json={
            "name": "Test Portfolio 1",
            "currency": "USD"
        })
        await client.post("/api/v1/portfolios/", json={
            "name": "Test Portfolio 2",
            "currency": "EUR"
        })

        response = await client.get("/api/v1/portfolios/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {d["name"] for d in data}
        assert "Test Portfolio 1" in names
        assert "Test Portfolio 2" in names

    async def test_get_portfolio(self, client):
        # Create a portfolio
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Get Test",
            "currency": "USD"
        })
        portfolio_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/portfolios/{portfolio_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test"
        assert data["id"] == portfolio_id

    async def test_get_portfolio_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/portfolios/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_delete_portfolio(self, client):
        # Create a portfolio
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Delete Me",
            "currency": "USD"
        })
        portfolio_id = create_resp.json()["id"]

        # Delete it
        response = await client.delete(f"/api/v1/portfolios/{portfolio_id}")
        assert response.status_code == 204

        # Verify it's gone
        response = await client.get(f"/api/v1/portfolios/{portfolio_id}")
        assert response.status_code == 404

    async def test_add_position(self, client):
        # Create a portfolio
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Position Test",
            "currency": "USD"
        })
        portfolio_id = create_resp.json()["id"]

        # Add a position
        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "AAPL",
            "quantity": 100,
            "price": 150.0
        })
        assert response.status_code == 201
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["quantity"] == 100
        assert data["price"] == 150.0
        assert data["market_value"] == 15000.0
        assert data["gain"] == 0.0

    async def test_add_transaction(self, client):
        # Create a portfolio
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Transaction Test",
            "currency": "USD"
        })
        portfolio_id = create_resp.json()["id"]

        # Add a transaction
        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
            "symbol": "MSFT",
            "transaction_type": "buy",
            "quantity": 50,
            "price": 300.0,
            "fees": 5.0
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "recorded"
        assert "id" in data

    async def test_refresh_prices(self, client):
        # Create a portfolio and position
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": "Refresh Test",
            "currency": "USD"
        })
        portfolio_id = create_resp.json()["id"]

        await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "symbol": "AAPL",
            "quantity": 10,
            "price": 100.0
        })

        # Refresh prices (will fail to fetch from yfinance in test env, but should not crash)
        response = await client.post(f"/api/v1/portfolios/{portfolio_id}/positions/refresh")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "AAPL"

    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
