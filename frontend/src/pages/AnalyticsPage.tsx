/**
 * Analytics page — risk metrics, benchmark selector, time range selector, charts.
 *
 * Segment 6.1: Risk metrics table (9+ metrics, color-coded)
 * Segment 6.2: NAV chart, allocation pie, drawdown chart
 * Segment 6.3: Monthly returns heatmap, benchmark comparison
 *
 * Data is fetched from the analytics backend routes:
 *   GET /api/v1/portfolios/{id}/analytics/risk?period=X&benchmark=Y
 *   GET /api/v1/portfolios/{id}/charts/nav?period=X
 *   GET /api/v1/portfolios/{id}/charts/drawdown?period=X
 *   GET /api/v1/portfolios/{id}/charts/allocation?group_by=Y
 *   GET /api/v1/portfolios/{id}/charts/monthly-returns?period=X
 *   GET /api/v1/portfolios/{id}/charts/benchmark-comparison?period=X&benchmark=Y
 */

import { useEffect, useState } from 'react'
import { analyticsApi, type Benchmark } from '@/services/api'
import { usePortfolioStore } from '@/store/portfolioStore'
import RiskGauge, { RISK_METRICS } from '@/components/RiskGauge'
import NavChart from '@/components/NavChart'
import AllocationPie from '@/components/AllocationPie'
import DrawdownChart from '@/components/DrawdownChart'
import MonthlyReturnsHeatmap from '@/components/MonthlyReturnsHeatmap'
import BenchmarkComparison from '@/components/BenchmarkComparison'

/* ── Constants ──────────────────────────────────────────────────────── */

const PERIODS = [
  { label: '1M', value: '1mo' },
  { label: '3M', value: '3mo' },
  { label: '6M', value: '6mo' },
  { label: '1Y', value: '1y' },
  { label: 'All', value: 'max' },
]

const BENCHMARKS: Benchmark[] = [
  { id: 'spy', symbol: 'SPY', name: 'S&P 500 (SPY)', created_at: '' },
  { id: 'qqq', symbol: 'QQQ', name: 'NASDAQ 100 (QQQ)', created_at: '' },
]

/* ── Types ──────────────────────────────────────────────────────────── */

interface NavPoint {
  date: string
  nav: number
}

interface DrawdownPoint {
  date: string
  drawdown: number
}

interface AllocationSlice {
  key: string
  value: number
  pct: number
}

interface MonthlyReturnPoint {
  month: string
  return: number
}

interface BenchmarkComparisonPoint {
  date: string
  portfolio: number
  benchmark: number
}

interface BenchmarkComparisonMetrics {
  tracking_error?: number
  information_ratio?: number
  excess_return_annualized?: number
  cumulative_excess_return?: number
}

/* ── Page ───────────────────────────────────────────────────────────── */

