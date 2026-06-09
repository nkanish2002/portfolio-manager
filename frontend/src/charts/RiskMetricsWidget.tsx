interface RiskMetricProps {
  label: string;
  value: string;
  threshold?: 'good' | 'warning' | 'bad';
  subtext?: string;
}

function RiskMetric({ label, value, threshold = 'good', subtext }: RiskMetricProps) {
  const colorMap = {
    good: 'text-emerald-400',
    warning: 'text-amber-400',
    bad: 'text-red-400',
  };

  const borderColorMap = {
    good: 'border-emerald-500/30',
    warning: 'border-amber-500/30',
    bad: 'border-red-500/30',
  };

  return (
    <div className={`bg-slate-900/80 border ${borderColorMap[threshold]} rounded-none p-3 sm:p-4 transition-all hover:bg-slate-800/80`}>
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-lg sm:text-xl font-bold ${colorMap[threshold]}`}>{value}</div>
      {subtext && <div className="text-[10px] text-slate-600 mt-1">{subtext}</div>}
    </div>
  );
}

interface RiskMetricsWidgetProps {
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  valueAtRisk: number;
  beta: number;
  alpha: number;
  treynorRatio: number;
  calmarRatio: number;
  ulcerIndex: number;
  className?: string;
}

function getMetricThreshold(label: string, value: number): 'good' | 'warning' | 'bad' {
  switch (label) {
    case 'Sharpe Ratio':
      return value >= 1 ? 'good' : value >= 0.5 ? 'warning' : 'bad';
    case 'Sortino Ratio':
      return value >= 1.5 ? 'good' : value >= 0.8 ? 'warning' : 'bad';
    case 'Max Drawdown':
      return Math.abs(value) <= 10 ? 'good' : Math.abs(value) <= 20 ? 'warning' : 'bad';
    case 'VaR (95%)':
      return Math.abs(value) <= 5 ? 'good' : Math.abs(value) <= 10 ? 'warning' : 'bad';
    case 'Beta':
      return value >= 0.8 && value <= 1.2 ? 'good' : value >= 0.5 && value <= 1.5 ? 'warning' : 'bad';
    case 'Alpha':
      return value > 0 ? 'good' : value > -1 ? 'warning' : 'bad';
    case 'Treynor Ratio':
      return value >= 0.05 ? 'good' : value >= 0.02 ? 'warning' : 'bad';
    case 'Calmar Ratio':
      return value >= 1 ? 'good' : value >= 0.5 ? 'warning' : 'bad';
    case 'Ulcer Index':
      return value <= 5 ? 'good' : value <= 10 ? 'warning' : 'bad';
    default:
      return 'good';
  }
}

export function RiskMetricsWidget({
  sharpeRatio,
  sortinoRatio,
  maxDrawdown,
  valueAtRisk,
  beta,
  alpha,
  treynorRatio,
  calmarRatio,
  ulcerIndex,
  className = '',
}: RiskMetricsWidgetProps) {
  const metrics: RiskMetricProps[] = [
    { label: 'Sharpe Ratio', value: sharpeRatio.toFixed(2), threshold: getMetricThreshold('Sharpe Ratio', sharpeRatio), subtext: 'Return per unit of risk' },
    { label: 'Sortino Ratio', value: sortinoRatio.toFixed(2), threshold: getMetricThreshold('Sortino Ratio', sortinoRatio), subtext: 'Downside risk-adjusted return' },
    { label: 'Max Drawdown', value: `${maxDrawdown.toFixed(2)}%`, threshold: getMetricThreshold('Max Drawdown', maxDrawdown) },
    { label: 'VaR (95%)', value: `${valueAtRisk.toFixed(2)}%`, threshold: getMetricThreshold('VaR (95%)', valueAtRisk), subtext: '95% daily VaR' },
    { label: 'Beta', value: beta.toFixed(2), threshold: getMetricThreshold('Beta', beta), subtext: 'Market sensitivity' },
    { label: 'Alpha', value: alpha.toFixed(2), threshold: getMetricThreshold('Alpha', alpha), subtext: 'Excess return vs benchmark' },
    { label: 'Treynor Ratio', value: treynorRatio.toFixed(4), threshold: getMetricThreshold('Treynor Ratio', treynorRatio), subtext: 'Return per unit of systematic risk' },
    { label: 'Calmar Ratio', value: calmarRatio.toFixed(2), threshold: getMetricThreshold('Calmar Ratio', calmarRatio), subtext: 'Return / Max Drawdown' },
    { label: 'Ulcer Index', value: ulcerIndex.toFixed(2), threshold: getMetricThreshold('Ulcer Index', ulcerIndex), subtext: 'Depth & duration of drawdown' },
  ];

  return (
    <div className={`space-y-3 ${className}`}>
      <h2 className="text-lg font-semibold text-white">Risk Metrics</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
        {metrics.map((m) => (
          <RiskMetric key={m.label} {...m} />
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-slate-500 pt-2 border-t border-slate-800">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-emerald-400 rounded-none inline-block"></span> Good
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-amber-400 rounded-none inline-block"></span> Warning
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-red-400 rounded-none inline-block"></span> Concern
        </span>
      </div>
    </div>
  );
}
