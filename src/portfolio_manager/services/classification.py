"""Sector / region / asset-class classification.

Maps ticker symbols to human buckets for allocation breakdowns. Falls back
to data already stored on the ``Asset`` row when present; otherwise returns
"Unknown" rather than guessing.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

# Coarse region inference from common exchange suffixes / symbols.
_REGION_HINTS = {
    ".SW": "Europe",
    ".L": "Europe",
    ".DE": "Europe",
    ".PA": "Europe",
    ".TO": "North America",
    ".TR": "North America",
    ".HK": "Asia",
    ".T": "Asia",
    ".SS": "Asia",
    ".SZ": "Asia",
    ".AX": "Oceania",
    ".BR": "Latin America",
    ".MX": "Latin America",
    ".MI": "Europe",
    ".AS": "Europe",
}


def infer_region(symbol: str) -> str:
    """Best-effort region from a symbol's exchange suffix."""
    if "." in symbol:
        suffix = symbol.rsplit(".", 1)[-1].upper()
        return _REGION_HINTS.get(f".{suffix}", "International")
    # US-listed (no suffix)
    return "United States"


def classify_asset(*, sector: str | None = None, region: str | None = None, symbol: str | None = None) -> dict[str, str]:
    """Return a {sector, region} classification for an asset.

    Prefers explicit ``sector``/``region`` values (from the Asset row);
    falls back to inferring region from the symbol. ``sector`` defaults to
    "Unknown".
    """
    return {
        "sector": sector or "Unknown",
        "region": region or infer_region(symbol or ""),
    }


def classify_positions(
    positions: Iterable,
    *,
    sector_of: callable,  # type: ignore[name-defined]
    region_of: callable,  # type: ignore[name-defined]
    symbol_of: callable,  # type: ignore[name-defined]
) -> list[dict[str, str]]:
    """Classify each position using caller-supplied accessors.

    ``sector_of``/``region_of``/``symbol_of`` are callables taking a
    position and returning the corresponding attribute (or None). This keeps
    the function decoupled from the ORM model shape.
    """
    out: list[dict[str, str]] = []
    for p in positions:
        out.append(
            classify_asset(
                sector=sector_of(p),
                region=region_of(p),
                symbol=symbol_of(p),
            )
        )
    return out


def bucketize(values: Sequence[str]) -> dict[str, int]:
    """Count occurrences per bucket — handy for quick allocation tallies."""
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return counts
