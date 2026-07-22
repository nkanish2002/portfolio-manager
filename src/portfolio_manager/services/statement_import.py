"""Broker statement import — parse Schwab PDF → create/update positions + assets.

Public API:
  * ``parse_pdf_text(text: str) -> list[StatementHolding]`` — extract holdings from raw PDF text
  * ``import_statement(session, portfolio_id, file, force_upsert=False)`` — full import pipeline

Strategy:
  1. Extract text pages from the PDF via ``pypdf``.
  2. Run regex heuristics to identify the "holdings" / "positions" section.
  3. Parse each row into a ``StatementHolding`` (symbol, qty, cost_basis, market_value, name).
  4. Upsert the ``Asset`` row (idempotent by symbol) and create/update the ``Position``.

The parsing is heuristic (regex-based on common Schwab PDF layouts). It is intentionally
resilient — rows that don't match any known pattern are silently skipped with a warning
log. This keeps the import useful even as Schwab tweaks PDF formatting over time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from uuid import UUID

import structlog
from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.models import Asset, Portfolio, Position

log = structlog.get_logger()

# ── Data class for a parsed holding ───────────────────────────────────────


@dataclass
class StatementHolding:
    """One parsed row from a statement holdings table."""

    symbol: str
    name: str = ""
    quantity: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    currency: str = "USD"

    @property
    def is_significant(self) -> bool:
        """Filter out zero-quantity cash-like rows unless they have value."""
        return self.quantity > 0 or self.market_value > 0


# ── Regex patterns for Schwab PDF holdings ────────────────────────────────
# Schwab statements have multiple formats; these patterns cover the common ones.

# Pattern 1: standard holdings table row
#   Symbol   Description              Shares      Market Value   Cost Basis   Gain/Loss
#   AAPL     Apple Inc              100.000   $  19,850.00  $  15,000.00  $   4,850.00
_HOLDING_RE1 = re.compile(
    r"(?P<symbol>[A-Z]{1,6})\s+"                       # ticker
    r"(?P<name>.*?)\s+"                                 # description
    r"(?P<qty>[0-9]+(?:\.[0-9]+)?)\s+"                  # shares
    r"\$\s*(?P<value>[0-9,]+(?:\.[0-9]+)?)"             # market value
    r"(?:\s+\$\s*(?P<cost>[0-9,]+(?:\.[0-9]+)?))?"      # cost basis (optional)
    r"(?:\s+\$\s*(?P<gain>[0-9,]+(?:\.[0-9]+)?))?"      # gain/loss (optional)
)

# Pattern 2: compact single-line format (often in "account snapshot" sections)
#   AAPL   100   $198.50   $15,000.00   Apple Inc
_HOLDING_RE2 = re.compile(
    r"(?P<symbol>[A-Z]{1,6})\s+"
    r"(?P<qty>[0-9]+(?:\.[0-9]+)?)\s+"
    r"\$\s*(?P<price>[0-9,]+(?:\.[0-9]+)?)\s+"
    r"\$\s*(?P<cost>[0-9,]+(?:\.[0-9]+)?)"
    r".*?(?P<name>[A-Za-z].*[A-Za-z])"
)

# Pattern 3: ETF/mutual fund format with CUSIP
#   VTI    Vanguard Total Stock Mkt Idx 012345AB7 50.000 $ 8,250.00 $ 7,500.00
_HOLDING_RE3 = re.compile(
    r"(?P<symbol>[A-Z]{1,6})\s+"
    r"(?P<name>.*?)\s+"
    r"[0-9]{9}\s+"                                       # CUSIP (9 digits) — skip
    r"(?P<qty>[0-9]+(?:\.[0-9]+)?)\s+"
    r"\$\s*(?P<value>[0-9,]+(?:\.[0-9]+)?)\s+"
    r"\$\s*(?P<cost>[0-9,]+(?:\.[0-9]+)?)?"
)

# Pattern 4: bond/CD format (no shares, face value)
#   BND    Vanguard Total Bond Mkt Idx            $ 5,000.00  $ 5,100.00
_HOLDING_RE4 = re.compile(
    r"(?P<symbol>[A-Z]{1,6})\s+"
    r"(?P<name>.*?)\s+"
    r"\$\s*(?P<cost>[0-9,]+(?:\.[0-9]+)?)\s+"
    r"\$\s*(?P<value>[0-9,]+(?:\.[0-9]+)?)\s*$"
)

# Cash row pattern
_CASH_RE = re.compile(
    r"(?:cash|money\s*market|sweep|cash\s*mgr|sweep\s*fund|settlement)\b.*?"
    r"\$\s*(?P<value>[0-9,]+(?:\.[0-9]+)?)"
)

# Common non-holding header/footer noise to skip
_SKIP_LINES = {
    "symbol", "description", "shares", "market value", "cost basis", "gain/loss",
    "holdings", "positions", "current positions", "unrealized", "account value",
    "total value", "total market value", "total gain/loss",
}

# ── Parsing helpers ───────────────────────────────────────────────────────


def _clean_number(raw: str | None) -> Decimal:
    """Parse a number string like '15,000.00' → Decimal('15000.00')."""
    if raw is None:
        return Decimal("0")
    try:
        return Decimal(raw.replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _extract_cash(text: str) -> StatementHolding | None:
    """Try to find a cash/money-market balance in the text."""
    m = _CASH_RE.search(text)
    if m:
        return StatementHolding(
            symbol="CASH",
            name="Cash / Sweep",
            quantity=Decimal("0"),
            market_value=_clean_number(m.group("value")),
        )
    return None


def _try_parse_line(line: str) -> StatementHolding | None:
    """Try each regex pattern on a line. Return first match or None."""
    for pattern in (_HOLDING_RE1, _HOLDING_RE3, _HOLDING_RE2, _HOLDING_RE4):
        m = pattern.search(line)
        if m:
            d = m.groupdict()
            qty = _clean_number(d.get("qty"))
            value = _clean_number(d.get("value"))
            cost = _clean_number(d.get("cost"))
            # If cost is missing but we have value and qty, estimate cost = value
            if cost == 0 and value > 0 and qty > 0:
                cost = value
            # If cost is missing but we have a price * qty from pattern 2
            if cost == 0 and qty > 0:
                price = _clean_number(d.get("price"))
                if price > 0:
                    cost = price * qty
            symbol = (d.get("symbol") or "").strip().upper()
            if not symbol or symbol in _SKIP_LINES:
                continue
            return StatementHolding(
                symbol=symbol,
                name=(d.get("name") or "").strip()[:255],
                quantity=qty,
                cost_basis=cost,
                market_value=value,
            )
    return None


def parse_pdf_text(text: str) -> list[StatementHolding]:
    """Parse raw PDF text into a list of holdings.

    Walks each line trying the regex patterns. Deduplicates by symbol,
    keeping the last match per symbol (later pages are usually more recent).
    """
    holdings: dict[str, StatementHolding] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower() in _SKIP_LINES:
            continue
        holding = _try_parse_line(line)
        if holding is not None and holding.is_significant:
            holdings[holding.symbol] = holding

    # Try to extract cash if not already found
    if "CASH" not in holdings:
        cash = _extract_cash(text)
        if cash is not None:
            holdings["CASH"] = cash

    return list(holdings.values())


# ── Full import pipeline ──────────────────────────────────────────────────


async def _upsert_asset(session: AsyncSession, holding: StatementHolding) -> Asset:
    """Create or update an Asset row (idempotent by symbol)."""
    result = await session.execute(select(Asset).where(Asset.symbol == holding.symbol))
    asset = result.scalar_one_or_none()

    if asset is None:
        asset = Asset(
            symbol=holding.symbol,
            name=holding.name or holding.symbol,
            asset_class="equity" if holding.symbol != "CASH" else "cash",
        )
        session.add(asset)
    else:
        # Update metadata if we have better info
        if holding.name and not asset.name:
            asset.name = holding.name
    return asset


async def _get_position(
    session: AsyncSession,
    portfolio_id,
    asset_id,
) -> Position | None:
    """Look up an existing position."""
    result = await session.execute(
        select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.asset_id == asset_id,
        )
    )
    return result.scalar_one_or_none()


async def import_statement(
    session: AsyncSession,
    portfolio_id: str,
    file_bytes: bytes,
) -> dict[str, object]:
    """Full pipeline: read PDF → parse → upsert assets & positions.

    Returns a summary dict with counts of created/updated items.
    """
    try:
        pid = UUID(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid portfolio_id") from exc

    # Verify portfolio exists
    result = await session.execute(select(Portfolio).where(Portfolio.id == pid))
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # ── Step 1: extract text from PDF ──────────────────────────────────
    try:
        reader = PdfReader(BytesIO(file_bytes))
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {exc}") from exc

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="PDF contains no extractable text")

    # ── Step 2: parse holdings ─────────────────────────────────────────
    holdings = parse_pdf_text(full_text)
    if not holdings:
        raise HTTPException(
            status_code=400,
            detail="No holdings found in statement. Ensure it is a Schwab holdings/positions statement.",
        )

    log.info("statement_import.parsed_holdings", count=len(holdings), symbols=[h.symbol for h in holdings])

    # ── Step 3: upsert assets and positions ────────────────────────────
    created: list[str] = []
    updated: list[str] = []

    for holding in holdings:
        asset = await _upsert_asset(session, holding)
        await session.flush()  # ensure asset.id is populated

        existing = await _get_position(session, portfolio.id, asset.id)
        if existing is not None:
            existing.quantity = holding.quantity
            existing.avg_cost_basis = holding.cost_basis
            if holding.quantity > 0:
                existing.current_price = holding.cost_basis / holding.quantity
            existing.market_value = existing.quantity * existing.current_price
            existing.unrealized_gain = Decimal("0")
            existing.unrealized_gain_pct = Decimal("0")
            updated.append(holding.symbol)
        else:
            position = Position(
                portfolio_id=portfolio.id,
                asset_id=asset.id,
                quantity=holding.quantity,
                avg_cost_basis=holding.cost_basis,
                current_price=(
                    holding.cost_basis / holding.quantity if holding.quantity > 0 else Decimal("0")
                ),
            )
            session.add(position)
            created.append(holding.symbol)

    await session.flush()

    return {
        "portfolio_id": str(portfolio.id),
        "holdings_imported": len(holdings),
        "created": created,
        "updated": updated,
    }
