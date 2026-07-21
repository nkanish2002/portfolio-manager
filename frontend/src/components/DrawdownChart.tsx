/**
 * DrawdownChart — Underwater drawdown area chart.
 *
 * Uses TradingView Lightweight Charts to show the portfolio's drawdown
 * over time (negative area below zero). Includes a max-drawdown label.
 *
 * Backend response:
 *   { series: [{ date: string, drawdown: number }, ...], max_drawdown: number }
 *
 * Implementation note: the chart container div is always rendered (even during
 * loading / empty states) so the chart-creation effect runs exactly once on
 * mount. States are overlaid on top of the container.
 */

import { useEffect, useRef } from 'react'
import { createChart, ColorType, AreaSeries, type IChartApi, type ISeriesApi } from 'lightweight-charts'

interface DrawdownChartProps {
  series: { date: string; drawdown: number }[]
  maxDrawdown: number
  isLoading?: boolean
  height?: number
}

/* ── Theme colours ──────────────────────────────────────────────────── */

const THEME = {
  bg: '#0d1117',
  grid: '#21262d',
  text: '#8b949e',
  line: '#f85149', // negative red
  crosshair: '#8b949e',
  tooltipBg: '#161b22',
  tooltipBorder: '#30363d',
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function DrawdownChart({ series, maxDrawdown, isLoading, height = 200 }: DrawdownChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null)

  /* ── Create chart on mount, destroy on unmount ───────────────────── */

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
        scaleMargins: { top: 0.05, bottom: 0 },
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

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(248, 81, 73, 0.4)',
      bottomColor: 'rgba(248, 81, 73, 0.02)',
      lineColor: THEME.line,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    })
    seriesRef.current = areaSeries

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  /* ── Update data ─────────────────────────────────────────────────── */

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return

    const data = series
      .map((p) => ({ time: p.date as string, value: p.drawdown * 100 }))
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))

    seriesRef.current.setData(data)
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

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div>
      {/* Max drawdown label */}
      <div className="mb-1 flex items-center justify-between">
        <span className="text-text-dim text-xs">Underwater Curve</span>
        <span className="font-mono-financial text-negative text-xs">
          Max DD: {(maxDrawdown * 100).toFixed(2)}%
        </span>
      </div>
      <div className="relative" style={{ height }}>
        <div ref={containerRef} style={{ height: '100%' }} />
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-text-dim">
            Loading drawdown data…
          </div>
        )}
        {!isLoading && !series.length && (
          <div className="absolute inset-0 flex items-center justify-center text-text-dim">
            No drawdown data available for the selected period
          </div>
        )}
      </div>
    </div>
  )
}