"""Portfolio classification service.

Categorizes assets by:
- Sector (Technology, Healthcare, Finance, etc.)
- Industry (Software, Banking, Pharmaceuticals, etc.)
- Region/Market (US, Europe, Emerging Markets, etc.)
- Market Cap (Large, Mid, Small, Micro)
"""


# Simplified sector mapping (in production, use a paid API like Alpha Vantage or IEX)
SECTOR_MAP = {
    # Technology
    "AAPL": ("Technology", "Consumer Electronics"),
    "MSFT": ("Technology", "Software"),
    "GOOGL": ("Technology", "Internet Services"),
    "GOOG": ("Technology", "Internet Services"),
    "AMZN": ("Technology", "E-Commerce"),
    "META": ("Technology", "Social Media"),
    "NVDA": ("Technology", "Semiconductors"),
    "TSLA": ("Consumer Discretionary", "Automotive"),
    "NFLX": ("Communication Services", "Streaming"),
    "CRM": ("Technology", "Enterprise Software"),
    "ORCL": ("Technology", "Database Software"),
    "ADBE": ("Technology", "Software"),
    "INTC": ("Technology", "Semiconductors"),
    "AMD": ("Technology", "Semiconductors"),
    "IBM": ("Technology", "IT Services"),
    # Finance
    "JPM": ("Financials", "Banking"),
    "BAC": ("Financials", "Banking"),
    "GS": ("Financials", "Investment Banking"),
    "MS": ("Financials", "Investment Banking"),
    "WFC": ("Financials", "Banking"),
    "C": ("Financials", "Banking"),
    "AXP": ("Financials", "Credit Services"),
    "BLK": ("Financials", "Asset Management"),
    "V": ("Financials", "Payment Processing"),
    "MA": ("Financials", "Payment Processing"),
    "BRK.B": ("Financials", "Insurance"),
    # Healthcare
    "JNJ": ("Healthcare", "Pharmaceuticals"),
    "PFE": ("Healthcare", "Pharmaceuticals"),
    "UNH": ("Healthcare", "Health Insurance"),
    "MRK": ("Healthcare", "Pharmaceuticals"),
    "ABBV": ("Healthcare", "Pharmaceuticals"),
    "TMO": ("Healthcare", "Life Sciences Tools"),
    "ABT": ("Healthcare", "Medical Devices"),
    "LLY": ("Healthcare", "Pharmaceuticals"),
    "AMGN": ("Healthcare", "Biotech"),
    "GILD": ("Healthcare", "Biotech"),
    # Consumer
    "PG": ("Consumer Staples", "Household Products"),
    "KO": ("Consumer Staples", "Beverages"),
    "PEP": ("Consumer Staples", "Beverages"),
    "WMT": ("Consumer Staples", "Retail"),
    "COST": ("Consumer Staples", "Retail"),
    "DIS": ("Communication Services", "Entertainment"),
    "NKE": ("Consumer Discretionary", "Apparel"),
    "HD": ("Consumer Discretionary", "Home Improvement"),
    "MCD": ("Consumer Discretionary", "Fast Food"),
    "SBUX": ("Consumer Discretionary", "Restaurants"),
    "MC": ("Consumer Staples", "Luxury Goods"),
    # Energy
    "XOM": ("Energy", "Oil & Gas Integrated"),
    "CVX": ("Energy", "Oil & Gas Integrated"),
    "COP": ("Energy", "Oil & Gas Exploration"),
    "SLB": ("Energy", "Oil & Gas Services"),
    # Industrial
    "BA": ("Industrials", "Aerospace & Defense"),
    "CAT": ("Industrials", "Construction Equipment"),
    "GE": ("Industrials", "Diversified"),
    "HON": ("Industrials", "Aerospace & Defense"),
    "UPS": ("Industrials", "Logistics"),
    "RTX": ("Industrials", "Aerospace & Defense"),
    # Utilities
    "NEE": ("Utilities", "Electric Utilities"),
    "DUK": ("Utilities", "Electric Utilities"),
    "SO": ("Utilities", "Electric Utilities"),
    "D": ("Utilities", "Electric Utilities"),
    # Real Estate
    "AMT": ("Real Estate", "REITs"),
    "PLD": ("Real Estate", "REITs"),
    "EQIX": ("Real Estate", "REITs"),
}

# Region mapping based on exchange suffix
REGION_MAP = {
    "US": ("United States", "North America"),
    "LSE": ("United Kingdom", "Europe"),
    "FRA": ("Germany", "Europe"),
    "TSE": ("Japan", "Asia-Pacific"),
    "SSE": ("China", "Asia-Pacific"),
    "HK": ("Hong Kong", "Asia-Pacific"),
    "BSE": ("India", "Asia-Pacific"),
    "NSE": ("India", "Asia-Pacific"),
}

