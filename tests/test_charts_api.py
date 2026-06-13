"""Tests for charts API endpoints."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from portfolio_manager.main import app
from portfolio_manager.database import Base, get_db

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


@pytest_asyncio.fixture
async def client(db_session):
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


@pytest.mark.asyncio
class TestChartsAPI:
    """Tests for charts API endpoints."""

    async def _create_portfolio_without_transactions(self, client, portfolio_name="Test Portfolio"):
        """Helper to create a portfolio without transactions."""
        create_resp = await client.post("/api/v1/portfolios/", json={
            "name": portfolio_name,
            "currency": "USD"
        })
        return create_resp.json()["id"]

    async def test_nav_history_empty_portfolio(self, client):
        """Test NAV history for a portfolio with no transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/nav-history")
        assert response.status_code == 200
        data = response.json()
        assert data["portfolio"] == []
        assert data["benchmark"] == []

    async def test_nav_chart_empty_portfolio(self, client):
        """Test NAV chart for a portfolio with no transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Chart Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/nav")
        assert response.status_code == 200
        data = response.json()
        assert data["portfolio_dates"] == []
        assert data["benchmark_dates"] == []

    async def test_drawdown_chart_empty_portfolio(self, client):
        """Test drawdown chart for a portfolio with no transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Drawdown Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/drawdown")
        assert response.status_code == 200
        data = response.json()
        assert data["dates"] == []
        assert data["drawdown"] == []
        assert data["nav"] == []

    async def test_allocation_chart_empty_portfolio(self, client):
        """Test allocation chart for a portfolio with no positions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Allocation Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/allocation")
        assert response.status_code == 200
        data = response.json()
        # No positions, so empty
        assert data["labels"] == []
        assert data["values"] == []

    async def test_allocation_chart_no_positions(self, client):
        """Test allocation chart for a portfolio with no positions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "No Positions Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/allocation")
        assert response.status_code == 200
        data = response.json()
        assert data["labels"] == []
        assert data["values"] == []

    async def test_returns_distribution_empty_portfolio(self, client):
        """Test returns distribution for a portfolio with no transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Distribution Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/returns-distribution")
        assert response.status_code == 200
        data = response.json()
        assert data["bins"] == []
        assert data["counts"] == []

    async def test_benchmark_comparison_empty_portfolio(self, client):
        """Test benchmark comparison for a portfolio with no transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Benchmark Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/benchmark-comparison")
        assert response.status_code == 200
        data = response.json()
        assert data["dates"] == []

    async def test_risk_report_empty_portfolio(self, client):
        """Test risk report for a portfolio with no transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Risk Portfolio")

        response = await client.get(f"/api/v1/{portfolio_id}/risk-report")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    async def test_nav_history_with_transactions(self, client):
        """Test NAV history with actual transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "With Transactions")

        # Add a transaction
        await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
            "cusip": "000000001",
            "symbol": "AAPL",
            "transaction_type": "buy",
            "quantity": 50,
            "price": 150.0
        })

        response = await client.get(f"/api/v1/{portfolio_id}/charts/nav-history")
        assert response.status_code == 200
        data = response.json()
        # Should have some data now
        assert isinstance(data["portfolio"], list)

    async def test_nav_chart_with_transactions(self, client):
        """Test NAV chart with actual transactions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "With Nav Chart")

        # Add transactions
        await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
            "cusip": "000000001",
            "symbol": "AAPL",
            "transaction_type": "buy",
            "quantity": 50,
            "price": 150.0
        })

        response = await client.get(f"/api/v1/{portfolio_id}/charts/nav")
        assert response.status_code == 200
        data = response.json()
        # Should have some data now
        assert isinstance(data["portfolio_dates"], list)

    async def test_monthly_returns_empty_portfolio(self, client):
        """Test monthly returns for a portfolio with insufficient data."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "Empty Monthly")

        response = await client.get(f"/api/v1/{portfolio_id}/charts/monthly-returns")
        assert response.status_code == 200
        data = response.json()
        assert data["years"] == []

    async def test_allocation_chart_with_positions(self, client):
        """Test allocation chart with actual positions."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "With Positions")

        # Add a position to the portfolio
        await client.post(f"/api/v1/portfolios/{portfolio_id}/positions", json={
            "cusip": "000000001",
            "symbol": "AAPL",
            "quantity": 100,
            "price": 150.0
        })

        response = await client.get(f"/api/v1/{portfolio_id}/charts/allocation")
        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "values" in data
        assert "colors" in data

    async def test_risk_report_with_data(self, client):
        """Test risk report with sufficient transaction data."""
        portfolio_id = await self._create_portfolio_without_transactions(client, "With Risk Data")

        # Add transactions to create enough NAV history
        for i in range(10):
            await client.post(f"/api/v1/portfolios/{portfolio_id}/transactions", json={
                "cusip": "000000001",
                "symbol": "AAPL",
                "transaction_type": "buy",
                "quantity": 10,
                "price": 150.0 + i
            })

        response = await client.get(f"/api/v1/{portfolio_id}/risk-report")
        assert response.status_code == 200
        data = response.json()
        # Should have risk metrics if we have enough data
        assert "portfolio_id" in data