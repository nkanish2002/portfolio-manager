"""Analytics screen — risk metrics and charts."""

from textual.screen import Screen
from textual.widgets import Header, Footer, Label, DataTable, Button
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual_plotext import PlotextPlot


class AnalyticsScreen(Screen):
    """Analytics screen with risk metrics and charts."""

    BINDINGS = [
        Binding("o", "open_charts", "Open Charts"),
        Binding("b", "benchmark", "Benchmark"),
        Binding("1", "range_1m", "1M"),
        Binding("3", "range_3m", "3M"),
        Binding("6", "range_6m", "6M"),
        Binding("y", "range_1y", "1Y"),
        Binding("a", "range_all", "All"),
        Binding("r", "return", "Return"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        """Initialize analytics screen."""
        super().__init__()
        self.current_benchmark = "SPY"
        self.current_range = "1Y"

    def compose(self):
        """Compose the analytics layout."""
        yield Header()
        
        with Container():
            yield Label("PORTFOLIO MANAGER > Analytics", classes="header")
            
            # Risk metrics display
            yield Label("Risk Metrics (Portfolio vs SPY, 1Y)", classes="accent")
            yield Label("")
            
            # Risk metrics table
            metrics_table = DataTable()
            metrics_table.add_columns("Metric", "Value", "Status")
            metrics_table.add_row("Sharpe Ratio", "1.42", "GOOD")
            metrics_table.add_row("Sortino Ratio", "2.18", "GOOD")
            metrics_table.add_row("Max Drawdown", "-8.3%", "OK")
            metrics_table.add_row("VaR(95%)", "-$4,231", "OK")
            metrics_table.add_row("Beta", "0.95", "NEUTRAL")
            metrics_table.add_row("Alpha", "+3.2%", "GOOD")
            metrics_table.add_row("Treynor Ratio", "12.4", "GOOD")
            metrics_table.add_row("Calmar Ratio", "4.2", "GOOD")
            metrics_table.add_row("Ulcer Index", "2.1", "OK")
            yield metrics_table
            
            yield Label("")
            
            # Chart area
            yield Label("NAV History + Benchmark Overlay", classes="accent")
            yield Label("[Use textual-plotext for charts]", classes="warning")
            
            # Placeholder for plotext chart
            chart = PlotextPlot()
            chart.title("NAV History")
            chart.xlabel("Date")
            chart.ylabel("Value")
            yield chart
            
            # Benchmark and range controls
            yield Label(f"Benchmark: {self.current_benchmark} [SPY] [QQQ] [Custom]")
            yield Label(f"Range: {self.current_range} [1]M [3]M [6]M [1]Y [A]ll")
        
        yield Footer()

    def action_open_charts(self) -> None:
        """Open detailed charts (if implemented)."""
        # TODO: Implement detailed chart view
        pass

    def action_benchmark(self) -> None:
        """Cycle through benchmark options."""
        benchmarks = ["SPY", "QQQ", "Custom"]
        idx = benchmarks.index(self.current_benchmark) if self.current_benchmark in benchmarks else 0
        self.current_benchmark = benchmarks[(idx + 1) % len(benchmarks)]

    def action_range_1m(self) -> None:
        self.current_range = "1M"
    
    def action_range_3m(self) -> None:
        self.current_range = "3M"
    
    def action_range_6m(self) -> None:
        self.current_range = "6M"
    
    def action_range_1y(self) -> None:
        self.current_range = "1Y"
    
    def action_range_all(self) -> None:
        self.current_range = "ALL"
    
    def action_return(self) -> None:
        """Show return metrics."""
        pass
