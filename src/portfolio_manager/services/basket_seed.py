"""Basket seed + target-allocation validation.

Provides the 3-basket preset (Super Stable / Stable Alpha / High Beta) that is
seeded for every new user on first run, plus a helper that summarizes basket
target allocations and emits a warning when they don't sum to 100%.

Baskets are user-scoped, so "first run" = "right after user registration".
The seeder is idempotent: if a user already owns any baskets, it does nothing.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.models import Basket

log = structlog.get_logger()


# ── 3-basket preset (seeds blue / purple / orange, 40 / 40 / 20) ──────────

PRESET_BASKETS: tuple[dict[str, object], ...] = (
    {
        "name": "Super Stable",
        "description": "Core compounders + broad market index — sleep well at night.",
        "color": "#58a6ff",  # blue
        "target_allocation": Decimal("40.00"),
        "sort_order": 1,
    },
    {
        "name": "Stable Alpha",
        "description": "Dividend growers + low-volatility factor — steady excess return.",
        "color": "#bc8cff",  # purple
        "target_allocation": Decimal("40.00"),
        "sort_order": 2,
    },
    {
        "name": "High Beta",
        "description": "High-beta / speculative names — growth kicker, sized small.",
        "color": "#f0883e",  # orange
        "target_allocation": Decimal("20.00"),
        "sort_order": 3,
    },
)

TARGET_TOTAL = Decimal("100.00")
TARGET_TOLERANCE = Decimal("0.01")  # allow rounding slack when summing percents


async def seed_default_baskets(session: AsyncSession, user_id: UUID) -> list[Basket]:
    """Seed the 3-basket preset for ``user_id`` if they have no baskets yet.

    Idempotent: returns the user's existing baskets untouched if any are found.
    Commits the new baskets and refreshes them before returning.
    """
    existing = (
        (await session.execute(select(Basket).where(Basket.user_id == user_id).order_by(Basket.sort_order)))
        .scalars()
        .all()
    )
    if existing:
        return list(existing)

    created: list[Basket] = []
    for preset in PRESET_BASKETS:
        basket = Basket(**preset, user_id=user_id, is_preset=True)  # type: ignore[arg-type]
        session.add(basket)
        created.append(basket)

    await session.commit()
    for basket in created:
        await session.refresh(basket)

    log.info("seeded_default_baskets", user_id=str(user_id), count=len(created))
    return created


async def compute_target_summary(session: AsyncSession, user_id: UUID) -> dict[str, object]:
    """Summarize basket target allocations and flag drift from 100%.

    Returns ``{total, targets_complete, warning}``. ``warning`` is ``None`` when
    the targets sum to ~100%, otherwise a human-readable hint.
    """
    total_decimal: Decimal = (
        await session.execute(
            select(func.coalesce(func.sum(Basket.target_allocation), Decimal("0"))).where(Basket.user_id == user_id)
        )
    ).scalar_one()

    count: int = (
        await session.execute(select(func.count()).select_from(Basket).where(Basket.user_id == user_id))
    ).scalar_one()

    total = Decimal(total_decimal or 0)
    targets_complete = abs(total - TARGET_TOTAL) <= TARGET_TOLERANCE
    warning: str | None = None
    if not targets_complete:
        if count == 0:
            warning = "No baskets yet — create some to set target allocations."
        elif total < TARGET_TOTAL:
            warning = f"Basket targets sum to {total:.2f}% — {TARGET_TOTAL - total:.2f}% unallocated."
        else:
            warning = f"Basket targets sum to {total:.2f}% — {total - TARGET_TOTAL:.2f}% over-allocated."

    return {
        "total_target_allocation": float(total),
        "basket_count": count,
        "targets_complete": bool(targets_complete),
        "warning": warning,
    }
