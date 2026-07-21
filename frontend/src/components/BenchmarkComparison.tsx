/**
 * BenchmarkComparison — portfolio vs benchmark overlay (normalized to 100).
 *
 * Uses TradingView Lightweight Charts to render two line series:
 *   - portfolio (green) and benchmark (blue), both rebased to start at 100.
 *
 * Backend response (via benchmarkComparison API):
 *   {
 *     series: [{ date, portfolio, benchmark }, ...],   // already normalized to 1.0
 *     benchmark: "SPY",
 *     comparison: { tracking_error, information_ratio,
 *                   excess_return_annualized, cumulative_excess_return }
 *   }
 *
 * The series is rebased from 1.0 → 100 here so the chart reads naturally
 * (100 = starting value).
 */

import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineSeries, type IChartApi, type ISeriesApi } from 'lightweight-charts'

interface BenchmarkComparisonProps {
  series: { date: string; portfolio: number; benchmark: number }[]
  benchmark: string
  comparison?: {
    tracking_error?: number
    information_ratio?: number
    excess_return_annualized?: number
    cumulative_excess_return?: number
  }
  isLoading?: boolean
  height?: number
}

/* ── Theme ──────────────────────────────────────────────────────────── */

const THEME = {
  bg: '#0d1117',
  grid: '#21262d',
  text: '#8b949e',
  portfolioLine: '#10b981', // emerald
  benchmarkLine: '#58a6ff', // blue
  crosshair: '#8b949e',
  tooltipBg: '#161b22',
  tooltipBorder: '#30363d',
}

/* ── Helpers ────────────────────────────────────────────────────────── */

function fmtPct(v: number | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${v >= 0 ? '+' : ''}${(v * 100).toFixed(digits)}%`
}

function fmtNum(v: number | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '—'
  return v.toFixed(digits)
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function BenchmarkComparison({
  series,
  benchmark,
  comparison,
  isLoading,
  height = 280,
}: BenchmarkComparisonProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const portSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const benchSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)

  /* ── Create chart on mount ───────────────────────────────────────── */

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: THEME.bg },
        textColor: THEME.text,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: THEME.grid },
        horzLines: { color: THEME.grid },
      },
      crosshair: {
        vertLine: { color: THEME.crosshair, style: 0, width: 1, labelBackgroundColor: THEME.tooltipBg },
        horzLine: { color: THEME.crosshair, style: 0, width: 1, labelBackgroundColor: THEME.tooltipBg },
      },
      rightPriceScale: {
        borderColor: THEME.tooltipBorder,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: THEME.tooltipBorder,
        timeVisible: false,
        rightOffset: 5,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    })

    chartRef.current = chart

    portSeriesRef.current = chart.addSeries(LineSeries, {
      color: THEME.portfolioLine,
      lineWidth: 2,
      lastValueVisible: true,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    })
    benchSeriesRef.current = chart.addSeries(LineSeries, {
      color: THEME.benchmarkLine,
      lineWidth: 2,
      lastValueVisible: true,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    })

    return () => {
      chart.remove()
      chartRef.current = null
      portSeriesRef.current = null
      benchSeriesRef.current = null
    }
  }, [])

  /* ── Update data ─────────────────────────────────────────────────── */

  useEffect(() => {
    if (!portSeriesRef.current || !benchSeriesRef.current || !chartRef.current) return

    // Rebase normalized (1.0) series to start at 100.
    const portData = series
      .filter((p) => p.portfolio != null && p.date != null)
      .map((p) => ({ time: p.date as string, value: p.portfolio * 100 }))
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))

    const benchData = series
      .filter((p) => p.benchmark != null && p.date != null)
      .map((p) => ({ time: p.date as string, value: p.benchmark * 100 }))
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))

    portSeriesRef.current.setData(portData)
    benchSeriesRef.current.setData(benchData)
    chartRef.current.timeScale().fitContent()
  }, [series])

  /* ── Resize observer ─────────────────────────────────────────────── */

  useEffect(() => {
    if (!containerRef.current || !chartRef.current) return
    const el = containerRef.current
    const chart = chartRef.current

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height: h } = entry.contentRect
        if (width > 0 && h > 0) {
          chart.applyOptions({ width, height: h })
        }
      }
    })

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  /* ── Legend ──────────────────────────────────────────────────────── */

  function Legend() {
    return (
      <div className="mb-2 flex flex-wrap items-center gap-4 text-xs">
        <span className="flex items-center gap-1.5 text-text">
          <span className="h-2 w-4 rounded-sm" style={{ backgroundColor: THEME.portfolioLine }} />
          Portfolio
        </span>
        <span className="flex items-center gap-1.5 text-text">
          <span className="h-2 w-4 rounded-sm" style={{ backgroundColor: THEME.benchmarkLine }} />
          {benchmark}
        </span>
        <span className="text-text-dim">Rebased to 100</span>
      </div>
    )
  }

  /* ── Comparison metrics row ──────────────────────────────────────── */

  function Metric({ label, value }: { label: string; value: string }) {
    return (
      <div className="rounded border border-border/50 bg-bg px-3 py-2">
        <div className="text-text-dim text-xs">{label}</div>
        <div className="font-mono-financial text-text text-sm">{value}</div>
      </div>
    )
  }

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div>
      <Legend />

      <div className="relative" style={{ height }}>
        <div ref={containerRef} style={{ height: '100%' }} />
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-text-dim">
            Loading benchmark comparison…
          </div>
        )}
        {!isLoading && !series.length && (
          <div className="absolute inset-0 flex items-center justify-center text-text-dim">
            No benchmark comparison data available for the selected period
          </div>
        )}
      </div>

      {comparison && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Metric label="Excess Return (ann.)" value={fmtPct(comparison.excess_return_annualized)} />
          <Metric label="Cumulative Excess" value={fmtPct(comparison.cumulative_excess_return)} />
          <Metric label="Tracking Error" value={fmtNum(comparison.tracking_error)} />
          <Metric label="Information Ratio" value={fmtNum(comparison.information_ratio)} />
        </div>
      )}
    </div>
  )
}