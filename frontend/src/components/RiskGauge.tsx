/**
 * RiskGauge — a single risk metric displayed as a card with color-coded value.
 *
 * Used by AnalyticsPage to render each of the 9 risk metrics in a grid.
 * Supports "higher-is-better", "lower-is-better", and "closer-to-1-is-better"
 * colour grading so users instantly see whether a metric is healthy.
 */

interface RiskMetricDef {
  key: string
  label: string
  description: string
  format: (v: number) => string
  direction: 'higher' | 'lower' | 'neutral' | 'closer-to-1'
  /** Optional thresholds for health colours (low → mid → high value) */
  thresholds?: [number, number]
}

/* ── Metric definitions ─────────────────────────────────────────────── */

export const RISK_METRICS: RiskMetricDef[] = [
  {
    key: 'sharpe',
    label: 'Sharpe Ratio',
    description: 'Excess return per unit of risk (annualized). > 1.0 is good.',
    format: (v) => v.toFixed(2),
    direction: 'higher',
    thresholds: [0.5, 1.0],
  },
  {
    key: 'sortino',
    label: 'Sortino Ratio',
    description: 'Like Sharpe but penalizes only downside volatility. > 2.0 is excellent.',
    format: (v) => v.toFixed(2),
    direction: 'higher',
    thresholds: [1.0, 2.0],
  },
  {
    key: 'max_drawdown',
    label: 'Max Drawdown',
    description: 'Largest peak-to-trough decline. Smaller (closer to 0) is better.',
    format: (v) => `${(v * 100).toFixed(2)}%`,
    direction: 'lower',
    thresholds: [-0.1, -0.2],
  },
  {
    key: 'var_95_parametric',
    label: 'VaR (95%, Parametric)',
    description: 'Worst expected daily loss at 95% confidence (Gaussian).',
    format: (v) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    direction: 'lower',
    thresholds: [0, 0], // always show absolute value
  },
  {
    key: 'var_95_historical',
    label: 'VaR (95%, Historical)',
    description: 'Worst expected daily loss at 95% confidence (empirical).',
    format: (v) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
    direction: 'lower',
    thresholds: [0, 0],
  },
  {
    key: 'beta',
    label: 'Beta',
    description: 'Systematic risk vs benchmark. 1.0 = moves with market.',
    format: (v) => v.toFixed(2),
    direction: 'closer-to-1',
    thresholds: [0.8, 1.2],
  },
  {
    key: 'alpha',
    label: 'Alpha',
    description: 'Excess return vs CAPM expectation (annualized %). Positive is good.',
    format: (v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`,
    direction: 'higher',
    thresholds: [0, 2],
  },
  {
    key: 'treynor',
    label: 'Treynor Ratio',
    description: 'Annualized excess return per unit of beta. Higher is better.',
    format: (v) => v.toFixed(2),
    direction: 'higher',
    thresholds: [5, 10],
  },
  {
    key: 'calmar',
    label: 'Calmar Ratio',
    description: 'Annualized return / max drawdown. > 1.0 is good.',
    format: (v) => v.toFixed(2),
    direction: 'higher',
    thresholds: [0.5, 1.0],
  },
  {
    key: 'ulcer_index',
    label: 'Ulcer Index',
    description: 'Sqrt of mean squared drawdown. Lower is better.',
    format: (v) => v.toFixed(2),
    direction: 'lower',
    thresholds: [5, 10],
  },
  {
    key: 'annualized_return',
    label: 'Annualized Return',
    description: 'Geometric annualized return from daily data.',
    format: (v) => `${(v * 100).toFixed(2)}%`,
    direction: 'higher',
    thresholds: [0.05, 0.1],
  },
]

/* ── Health colour helpers ──────────────────────────────────────────── */

function gradeHigher(value: number, t: [number, number]): string {
  if (value >= t[1]) return 'text-positive'
  if (value >= t[0]) return 'text-warning'
  return 'text-negative'
}

function gradeLower(value: number, t: [number, number]): string {
  // VaR-style metrics where 0 is ideal (thresholds are both 0)
  if (t[0] === 0 && t[1] === 0) {
    const abs = Math.abs(value)
    return abs === 0 ? 'text-positive' : abs < 10000 ? 'text-warning' : 'text-negative'
  }
  if (value <= t[0]) return 'text-positive'
  if (value <= t[1]) return 'text-warning'
  return 'text-negative'
}

function gradeCloserTo1(value: number): string {
  const dist = Math.abs(value - 1.0)
  if (dist <= 0.2) return 'text-positive'
  if (dist <= 0.5) return 'text-warning'
  return 'text-negative'
}

function getHealthColor(metric: RiskMetricDef, value: number): string {
  const t = metric.thresholds
  if (!t) return ''

  switch (metric.direction) {
    case 'higher':
      return gradeHigher(value, t)
    case 'lower':
      return gradeLower(value, t)
    case 'closer-to-1':
      return gradeCloserTo1(value)
    default:
      return ''
  }
}

/* ── Component ──────────────────────────────────────────────────────── */

interface RiskGaugeProps {
  metric: RiskMetricDef
  value: number | undefined
  isLoading?: boolean
}

export default function RiskGauge({ metric, value, isLoading }: RiskGaugeProps) {
  const displayValue = isLoading ? '—' : value != null ? metric.format(value) : 'N/A'
  const healthColor = value != null ? getHealthColor(metric, value) : 'text-text-dim'

  return (
    <div
      className="group relative rounded border border-border bg-bg p-3 transition hover:border-accent/50"
      title={metric.description}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-text-dim text-xs">{metric.label}</span>
        {/* Health dot */}
        {!isLoading && value != null && (
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              healthColor === 'text-positive'
                ? 'bg-positive'
                : healthColor === 'text-warning'
                  ? 'bg-warning'
                  : healthColor === 'text-negative'
                    ? 'bg-negative'
                    : 'bg-text-dim'
            }`}
          />
        )}
      </div>
      <p className={`font-mono-financial text-lg font-semibold ${healthColor || 'text-text'}`}>{displayValue}</p>
      {/* Tooltip on hover */}
      <div className="pointer-events-none absolute -left-2 -right-2 top-full z-10 translate-y-1 opacity-0 transition group-hover:opacity-100">
        <p className="rounded border border-border bg-surface px-2 py-1 text-xs text-text-dim">
          {metric.description}
        </p>
      </div>
    </div>
  )
}
