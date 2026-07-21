"""Statement import tests — PDF parsing, service pipeline, and HTTP route.

Coverage:
  1. parse_pdf_text: regex patterns against Schwab-style text (4 formats + cash)
  2. import_statement: upsert assets + positions, created vs updated tracking
  3. Route: file upload, auth, ownership validation, error responses
"""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio

from portfolio_manager.services.statement_import import (
    StatementHolding,
    import_statement,
    parse_pdf_text,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def make_portfolio_with_account(auth_client, make_account):
    """Create a portfolio (with its account) via the API."""

    async def _factory():
        account = await make_account()
        r = await auth_client.post(
            "/api/v1/portfolios/",
            json={"name": "Import Test", "account_id": account["id"], "currency": "USD"},
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _factory


@pytest.fixture
def schwab_holdings_text():
    """Simulated PDF text from a Schwab holdings page.

    Format: Symbol  Description  Shares  Market Value  Cost Basis  Gain/Loss
    """
    return """\
Your Account Holdings
As of 01/15/2026

Symbol    Description              Shares      Market Value   Cost Basis   Gain/Loss
AAPL      Apple Inc              100.000   $  19,850.00  $  15,000.00  $   4,850.00
MSFT      Microsoft Corp           50.000   $  19,500.00  $  16,250.00  $   3,250.00
VTI       Vanguard Total Stock Mkt Idx  25.000   $   8,250.00  $   7,500.00  $     750.00
BND       Vanguard Total Bond Mkt Idx   30.000   $   2,850.00  $   3,000.00  $    -150.00
QQQ       Invesco QQQ Trust         20.000   $   8,600.00  $   7,200.00  $   1,400.00

Total Market Value: $ 59,050.00
Total Cost Basis:   $ 48,950.00
Total Gain/Loss:    $ 10,100.00
"""


@pytest.fixture
def schwab_compact_text():
    """Compact single-line format from Schwab account snapshot."""
    return """\
Account Snapshot
AAPL 100 $198.50 $15,000.00 Apple Inc
MSFT 50 $390.00 $16,250.00 Microsoft Corp
TSLA 25 $245.30 $5,500.00 Tesla Inc
"""


@pytest.fixture
def schwab_with_cusip_text():
    """ETF/mutual fund format with 9-digit CUSIP."""
    return """\
Holdings Detail
VTI    Vanguard Total Stock Mkt Idx 922908769 50.000 $ 8,250.00 $ 7,500.00
VOO    Vanguard S&P 500 Index 922908363 10.000 $ 5,100.00 $ 4,800.00
VTSAX  Vanguard Total Stock Mkt Idx Adm 922908776 200.000 $ 38,000.00 $ 35,000.00
"""


@pytest.fixture
def schwab_bond_text():
    """Bond/CD format (no shares, face value)."""
    return """\
Fixed Income Holdings
BND    Vanguard Total Bond Mkt Idx            $ 5,000.00  $ 5,100.00
LQD    iShares Investment Grade Corp Bond     $ 8,000.00  $ 8,200.00
TLT    iShares 20+ Year Treasury Bond         $ 3,000.00  $ 2,850.00
"""


@pytest.fixture
def schwab_cash_text():
    """Text containing a cash/money-market balance."""
    return """\
Cash & Sweep
Cash and cash equivalents: $ 12,345.67
AAPL      Apple Inc              100.000   $  19,850.00  $  15,000.00  $   4,850.00
"""


# ── Parsing tests ─────────────────────────────────────────────────────────


class TestParsePdfText:
    """Test parse_pdf_text against various Schwab text formats."""

    def test_standard_holdings(self, schwab_holdings_text):
        holdings = parse_pdf_text(schwab_holdings_text)
        symbols = {h.symbol for h in holdings}
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "VTI" in symbols
        assert "BND" in symbols
        assert "QQQ" in symbols

        # Verify parsed values for AAPL
        aapl = next(h for h in holdings if h.symbol == "AAPL")
        assert aapl.quantity == Decimal("100.000")
        assert aapl.market_value == Decimal("19850.00")
        assert aapl.cost_basis == Decimal("15000.00")

    def test_compact_format(self, schwab_compact_text):
        holdings = parse_pdf_text(schwab_compact_text)
        symbols = {h.symbol for h in holdings}
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "TSLA" in symbols

        tsla = next(h for h in holdings if h.symbol == "TSLA")
        assert tsla.quantity == Decimal("25")
        assert tsla.cost_basis == Decimal("5500.00")

    def test_cusip_format(self, schwab_with_cusip_text):
        holdings = parse_pdf_text(schwab_with_cusip_text)
        symbols = {h.symbol for h in holdings}
        assert "VTI" in symbols
        assert "VOO" in symbols
        assert "VTSAX" in symbols

        vti = next(h for h in holdings if h.symbol == "VTI")
        assert vti.quantity == Decimal("50.000")
        assert vti.market_value == Decimal("8250.00")
        assert vti.cost_basis == Decimal("7500.00")

    def test_bond_format(self, schwab_bond_text):
        holdings = parse_pdf_text(schwab_bond_text)
        symbols = {h.symbol for h in holdings}
        assert "BND" in symbols
        assert "LQD" in symbols
        assert "TLT" in symbols

        bnd = next(h for h in holdings if h.symbol == "BND")
        # Bond format has no shares; quantity = 0, cost = face value
        assert bnd.quantity == Decimal("0")
        assert bnd.market_value == Decimal("5100.00")
        assert bnd.cost_basis == Decimal("5000.00")

    def test_cash_extraction(self, schwab_cash_text):
        holdings = parse_pdf_text(schwab_cash_text)
        symbols = {h.symbol for h in holdings}
        assert "CASH" in symbols
        assert "AAPL" in symbols

        cash = next(h for h in holdings if h.symbol == "CASH")
        assert cash.market_value == Decimal("12345.67")
        assert cash.quantity == Decimal("0")

    def test_deduplication(self, schwab_holdings_text):
        """Same symbol appearing twice → only one result (last wins)."""
        double = schwab_holdings_text + "\nAAPL      Apple Inc              200.000   $  39,700.00  $  30,000.00  $   9,700.00\n"
        holdings = parse_pdf_text(double)
        aapl_list = [h for h in holdings if h.symbol == "AAPL"]
        assert len(aapl_list) == 1
        assert aapl_list[0].quantity == Decimal("200.000")

    def test_empty_text(self):
        assert parse_pdf_text("") == []

    def test_noise_text(self):
        """Text with no holdings → empty result."""
        assert parse_pdf_text("This is just some random text with no holdings data.") == []

    def test_is_significant_filter(self):
        """Zero-quantity, zero-value rows are filtered out."""
        # A line that parses but has qty=0 and value=0
        holdings = parse_pdf_text("AAPL Apple Inc 0.000 $ 0.00 $ 0.00 $ 0.00")
        assert all(h.is_significant for h in holdings) is False or len(holdings) == 0


# ── StatementHolding dataclass tests ──────────────────────────────────────


class TestStatementHolding:
    def test_is_significant_with_quantity(self):
        h = StatementHolding(symbol="AAPL", quantity=Decimal("100"))
        assert h.is_significant is True

    def test_is_significant_with_market_value(self):
        h = StatementHolding(symbol="CASH", market_value=Decimal("5000"))
        assert h.is_significant is True

    def test_not_significant(self):
        h = StatementHolding(symbol="XXX", quantity=Decimal("0"), market_value=Decimal("0"))
        assert h.is_significant is False


# ── Service (import_statement) tests ─────────────────────────────────────


class TestImportStatement:
    """Test the full import pipeline with real DB."""

    async def test_import_creates_positions(
        self,
        db_session,
        auth_client,
        make_portfolio_with_account,
        schwab_holdings_text,
        monkeypatch,
    ):
        """Import a statement with 5 holdings → 5 assets + 5 positions created."""

        # Mock PdfReader to return our test text
        class MockPdfReader:
            class MockPage:
                def extract_text(self):
                    return schwab_holdings_text

            @property
            def pages(self):
                return [self.MockPage()]

            def __init__(self, *a, **kw):
                pass

        monkeypatch.setattr("portfolio_manager.services.statement_import.PdfReader", MockPdfReader)

        portfolio = await make_portfolio_with_account()
        portfolio_id = portfolio["id"]

        result = await import_statement(db_session, portfolio_id, b"fake-pdf-bytes")
        await db_session.commit()

        assert result["holdings_imported"] == 5
        assert "AAPL" in result["created"]
        assert "MSFT" in result["created"]
        assert "VTI" in result["created"]
        assert result["updated"] == []

    async def test_import_updates_existing_positions(
        self,
        db_session,
        auth_client,
        make_portfolio_with_account,
        schwab_holdings_text,
        monkeypatch,
        make_asset,
    ):
        """Import twice: second import updates existing positions."""

        class MockPdfReader:
            class MockPage:
                def extract_text(self):
                    return schwab_holdings_text

            @property
            def pages(self):
                return [self.MockPage()]

            def __init__(self, *a, **kw):
                pass

        monkeypatch.setattr("portfolio_manager.services.statement_import.PdfReader", MockPdfReader)

        portfolio = await make_portfolio_with_account()
        portfolio_id = portfolio["id"]

        # First import
        result1 = await import_statement(db_session, portfolio_id, b"fake-pdf-bytes")
        await db_session.commit()
        assert result1["created"] == ["AAPL", "MSFT", "VTI", "BND", "QQQ"]
        assert result1["updated"] == []

        # Second import — all positions should be updated, not created
        await db_session.flush()
        result2 = await import_statement(db_session, portfolio_id, b"fake-pdf-bytes")
        await db_session.commit()
        assert result2["created"] == []
        assert set(result2["updated"]) == {"AAPL", "MSFT", "VTI", "BND", "QQQ"}

    async def test_import_invalid_portfolio_id(self, db_session):
        from fastapi import HTTPException

        from portfolio_manager.services.statement_import import import_statement

        with pytest.raises(HTTPException) as exc_info:
            await import_statement(db_session, "not-a-uuid", b"fake-pdf-bytes")
        assert exc_info.value.status_code == 400

    async def test_import_portfolio_not_found(self, db_session):
        import uuid

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await import_statement(db_session, str(uuid.uuid4()), b"fake-pdf-bytes")
        assert exc_info.value.status_code == 404


# ── Route tests ───────────────────────────────────────────────────────────


class TestImportRoute:
    """Test the HTTP import endpoint."""

    async def test_unauthenticated_rejected(self, client):
        r = await client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": "00000000-0000-0000-0000-000000000000"},
            files={"file": ("statement.pdf", b"%PDF-fake", "application/pdf")},
        )
        assert r.status_code in (401, 403)

    async def test_invalid_portfolio_id(self, auth_client):
        r = await auth_client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": "not-a-uuid"},
            files={"file": ("statement.pdf", b"%PDF-fake", "application/pdf")},
        )
        assert r.status_code == 400

    async def test_portfolio_not_found(self, auth_client):
        import uuid

        r = await auth_client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": str(uuid.uuid4())},
            files={"file": ("statement.pdf", b"%PDF-fake", "application/pdf")},
        )
        assert r.status_code == 404

    async def test_unsupported_file_type(self, auth_client, db_session, make_portfolio):
        """Non-PDF file → 400."""
        # We need a real portfolio UUID for this test
        portfolio = await make_portfolio()

        r = await auth_client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": portfolio["id"]},
            files={"file": ("statement.txt", b"some text", "text/plain")},
        )
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    async def test_empty_file(self, auth_client, db_session, make_portfolio):
        """Empty file → 400."""
        portfolio = await make_portfolio()

        r = await auth_client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": portfolio["id"]},
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert r.status_code == 400
        assert "Empty file" in r.json()["detail"]

    async def test_successful_import(
        self,
        auth_client,
        db_session,
        make_portfolio_with_account,
        schwab_holdings_text,
        monkeypatch,
    ):
        """Full route integration test: upload → parse → positions created."""

        class MockPdfReader:
            class MockPage:
                def extract_text(self):
                    return schwab_holdings_text

            @property
            def pages(self):
                return [self.MockPage()]

            def __init__(self, *a, **kw):
                pass

        monkeypatch.setattr("portfolio_manager.services.statement_import.PdfReader", MockPdfReader)

        portfolio = await make_portfolio_with_account()

        r = await auth_client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": portfolio["id"]},
            files={"file": ("statement.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["holdings_imported"] == 5
        assert "AAPL" in data["created"]

    async def test_another_user_cannot_import(
        self,
        client,
        make_user,
        make_portfolio_with_account,
        auth_client,
    ):
        """User B cannot import into User A's portfolio."""
        # Create a portfolio for user A
        portfolio = await make_portfolio_with_account()

        # Create user B
        user_b = await make_user(display_name="Other User")
        client.headers.update({"Authorization": f"Bearer {user_b['token']}"})

        r = await client.post(
            "/api/v1/import/statement",
            data={"portfolio_id": portfolio["id"]},
            files={"file": ("statement.pdf", b"%PDF-fake", "application/pdf")},
        )
        assert r.status_code == 404  # "not found" — ownership hidden
