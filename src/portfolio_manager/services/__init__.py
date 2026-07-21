"""Service layer — business logic that sits between routes and the DB/feeds."""

from portfolio_manager.services.basket_seed import (
    PRESET_BASKETS,
    TARGET_TOLERANCE,
    TARGET_TOTAL,
    compute_target_summary,
    seed_default_baskets,
)
from portfolio_manager.services.benchmark import (
    compare_to_benchmark,
    excess_returns,
    information_ratio,
    tracking_error,
)
from portfolio_manager.services.classification import classify_asset, infer_region
from portfolio_manager.services.data_feed import (
    DataFeed,
    PriceBar,
    PriceQuote,
    TickerSearchResult,
    YFinanceFetcher,
    data_feed,
    price_cache,
)
from portfolio_manager.services.nav_history import NavPoint, build_nav_history
from portfolio_manager.services.portfolio_calc import (
    PortfolioSummary,
    PositionValue,
    compute_allocation,
    compute_nav,
    compute_pnl,
    compute_position_fields,
    position_value,
    simple_returns,
    summarize_portfolio,
)
from portfolio_manager.services.price_cache import PriceCache
from portfolio_manager.services.risk import compute_risk_metrics, max_drawdown
from portfolio_manager.services.trades import (
    SellResult,
    TradeLedger,
    build_ledger,
    fifo_realized_gain,
)
from portfolio_manager.services.ws_service import WebSocketManager, ws_manager

__all__ = [
    # data feed + cache
    "DataFeed",
    "PriceBar",
    "PriceCache",
    "PriceQuote",
    "TickerSearchResult",
    "YFinanceFetcher",
    "data_feed",
    "price_cache",
    # portfolio calc
    "PortfolioSummary",
    "PositionValue",
    "compute_allocation",
    "compute_nav",
    "compute_pnl",
    "compute_position_fields",
    "position_value",
    "simple_returns",
    "summarize_portfolio",
    # risk
    "compute_risk_metrics",
    "max_drawdown",
    # trades
    "SellResult",
    "TradeLedger",
    "build_ledger",
    "fifo_realized_gain",
    # nav history
    "NavPoint",
    "build_nav_history",
    # benchmark
    "compare_to_benchmark",
    "excess_returns",
    "information_ratio",
    "tracking_error",
    # basket seed
    "PRESET_BASKETS",
    "TARGET_TOTAL",
    "TARGET_TOLERANCE",
    "compute_target_summary",
    "seed_default_baskets",
    # classification
    "classify_asset",
    "infer_region",
    # websocket
    "WebSocketManager",
    "ws_manager",
]
