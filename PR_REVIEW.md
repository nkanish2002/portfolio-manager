# Portfolio Manager Code Review

## Summary
Comprehensive review of the portfolio-manager codebase with suggestions for improvements and fixes.

## ✅ Strengths (What's Already Good)
- **Clean architecture**: Separation of concerns (models → services → routes → templates) follows modern FastAPI best practices
- **Async-first**: Uses `aiosqlite`, async sessions, and async services — good for scalability
- **Professional risk metrics**: Full suite (Sharpe, Sortino, Max DD, VaR, Beta, Alpha, Treynor, Calmar, Ulcer Index)
- **TradingView Lightweight Charts integration**: Phase 8 complete with proper NAV building from transactions
- **WebSocket market data**: Real-time price streaming with subscription management
- **React SPA fallback**: Proper catch-all route with `api/` path check

---

## 🚨 Critical Issues

### 1. Missing Portfolio Import in `routes/portfolios.py`
**Line 126**: `select(Portfolio)` but Portfolio not imported

**Fix**: Add `from portfolio_manager.models.portfolio import Portfolio`

### 2. PortfolioResponse Hardcodes position_count=0
**Lines 128-130**: Returns hardcoded 0 instead of actual count

**Impact**: Dashboard shows wrong counts

### 3. Asset.cusip Nullable But Position Requires It
- `PositionCreate.cusip` is `Field(...)` (required)
- But `Asset.cusip` is `nullable=True`
- Can create asset without CUSIP, then fail on position creation

### 4. Missing Error Handling for Price Fetch Failures
In `routes/ui.py:refresh_prices()`:
- No try/except around `get_price` — yfinance failure crashes the endpoint

### 5. BenchmarkPortfolioAssociation Table Not Created
- Defined in `models/benchmark.py` but never referenced in models `__init__.py`
- `portfolio.benchmarks` relationship uses `secondary="benchmark_portfolios"` but table not registered

---

## ⚨ High Priority Issues

### 6. Date Comparison Mismatch in `build_nav_from_transactions`
**Lines 74-78**: Creates DatetimeIndex but uses `.date()`
- `.date()` returns `date` objects, not `Timestamp` — may cause issues with resampling

### 7. PortfolioDashboardPage Returns HTML for React SPA Instead of API
- `/dashboard/{portfolio_id}` returns `FileResponse(SPA_INDEX)` instead of portfolio data
- React should fetch portfolio data from `/api/v1/portfolios/{id}`

### 8. Missing Input Validation on Price Updates
- No check that `quantity > 0` before creating/updating position
- No validation of `price >= 0`

### 9. AssetClass.CASH Typo
```python
class AssetClass(StrEnum):
    CASH = "cash"  # Should be CASH but typo in name
```

---

## ⚨ Medium Priority Issues

### 10. No Rate Limiting on Price Fetching
- `refresh_prices` calls `get_price` per position — no batching or caching
- Could hit yfinance rate limits on large portfolios

### 11. Transaction.total_amount Doesn't Handle All Types
- Should handle SPLIT, REINVEST explicitly

### 12. No Migration System
- Uses `Base.metadata.create_all()` — no Alembic
- Schema changes will require manual DB drops

---

## 🟡 Lower Priority / Suggestions

### 13. Missing Unit Tests for Charts API
- `tests/test_api.py` exists but chart endpoints untested

### 14. No Logging
- All `print` statements missing — should add `logging` module

### 15. Missing Cache Layer
- Price fetching hits yfinance every refresh
- Could add Redis or in-memory cache (5-min TTL)

### 16. Asset.name Required But Can Be Auto-Generated
- If `symbol` exists, name could default to symbol

### 17. Portfolio.currency Not Enforced
- No enum validation — could allow invalid 3-letter codes

### 18. Missing CORS Configuration
- No `CORSMiddleware` — frontend on different origin will fail

---

## 📊 Priority Matrix

| Priority | Issue | Impact |
|----------|-------|--------|
| **Critical** | Missing `Portfolio` import | API broken |
| **Critical** | `PortfolioResponse` hardcodes position_count | UI shows wrong data |
| **High** | `BenchmarkPortfolioAssociation` not registered | Many-to-many broken |
| **High** | Price fetch errors crash endpoint | Data refresh fails |
| **Medium** | Date index mismatch in NAV building | Chart alignment issues |
| **Medium** | No migration system | Schema evolution blocked |

---

## 🛠️ Quick Fixes (To Implement First)

1. Add `Portfolio` import in `routes/portfolios.py`
2. Fix `PortfolioResponse` to count actual positions
3. Register `BenchmarkPortfolioAssociation` in `models/__init__.py`
4. Add try/except around `get_price` in `routes/ui.py`
5. Add CORS middleware to `main.py`
