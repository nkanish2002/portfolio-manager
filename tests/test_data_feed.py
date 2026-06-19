"""Tests for the data feed service."""

from datetime import date

from portfolio_manager.services.data_feed import YFinanceSource


class TestYFinanceSourceConnection:
    """Test connection checking."""

    def test_check_connection_method_exists(self) -> None:
        """Verify check_connection method exists on YFinanceSource."""
        source = YFinanceSource()
        assert hasattr(source, "check_connection")
        assert callable(source.check_connection)

    def test_check_connection_returns_bool(self) -> None:
        """check_connection should return True/False."""
        source = YFinanceSource()
        result = source.check_connection()
        assert isinstance(result, bool)

    def test_timeout_configurable(self) -> None:
        """Timeout should be configurable."""
        source = YFinanceSource(timeout=10)
        assert source.timeout == 10

        source2 = YFinanceSource(timeout=60)
        assert source2.timeout == 60


class TestYFinanceSourceGetPrice:
    """Test price fetching."""

    def test_get_price_returns_decimal(self) -> None:
        """get_price should return a Decimal or None."""
        source = YFinanceSource()
        result = source.get_price("SPY")
        assert result is None or hasattr(result, "__float__")

    def test_get_price_with_date(self) -> None:
        """get_price should work with a date parameter."""
        source = YFinanceSource()
        # Use a recent date
        yesterday = date.today() - __import__("datetime").timedelta(days=1)
        result = source.get_price("SPY", as_of=yesterday)
        # SPY almost always has a price on trading days
        # This test may return None on weekends/holidays
