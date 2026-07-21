"""HTML report generator — standalone portfolio snapshot (like the July 17 3-basket report).

Generates a self-contained HTML file with inline CSS and embedded data.
The report covers:
  - Portfolio summary (NAV, P&L, position count)
  - Basket allocation (target vs actual, color-coded)
  - Position table (symbol, qty, price, value, P&L)
  - Risk metrics (9 metrics with benchmark comparison)
  - Allocation breakdown (sector, region, asset class)
  - Transaction history summary

All data is provided as a Python dict by the caller; this service only
assembles the HTML template. This keeps the service pure and testable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

log = structlog.get_logger()


# ── HTML template ──────────────────────────────────────────────────────

_REPORT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --text-dim: #8b949e;
      --accent: #10b981;
      --positive: #3fb950;
      --negative: #f85149;
      --warning: #d29922;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    h2 {{ font-size: 1.1rem; margin: 1.5rem 0 0.75rem; color: var(--text-dim); }}
    .subtitle {{ color: var(--text-dim); font-size: 0.85rem; margin-bottom: 1.5rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 1rem; font-size: 0.85rem; }}
    th {{ text-align: left; color: var(--text-dim); border-bottom: 1px solid var(--border); padding: 0.5rem; font-weight: 500; }}
    td {{ border-bottom: 1px solid var(--border); padding: 0.5rem; }}
    tr:hover td {{ background: var(--surface); }}
    .mono {{ font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; }}
    .positive {{ color: var(--positive); }}
    .negative {{ color: var(--negative); }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
    .kpi-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 1rem; }}
    .kpi-label {{ font-size: 0.75rem; color: var(--text-dim); }}
    .kpi-value {{ font-size: 1.25rem; font-weight: 600; margin-top: 0.25rem; }}
    .bar-row {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }}
    .bar-name {{ min-width: 140px; font-size: 0.85rem; }}
    .bar-track {{ flex: 1; height: 8px; background: var(--bg); border-radius: 4px; overflow: hidden; position: relative; }}
    .bar-fill {{ height: 100%; border-radius: 4px; }}
    .bar-target {{ position: absolute; top: 0; height: 100%; width: 1px; background: var(--text-dim); }}
    .bar-label {{ min-width: 100px; font-size: 0.85rem; text-align: right; color: var(--text-dim); }}
    .risk-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }}
    .risk-item {{ background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 0.75rem; }}
    .risk-label {{ font-size: 0.75rem; color: var(--text-dim); }}
    .risk-value {{ font-size: 1rem; font-weight: 600; margin-top: 0.25rem; }}
    .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{title}</h1>
    <p class="subtitle">Generated {generated_at} — Portfolio Manager</p>

    <!-- ── KPI Summary ──────────────────────────────────────────── -->
    <h2>Portfolio Summary</h2>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Total Value (NAV)</div>
        <div class="kpi-value mono">${total_value}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total P&L</div>
        <div class="kpi-value mono {pnl_class}">${pnl_display}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Positions</div>
        <div class="kpi-value mono">{position_count}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Baskets</div>
        <div class="kpi-value mono">{basket_count}</div>
      </div>
    </div>

    <!-- ── Basket Allocation ────────────────────────────────────── -->
    <h2>Basket Allocation (Target vs Actual)</h2>
    <div style="margin-bottom: 1rem;">
{basket_rows}
    </div>

    <!-- ── Positions ────────────────────────────────────────────── -->
    <h2>Positions</h2>
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th style="text-align:right">Qty</th>
          <th style="text-align:right">Price</th>
          <th style="text-align:right">Value</th>
          <th style="text-align:right">P&L</th>
          <th style="text-align:right">P&L %</th>
          <th>Sector</th>
        </tr>
      </thead>
      <tbody>
{position_rows}
      </tbody>
    </table>

    <!-- ── Risk Metrics ─────────────────────────────────────────── -->
    <h2>Risk Metrics (vs {benchmark}, {risk_period})</h2>
    <div class="risk-grid">
{risk_items}
    </div>

    <!-- ── Allocation by Sector ─────────────────────────────────── -->
    <h2>Allocation by Sector</h2>
    <table>
      <thead>
        <tr>
          <th>Sector</th>
          <th style="text-align:right">Value</th>
          <th style="text-align:right">%</th>
        </tr>
      </thead>
      <tbody>
{sector_rows}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


# ── Helper functions ───────────────────────────────────────────────────


def _fmt_currency(value: float) -> str:
    """Format a float as a dollar amount (commas, 2 decimals)."""
    return f"{abs(value):,.2f}"


def _fmt_pct(value: float) -> str:
    """Format a float as a percentage."""
    return f"{value:+.2f}%"


def _color_class(value: float) -> str:
    """Return 'positive' or 'negative' CSS class based on sign."""
    return "positive" if value >= 0 else "negative"


# ── Public API ─────────────────────────────────────────────────────────


def generate_portfolio_report(data: dict[str, Any]) -> bytes:
    """Generate a standalone HTML report from portfolio data.

    ``data`` should contain:
      - ``portfolio_name`` (str) — portfolio display name
      - ``total_value`` (float) — NAV
      - ``total_pnl`` (float) — unrealized gain/loss
      - ``position_count`` (int) — number of positions
      - ``basket_count`` (int) — number of baskets
      - ``baskets`` (list[dict]) — each with: name, color, target_allocation, actual_allocation
      - ``positions`` (list[dict]) — each with: symbol, quantity, current_price, market_value, unrealized_gain, unrealized_gain_pct, sector
      - ``risk_metrics`` (dict) — key-value risk metric map (optional, defaults to empty)
      - ``benchmark`` (str) — benchmark ticker (default: "SPY")
      - ``risk_period`` (str) — period label (default: "1Y")
      - ``sector_allocation`` (dict[str, float]) — sector → % (optional)

    Returns raw HTML bytes ready for file download.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    total_value = data.get("total_value", 0.0)
    total_pnl = data.get("total_pnl", 0.0)
    position_count = data.get("position_count", 0)
    basket_count = data.get("basket_count", 0)
    basket_rows_data = data.get("baskets", [])
    positions_data = data.get("positions", [])
    risk_metrics = data.get("risk_metrics", {})
    benchmark = data.get("benchmark", "SPY")
    risk_period = data.get("risk_period", "1Y")
    sector_allocation = data.get("sector_allocation", {})

    pnl_class = _color_class(total_pnl)
    pnl_display = f"{'+' if total_pnl >= 0 else ''}${_fmt_currency(total_pnl)}"

    # Build basket rows
    basket_rows_parts: list[str] = []
    for b in basket_rows_data:
        name = b.get("name", "Unknown")
        color = b.get("color", "#8b949e")
        target = b.get("target_allocation", 0)
        actual = b.get("actual_allocation", 0)
        fill_width = min(actual, 100)
        target_pos = min(target, 100)
        basket_rows_parts.append(
            f'<div class="bar-row">'
            f'  <span class="bar-name"><span class="dot" style="background:{color}"></span>{name}</span>'
            f'  <div class="bar-track">'
            f'    <div class="bar-fill" style="width:{fill_width}%;background:{color}"></div>'
            f'    <div class="bar-target" style="left:{target_pos}%"></div>'
            f"  </div>"
            f'  <span class="bar-label">{actual:.1f}% / {target:.0f}% target</span>'
            f"</div>"
        )
    basket_rows = (
        "\n".join(basket_rows_parts)
        if basket_rows_parts
        else '<p style="color:var(--text-dim);font-size:0.85rem;">No baskets configured</p>'
    )

    # Build position rows
    position_rows_parts: list[str] = []
    for pos in positions_data:
        symbol = pos.get("symbol", "?")
        qty = float(pos.get("quantity", 0))
        price = float(pos.get("current_price", 0))
        mv = float(pos.get("market_value", 0))
        gain = float(pos.get("unrealized_gain", 0))
        gain_pct = float(pos.get("unrealized_gain_pct", 0))
        sector = pos.get("sector") or "Unknown"
        pos_class = _color_class(gain)

        position_rows_parts.append(
            f"<tr>"
            f"  <td>{symbol}</td>"
            f'  <td class="mono" style="text-align:right">{qty:,.3g}</td>'
            f'  <td class="mono" style="text-align:right">${price:,.2f}</td>'
            f'  <td class="mono" style="text-align:right">${mv:,.2f}</td>'
            f'  <td class="mono {pos_class}" style="text-align:right">{_fmt_pct(gain).replace("+", "+")}</td>'
            f'  <td class="mono {pos_class}" style="text-align:right">{gain_pct:+.2f}%</td>'
            f"  <td>{sector}</td>"
            f"</tr>"
        )
    position_rows = (
        "\n".join(position_rows_parts)
        if position_rows_parts
        else '<tr><td colspan="7" style="color:var(--text-dim)">No positions</td></tr>'
    )

    # Build risk metric items
    risk_labels = {
        "sharpe": "Sharpe Ratio",
        "sortino": "Sortino Ratio",
        "max_drawdown": "Max Drawdown",
        "var_95_parametric": "VaR 95% (Parametric)",
        "var_95_historical": "VaR 95% (Historical)",
        "beta": "Beta",
        "alpha": "Alpha",
        "treynor": "Treynor Ratio",
        "calmar": "Calmar Ratio",
        "ulcer_index": "Ulcer Index",
        "annualized_return": "Annualized Return",
    }

    risk_items_parts: list[str] = []
    for key, display_name in risk_labels.items():
        value = risk_metrics.get(key)
        if value is None:
            continue
        if isinstance(value, float):
            if key in ("var_95_parametric", "var_95_historical"):
                display_val = f"-${abs(value):,.0f}"
            elif key in ("max_drawdown",):
                display_val = f"{value:.2%}"
            elif key in ("alpha", "annualized_return"):
                display_val = f"{value:+.2%}"
            elif key in ("ulcer_index",):
                display_val = f"{value:.2f}"
            else:
                display_val = f"{value:.2f}"
        else:
            display_val = str(value)

        risk_items_parts.append(
            f'<div class="risk-item">'
            f'  <div class="risk-label">{display_name}</div>'
            f'  <div class="risk-value mono">{display_val}</div>'
            f"</div>"
        )
    risk_items = (
        "\n".join(risk_items_parts)
        if risk_items_parts
        else '<p style="color:var(--text-dim);font-size:0.85rem;">Insufficient data for risk metrics</p>'
    )

    # Build sector allocation rows
    sector_rows_parts: list[str] = []
    for sector_name, pct in sorted(sector_allocation.items(), key=lambda x: -x[1]):
        sector_rows_parts.append(
            f"<tr>"
            f"  <td>{sector_name}</td>"
            f'  <td class="mono" style="text-align:right">{pct:.2%}</td>'
            f'  <td class="mono" style="text-align:right">{pct:.1%}</td>'
            f"</tr>"
        )
    sector_rows = (
        "\n".join(sector_rows_parts)
        if sector_rows_parts
        else '<tr><td colspan="3" style="color:var(--text-dim)">No allocation data</td></tr>'
    )

    # Format template
    html = _REPORT_HTML
    html = html.format(
        title=data.get("portfolio_name", "Portfolio Report"),
        generated_at=now,
        total_value=_fmt_currency(total_value),
        pnl_class=pnl_class,
        pnl_display=pnl_display,
        position_count=position_count,
        basket_count=basket_count,
        basket_rows=basket_rows,
        position_rows=position_rows,
        benchmark=benchmark,
        risk_period=risk_period,
        risk_items=risk_items,
        sector_rows=sector_rows,
    )

    log.info("report_generator.generated", size=len(html))
    return html.encode("utf-8")


def generate_report_filename(portfolio_name: str) -> str:
    """Generate a download filename for the report."""
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    safe_name = portfolio_name.replace(" ", "_").lower()
    return f"portfolio_report_{safe_name}_{now}.html"
