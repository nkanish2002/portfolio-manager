"""Risk gauge widget — horizontal bar chart with status indicators.

Displays a single risk metric as a horizontal bar in plotext, with
a text status indicator showing the value, threshold category (GOOD/WARNING/POOR),
and a comparison to the benchmark if available.
"""

from textual.containers import Container
from textual.widgets import Label, Static
from textual_plotext import PlotextPlot


class RiskGaugeWidget(Static):
    """Displays a single risk metric as a horizontal bar chart with status.

    Usage:
        gauge = RiskGaugeWidget(label="Sharpe Ratio", value=1.42, status="GOOD")
        yield gauge
        # Or set values after creation:
        gauge.update_gauge(label="Sharpe Ratio", value=1.42, status="GOOD",
                           benchmark=1.20)
    """

    def __init__(
        self,
        label: str = "",
        value: float = 0.0,
        status: str = "GOOD",
        benchmark: float | None = None,
    ) -> None:
        """Initialize risk gauge.

        Args:
            label: Metric name (e.g., "Sharpe Ratio")
            value: Current metric value
            status: "GOOD", "WARNING", or "POOR"
            benchmark: Optional benchmark value for comparison
        """
        super().__init__()
        self._label = label
        self._value = value
        self._status = status
        self._benchmark = benchmark
        self._plot = PlotextPlot()
        self._value_label = Label("")

        # Set CSS classes
        self.add_class("gauge-container")
        self._plot.add_class("gauge-plot")
        self._value_label.add_class("gauge-value")

        self._update_visuals()

    def compose(self):
        """Compose the gauge layout: plot above value label."""
        yield self._plot
        yield self._value_label

    def update_gauge(
        self,
        label: str,
        value: float,
        status: str,
        benchmark: float | None = None,
    ) -> None:
        """Update all gauge parameters and refresh the display.

        Args:
            label: New metric label
            value: New metric value
            status: New status category ("GOOD", "WARNING", "POOR")
            benchmark: Optional benchmark value
        """
        self._label = label
        self._value = value
        self._status = status
        self._benchmark = benchmark
        self._update_visuals()

    def _update_visuals(self) -> None:
        """Update the bar chart and value label."""
        color_map = {
            "GOOD": "#22C55E",
            "WARNING": "#F59E0B",
            "POOR": "#EF4444",
        }
        color = color_map.get(self._status, "#94A3B8")

        # Build the bar chart
        self._plot.clear_data()
        self._plot.plot_type = "scatter"
        self._plot.xlabel(self._label)
        self._plot.yticks(["value"], [""])

        # Bar: single point at the value
        self._plot.scatter([self._value], [1], symbol="#", color=color)

        # Set x-axis limits with padding
        abs_val = abs(self._value)
        if abs_val < 10:
            self._plot.xlim(-10, 10)
        elif abs_val < 100:
            self._plot.xlim(-100, 100)
        else:
            self._plot.xlim(-abs_val * 2, abs_val * 2)

        self._plot.ylim(0, 2)
        self._plot.hide_channel()
        self._plot.hide_grid()
        self._plot.xticks([], [])
        self._plot.yticks([1], [""])
        self._plot.canvas_color(color)
        self._plot.canvas_size(60, 1)

        # Update value label with status color
        status_symbols = {"GOOD": "OK", "WARNING": "WARN", "POOR": "BAD"}
        symbol = status_symbols.get(self._status, "?")
        val_str = f"{self._value:+.2f}"

        if self._benchmark is not None:
            val_str = f"{self._value:+.2f}"
            bm_str = f"BM:{self._benchmark:+.2f}"
            self._value_label.update(f"  {symbol} {val_str}   |   {bm_str}")
        else:
            self._value_label.update(f"  {symbol} {val_str}")

        self._value_label.remove_class("positive", "warning", "negative")
        if self._status == "GOOD":
            self._value_label.add_class("positive")
        elif self._status == "WARNING":
            self._value_label.add_class("warning")
        else:
            self._value_label.add_class("negative")

        self._plot.update_plot()