export default function AnalyticsPage() {
  const { selectedId } = usePortfolioStore()
  const [period, setPeriod] = useState('1y')
  const [benchmark, setBenchmark] = useState('SPY')
  const [allocationGroupBy, setAllocationGroupBy] = useState('sector')

  // Risk metrics
  const [riskMetrics, setRiskMetrics] = useState<Record<string, number>>({})
  const [riskLoading, setRiskLoading] = useState(true)
  const [riskError, setRiskError] = useState<string | null>(null)
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null)

  // NAV chart data
  const [navSeries, setNavSeries] = useState<NavPoint[]>([])
  const [navLoading, setNavLoading] = useState(true)

  // Drawdown chart data
  const [ddSeries, setDdSeries] = useState<DrawdownPoint[]>([])
  const [ddMax, setDdMax] = useState(0)
  const [ddLoading, setDdLoading] = useState(true)

  // Allocation data
  const [allocSlices, setAllocSlices] = useState<AllocationSlice[]>([])

  // Monthly returns heatmap
  const [monthlySeries, setMonthlySeries] = useState<MonthlyReturnPoint[]>([])
  const [monthlyLoading, setMonthlyLoading] = useState(true)

  // Benchmark comparison
  const [benchSeries, setBenchSeries] = useState<BenchmarkComparisonPoint[]>([])
  const [benchComparison, setBenchComparison] = useState<BenchmarkComparisonMetrics | undefined>(undefined)
  const [benchLoading, setBenchLoading] = useState(true)

  /* ── Fetch risk metrics ──────────────────────────────────────────── */

  useEffect(() => {
    if (!selectedId) return
    setRiskLoading(true)
    setRiskError(null)

    analyticsApi
      .risk(selectedId, { period, benchmark })
      .then((data: Record<string, unknown>) => {
        setRiskMetrics((data as any).metrics ?? {})
        setFetchedAt(new Date())
      })
      .catch((err: unknown) => {
        setRiskError(err instanceof Error ? err.message : 'Failed to load risk metrics')
        setRiskMetrics({})
      })
      .finally(() => setRiskLoading(false))
  }, [selectedId, period, benchmark])

  /* ── Fetch NAV series ────────────────────────────────────────────── */

  useEffect(() => {
    if (!selectedId) return
    setNavLoading(true)

    analyticsApi
      .navChart(selectedId, { period })
      .then((data: Record<string, unknown>) => {
        setNavSeries(((data as any).series ?? []) as NavPoint[])
      })
      .catch(() => setNavSeries([]))
      .finally(() => setNavLoading(false))
  }, [selectedId, period])

  /* ── Fetch drawdown series ───────────────────────────────────────── */

  useEffect(() => {
    if (!selectedId) return
    setDdLoading(true)

    analyticsApi
      .drawdownChart(selectedId, { period })
      .then((data: Record<string, unknown>) => {
        setDdSeries(((data as any).series ?? []) as DrawdownPoint[])
        setDdMax((data as any).max_drawdown ?? 0)
      })
      .catch(() => {
        setDdSeries([])
        setDdMax(0)
      })
      .finally(() => setDdLoading(false))
  }, [selectedId, period])

  /* ── Fetch allocation slices ─────────────────────────────────────── */

  useEffect(() => {
    if (!selectedId) return

    analyticsApi
      .allocationChart(selectedId, { group_by: allocationGroupBy })
      .then((data: Record<string, unknown>) => {
        setAllocSlices(((data as any).slices ?? []) as AllocationSlice[])
      })
      .catch(() => setAllocSlices([]))
  }, [selectedId, allocationGroupBy])

  /* ── Fetch monthly returns ──────────────────────────────────────── */

  useEffect(() => {
    if (!selectedId) return
    setMonthlyLoading(true)

    analyticsApi
      .monthlyReturns(selectedId, { period })
      .then((data: Record<string, unknown>) => {
        setMonthlySeries(((data as any).series ?? []) as MonthlyReturnPoint[])
      })
      .catch(() => setMonthlySeries([]))
      .finally(() => setMonthlyLoading(false))
  }, [selectedId, period])

  /* ── Fetch benchmark comparison ────────────────────────────────── */

  useEffect(() => {
    if (!selectedId) return
    setBenchLoading(true)

    analyticsApi
      .benchmarkComparison(selectedId, { period, benchmark })
      .then((data: Record<string, unknown>) => {
        setBenchSeries(((data as any).series ?? []) as BenchmarkComparisonPoint[])
        setBenchComparison((data as any).comparison as BenchmarkComparisonMetrics | undefined)
      })
      .catch(() => {
        setBenchSeries([])
        setBenchComparison(undefined)
      })
      .finally(() => setBenchLoading(false))
  }, [selectedId, period, benchmark])

  /* ── Empty / loading states ──────────────────────────────────────── */

  if (!selectedId) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Select a portfolio to view analytics</p>
      </div>
    )
  }

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="font-semibold text-xl text-text">Analytics</h1>

        {fetchedAt && (
          <span className="text-text-dim text-xs">
            Updated {fetchedAt.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* ── Controls bar ───────────────────────────────────────────── */}
      <div className="mb-6 flex flex-col gap-3 rounded border border-border bg-surface p-4 sm:flex-row sm:items-end">
        {/* Time range selector (buttons, not a form control — use a span label) */}
        <div className="block text-xs text-text-dim">
          Time Range
          <div className="mt-1 flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setPeriod(p.value)}
                className={`rounded border px-3 py-1 text-sm transition ${
                  period === p.value
                    ? 'border-accent bg-accent/10 text-accent'
                    : 'border-border text-text-dim hover:border-accent hover:text-accent'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Benchmark selector */}
        <label className="block text-xs text-text-dim">
          Benchmark
          <select
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
            className="mt-1 rounded border border-border bg-bg px-3 py-1 text-sm text-text outline-none focus:border-accent"
          >
            {BENCHMARKS.map((b) => (
              <option key={b.id} value={b.symbol}>
                {b.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* ── Error state ────────────────────────────────────────────── */}
      {riskError && (
        <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-4 py-3 text-negative text-sm">
          {riskError}
        </div>
      )}

      {/* ── Risk metrics grid ──────────────────────────────────────── */}
      <div className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-sm text-text">Risk Metrics</h2>
          <span className="text-text-dim text-xs">
            vs {benchmark} · {PERIODS.find((p) => p.value === period)?.label}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {RISK_METRICS.map((metric) => (
            <RiskGauge
              key={metric.key}
              metric={metric}
              value={riskMetrics[metric.key]}
              isLoading={riskLoading}
            />
          ))}
        </div>
      </div>

      {/* ── Charts row: NAV + Allocation ───────────────────────────── */}
      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        {/* NAV growth chart */}
        <div className="rounded border border-border bg-surface p-4">
          <h2 className="mb-3 font-semibold text-sm text-text">NAV Growth</h2>
          <NavChart series={navSeries} isLoading={navLoading} height={280} />
        </div>

        {/* Allocation donut */}
        <div className="rounded border border-border bg-surface p-4">
          <h2 className="mb-3 font-semibold text-sm text-text">Allocation</h2>
          <AllocationPie
            slices={allocSlices}
            groupBy={allocationGroupBy}
            onChangeGroupBy={setAllocationGroupBy}
            height={280}
          />
        </div>
      </div>

      {/* ── Drawdown chart (full width) ────────────────────────────── */}
      <div className="mb-6 rounded border border-border bg-surface p-4">
        <h2 className="mb-3 font-semibold text-sm text-text">Drawdown</h2>
        <DrawdownChart series={ddSeries} maxDrawdown={ddMax} isLoading={ddLoading} height={200} />
      </div>

      {/* ── Monthly returns heatmap (full width) ────────────────────── */}
      <div className="mb-6 rounded border border-border bg-surface p-4">
        <h2 className="mb-3 font-semibold text-sm text-text">Monthly Returns</h2>
        <MonthlyReturnsHeatmap series={monthlySeries} isLoading={monthlyLoading} />
      </div>

      {/* ── Benchmark comparison (full width) ──────────────────────── */}
      <div className="mb-6 rounded border border-border bg-surface p-4">
        <h2 className="mb-3 font-semibold text-sm text-text">
          Benchmark Comparison <span className="text-text-dim font-normal">· vs {benchmark}</span>
        </h2>
        <BenchmarkComparison
          series={benchSeries}
          benchmark={benchmark}
          comparison={benchComparison}
          isLoading={benchLoading}
          height={280}
        />
      </div>

      {/* ── Health legend ──────────────────────────────────────────── */}
      <div className="rounded border border-border bg-surface p-4">
        <h3 className="mb-2 font-medium text-xs text-text-dim">Health Indicators</h3>
        <div className="flex flex-wrap gap-4 text-xs text-text-dim">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-positive" />
            Healthy
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-warning" />
            Fair
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-negative" />
            Concerning
          </span>
          <span className="text-text-dim ml-4">Hover over any metric for details</span>
        </div>
      </div>
    </div>
  )
}
