"""ASCII risk gauge widgets.

Renders the 9 risk metrics as visual ASCII bar-chart gauges with
green / amber / red thresholds that map to GOOD, OK, or BAD status.

Usage
-----
    from portfolio_manager.services.risk_gauges import RiskGauge, render_risk_gauges

    gauge = RiskGauge("Sharpe Ratio", 1.42, min_val=-1, max_val=4)
    gauge.render()  # -> "▓▓▓▓▓▓░░░ 1.42 / GOOD"

    # Batch render all 9 metrics at once:
    lines = render_risk_gauges(risk_report)  # -> list[str]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── Thresholds ──────────────────────────────────────────────────────────

_GAUGE_WIDTH = 15  # characters for the bar

# Inverted metrics: value closer to 0 = GOOD
INVERTED_METRICS = {
    "max_drawdown",
    "ulcer_index",
    "var_95",
}

# Threshold tables per metric
# "good" and "ok" are (lower, upper) bounds
_THRESHOLDS: dict[str, dict[str, tuple[float, float]]] = {
    "sharpe_ratio": {
        "good": (-0.5, 999.0),
        "ok": (-999.0, -0.5),
    },
    "sortino_ratio": {
        "good": (-0.5, 999.0),
        "ok": (-999.0, -0.5),
    },
    "max_drawdown": {
        "good": (-5.0, 0.0),
        "ok": (-30.0, -5.0),
    },
    "var_95": {
        "good": (0.0, 2.0),
        "ok": (2.0, 10.0),
    },
    "beta": {
        "good": (0.5, 1.5),
        "ok": (0.0, 2.5),
    },
    "alpha": {
        "good": (-1.0, 999.0),
        "ok": (-999.0, -1.0),
    },
    "treynor_ratio": {
        "good": (-1.0, 999.0),
        "ok": (-999.0, -1.0),
    },
    "calmar_ratio": {
        "good": (0.5, 999.0),
        "ok": (-999.0, 0.5),
    },
    "ulcer_index": {
        "good": (0.0, 5.0),
        "ok": (5.0, 20.0),
    },
}


def _classify(value: float, metric: str) -> str:
    """Return GOOD, OK, or BAD for a single metric value."""
    thresholds = _THRESHOLDS.get(metric)
    if thresholds is None:
        return "UNKNOWN"

    good_lo, good_hi = thresholds["good"]
    ok_lo, ok_hi = thresholds["ok"]

    if ok_lo <= value <= ok_hi:
        return "OK"
    if good_lo <= value <= good_hi:
        return "GOOD"
    return "BAD"


def _status_color(status: str) -> str:
    """ANSI colour for status text."""
    colors = {
        "GOOD": "GREEN",
        "OK": "YELLOW",
        "BAD": "RED",
        "UNKNOWN": "WHITE",
    }
    return colors.get(status, "WHITE")


@dataclass
class RiskGauge:
    """Single risk metric gauge."""

    name: str
    value: float
    unit: str = ""
    min_val: float = 0.0
    max_val: float = 100.0
    _metric_key: str = ""  # for _classify lookup

    def _clamped_value(self) -> float:
        """Clamp value to [min_val, max_val] for bar positioning."""
        return max(self.min_val, min(self.max_val, self.value))

    def _bar_fraction(self) -> float:
        """Fraction 0..1 for bar width."""
        if self.max_val == self.min_val:
            return 0.0
        return (self._clamped_value() - self.min_val) / (self.max_val - self.min_val)

    def render(self) -> str:
        """Render a single gauge as a single line."""
        frac = self._bar_fraction()
        filled = round(frac * _GAUGE_WIDTH)
        bar = "\u2588" * filled + "\u2591" * (_GAUGE_WIDTH - filled)
        status = (
            _classify(self.value, self._metric_key)
            if self._metric_key
            else "UNKNOWN"
        )
        sc = _status_color(status)

        val_str = f"{self.value:.2f}"
        if self.unit:
            val_str += self.unit

        label = f" {self.name:<22} [{bar}] {val_str:>12} [{sc}]"
        return label

    def __str__(self) -> str:
        return self.render()


@dataclass
class _GaugeGroup:
    """Container for a group of gauges (e.g. 'Risk Metrics')."""

    title: str
    gauges: list[RiskGauge] = field(default_factory=list)


def render_gauge_group(group: _GaugeGroup, width: int = 80) -> list[str]:
    """Render a group of gauges to a list of text lines."""
    lines: list[str] = []
    bar = "\u2550" * (width - 2)
    header = f" \u2554{bar}\u2557"
    sep = f" \u255c{bar}\u255e"
    footer = f" \u255a{bar}\u255d"
    side = " \u2551 "
    pad = width - len(side) - 1  # minus trailing space

    lines.append(header)
    lines.append(f"{side}{group.title:<{pad - len(side) + 1}}\u2551")
    lines.append(sep)

    for gauge in group.gauges:
        line = gauge.render()
        padded = line.ljust(width - len(side) - 1)
        lines.append(f"{side}{padded}\u2551")

    lines.append(footer)
    return lines


# ── Convenience: build the 9-metric report from a risk dict ────────────

_RANGE: dict[str, tuple[float, float]] = {
    "sharpe_ratio": (-3.0, 5.0),
    "sortino_ratio": (-3.0, 5.0),
    "max_drawdown": (-50.0, 0.0),
    "var_95": (0.0, 15.0),
    "beta": (0.0, 3.0),
    "alpha": (-20.0, 30.0),
    "treynor_ratio": (-20.0, 50.0),
    "calmar_ratio": (-3.0, 10.0),
    "ulcer_index": (0.0, 30.0),
}


def _build_gauge(metric: str, value: Any, unit: str = "") -> RiskGauge:
    """Build a RiskGauge from a metric name / value pair."""
    lo, hi = _RANGE.get(metric, (0.0, 100.0))
    if isinstance(value, (int, float)):
        g = RiskGauge(
            metric.replace("_", " ").title(),
            float(value),
            unit,
            lo,
            hi,
        )
        g._metric_key = metric
        return g
    g = RiskGauge(
        metric.replace("_", " ").title(),
        0.0,
        unit,
        lo,
        hi,
    )
    g._metric_key = metric
    return g


def build_risk_gauges(report: dict[str, Any]) -> _GaugeGroup:
    """Build a GaugeGroup from a risk report dict."""
    gauges: list[RiskGauge] = []

    # Flat metrics
    flat_metrics = [
        ("sharpe_ratio", ""),
        ("sortino_ratio", ""),
        ("beta", ""),
        ("alpha", ""),
        ("treynor_ratio", ""),
        ("calmar_ratio", ""),
        ("ulcer_index", ""),
    ]

    for key, unit in flat_metrics:
        val = report.get(key)
        if val is not None and isinstance(val, (int, float)):
            gauges.append(_build_gauge(key, val, unit))

    # Max drawdown — nested dict
    mdd = report.get("max_drawdown", report.get("max_drawdown_pct"))
    if isinstance(mdd, dict):
        dd_val = mdd.get("max_drawdown_pct", 0)
    elif isinstance(mdd, (int, float)):
        dd_val = mdd
    else:
        dd_val = 0
    gauges.append(_build_gauge("max_drawdown", dd_val, "%"))

    # VaR — nested dict
    var_data = report.get("var", report.get("var_95"))
    if isinstance(var_data, dict):
        var_val = var_data.get(
            "parametric_var_daily",
            var_data.get("parametric_var_annual", 0),
        )
    elif isinstance(var_data, (int, float)):
        var_val = var_data
    else:
        var_val = 0
    gauges.append(_build_gauge("var_95", var_val))

    return _GaugeGroup(title="Risk Metrics", gauges=gauges)


def render_risk_report(report: dict[str, Any], width: int = 80) -> list[str]:
    """Render the full 9-metric risk report as ASCII gauges."""
    group = build_risk_gauges(report)
    return render_gauge_group(group, width)