# ETF sector mapping (common ETFs)
ETF_SECTOR_MAP = {
    "SPY": ("Broad Market", "Large Cap Blend"),
    "QQQ": ("Technology", "Growth"),
    "IWM": ("Broad Market", "Small Cap"),
    "VTI": ("Broad Market", "Total Market"),
    "EFA": ("International", "Developed Markets"),
    "EEM": ("Emerging Markets", "Emerging Markets"),
    "VEA": ("International", "Developed Markets"),
    "VWO": ("Emerging Markets", "Emerging Markets"),
    "LQD": ("Fixed Income", "Investment Grade Bonds"),
    "HYG": ("Fixed Income", "High Yield Bonds"),
    "TLT": ("Fixed Income", "Long-Term Treasury"),
    "GLD": ("Commodities", "Gold"),
    "SLV": ("Commodities", "Silver"),
}

# Crypto mapping
CRYPTO_MAP = {
    "BTC": ("Digital Assets", "Cryptocurrency"),
    "ETH": ("Digital Assets", "Cryptocurrency"),
    "SOL": ("Digital Assets", "Cryptocurrency"),
    "XRP": ("Digital Assets", "Cryptocurrency"),
    "ADA": ("Digital Assets", "Cryptocurrency"),
    "DOGE": ("Digital Assets", "Cryptocurrency"),
    "DOT": ("Digital Assets", "Cryptocurrency"),
    "MATIC": ("Digital Assets", "Cryptocurrency"),
    "AVAX": ("Digital Assets", "Cryptocurrency"),
}


def classify_asset(
    symbol: str, asset_class: str = "equity", exchange: str | None = None
) -> dict:
    """Classify an asset into sector, industry, region, and market cap categories.

    Args:
        symbol: Asset ticker symbol
        asset_class: Asset type (equity, etf, crypto, etc.)
        exchange: Exchange code (for region classification)

    Returns:
        dict with sector, industry, region, sub_region, market_category
    """
    symbol_upper = symbol.upper()
    result = {
        "symbol": symbol_upper,
        "asset_class": asset_class,
        "sector": None,
        "industry": None,
        "region": None,
        "sub_region": None,
        "market_category": "unknown",
    }

    # Handle crypto first
    if asset_class in ("crypto", "cryptocurrency"):
        result.update(
            {
                "sector": "Digital Assets",
                "industry": "Cryptocurrency",
                "market_category": "crypto",
            }
        )
        if symbol_upper in CRYPTO_MAP:
            result["sector"], result["industry"] = CRYPTO_MAP[symbol_upper]
        return result

    # Handle ETFs
    if asset_class == "etf" and symbol_upper in ETF_SECTOR_MAP:
        result.update(
            {
                "sector": ETF_SECTOR_MAP[symbol_upper][0],
                "industry": ETF_SECTOR_MAP[symbol_upper][1],
                "market_category": "etf",
            }
        )
        return result

    # Handle equities
    if symbol_upper in SECTOR_MAP:
        result["sector"], result["industry"] = SECTOR_MAP[symbol_upper]
    elif asset_class == "equity":
        # Default classification for unknown stocks
        result["sector"] = "Unknown"
        result["industry"] = "Unknown"

    # Determine market category
    if symbol_upper in ("SPY", "QQQ", "IWM", "VTI", "DIA"):
        result["market_category"] = "large_cap"
    elif symbol_upper.startswith(("SML", "IJR")):
        result["market_category"] = "mid_cap"
    elif symbol_upper.startswith(("IJR", "IWM")):
        result["market_category"] = "small_cap"
    else:
        result["market_category"] = "unknown"

    # Determine region if exchange is provided
    if exchange and exchange in REGION_MAP:
        result["region"], result["sub_region"] = REGION_MAP[exchange]
    else:
        # Default to US for most tickers
        result["region"] = "United States"
        result["sub_region"] = "North America"

    return result


def classify_positions(positions: list[dict]) -> list[dict]:
    """Classify multiple positions.

    Args:
        positions: List of position dicts with 'symbol', 'asset_class', 'exchange' keys

    Returns:
        List of positions with added classification fields
    """
    for pos in positions:
        classification = classify_asset(
            symbol=pos.get("symbol", ""),
            asset_class=pos.get("asset_class", "equity"),
            exchange=pos.get("exchange"),
        )
        pos.update(classification)
    return positions
