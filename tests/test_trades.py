"""FIFO trade ledger tests — realized P&L, lots, splits."""

from __future__ import annotations

from decimal import Decimal

from portfolio_manager.services.trades import (
    TradeLedger,
    build_ledger,
    fifo_realized_gain,
)


class TestFifoRealizedGain:
    def test_plan_example(self):
        # buy 10@100, buy 10@110, sell 5@120 → realized = $100
        g = fifo_realized_gain([(10, 100), (10, 110)], (5, 120))
        assert g == Decimal("100")

    def test_consume_first_lot_fully_then_second(self):
        # buy 10@100, buy 10@110, sell 12@120
        # 10 @ (120-100)=200 + 2 @ (120-110)=20 → 220
        g = fifo_realized_gain([(10, 100), (10, 110)], (12, 120))
        assert g == Decimal("220")

    def test_sell_all(self):
        g = fifo_realized_gain([(10, 100)], (10, 150))
        assert g == Decimal("500")

    def test_loss(self):
        g = fifo_realized_gain([(10, 100)], (10, 80))
        assert g == Decimal("-200")


class TestLedger:
    def test_avg_cost_basis_after_partial_sell(self):
        ledger = TradeLedger()
        ledger.buy("AAPL", Decimal("10"), Decimal("100"))
        ledger.buy("AAPL", Decimal("10"), Decimal("110"))
        ledger.sell("AAPL", Decimal("5"), Decimal("120"))
        # remaining: 5@100 + 10@110 → cost 500 + 1100 = 1600, qty 15 → 106.666
        assert ledger.avg_cost_basis("AAPL") == Decimal("1600") / Decimal("15")
        assert ledger.position_quantity("AAPL") == Decimal("15")

    def test_sell_more_than_held_returns_remaining(self):
        ledger = TradeLedger()
        ledger.buy("X", Decimal("5"), Decimal("100"))
        res = ledger.sell("X", Decimal("8"), Decimal("120"))
        # only 5 matched: proceeds 600, cost 500, gain 100; remaining 3
        assert res.realized_gain == Decimal("100")
        assert res.remaining_quantity == Decimal("3")
        assert res.lots_consumed == 1

    def test_buy_then_sell_exact(self):
        ledger = TradeLedger()
        ledger.buy("X", Decimal("10"), Decimal("100"))
        res = ledger.sell("X", Decimal("10"), Decimal("150"))
        assert res.realized_gain == Decimal("500")
        assert res.remaining_quantity == Decimal("0")
        assert ledger.position_quantity("X") == Decimal("0")

    def test_split_doubles_quantity_halves_price(self):
        ledger = TradeLedger()
        ledger.buy("X", Decimal("10"), Decimal("100"))
        ledger.split("X", Decimal("2"))
        assert ledger.position_quantity("X") == Decimal("20")
        assert ledger.avg_cost_basis("X") == Decimal("50")

    def test_zero_quantity_noop(self):
        ledger = TradeLedger()
        res = ledger.sell("X", Decimal("0"), Decimal("100"))
        assert res.realized_gain == Decimal("0")
        assert res.remaining_quantity == Decimal("0")


class TestBuildLedger:
    def test_replay_transactions_records_sells(self):
        txns = [
            {"asset_id": "A", "type": "buy", "quantity": Decimal("10"), "price": Decimal("100"), "fees": Decimal("0")},
            {"asset_id": "A", "type": "buy", "quantity": Decimal("10"), "price": Decimal("110"), "fees": Decimal("0")},
            {"asset_id": "A", "type": "sell", "quantity": Decimal("5"), "price": Decimal("120"), "fees": Decimal("0")},
        ]
        ledger, realized = build_ledger(txns)
        assert ledger.position_quantity("A") == Decimal("15")
        assert len(realized) == 1
        assert realized[0][1] == Decimal("100")  # realized gain on the sell

    def test_multiple_sells(self):
        txns = [
            {"asset_id": "A", "type": "buy", "quantity": Decimal("10"), "price": Decimal("100"), "fees": Decimal("0")},
            {"asset_id": "A", "type": "sell", "quantity": Decimal("4"), "price": Decimal("150"), "fees": Decimal("0")},
            {"asset_id": "A", "type": "sell", "quantity": Decimal("6"), "price": Decimal("200"), "fees": Decimal("0")},
        ]
        ledger, realized = build_ledger(txns)
        # sell1: 4*(150-100)=200 ; sell2: 6*(200-100)=600
        assert realized[0][1] == Decimal("200")
        assert realized[1][1] == Decimal("600")
        assert ledger.position_quantity("A") == Decimal("0")
