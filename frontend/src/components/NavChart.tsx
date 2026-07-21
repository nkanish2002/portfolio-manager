/**
 * NavChart — NAV growth line chart using TradingView Lightweight Charts.
 *
 * Renders a line chart of the portfolio's Net Asset Value over time with:
 *  - Interactive crosshair + tooltip
 *  - Dark theme matching the app palette
 *  - Empty state when no data is available
 *
 * Backend response: { series: [{ date: string, nav: number }, ...] }
 *
 * Implementation note: the chart container div is always rendered (even during
 * loading / empty states) so the chart-creation effect runs exactly once on
 * mount. States are overlaid on top of the container rather than replacing it,
 * which avoids the bug where the effect has already run but the container
 * mounts later (chart never created).
 */

import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineSeries, type IChartApi, type ISeriesApi } from 'lightweight-charts'

interface NavChartProps {
  series: { date: string; nav: number }[]
  isLoading?: boolean
  height?: number
}

/* ── Theme colours matching the app palette ─────────────────────────── */

const THEME = {
  bg: '#0d1117',
  grid: '#21262d',
  text: '#8b949e',
  line: '#10b981',
  crosshair: '#8b949e',
  tooltipBg: '#161b22',
  tooltipBorder: '#30363d',
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function NavChart({ series, isLoading, height = 300 }: NavChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null)

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

    const lineSeries = chart.addSeries(LineSeries, {
      color: THEME.line,
      lineWidth: 2,
      lastValueVisible: true,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    })
    seriesRef.current = lineSeries

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  /* ── Update data when series changes ─────────────────────────────── */

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return

    const data = series
      .map((p) => ({ time: p.date as string, value: p.nav }))
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
  // The container is always rendered so the chart is created once on mount.
  // Loading / empty states are overlaid on top so they don't unmount the
  // container (which would prevent the chart-creation effect from running).

  return (
    <div className="relative" style={{ height }}>
      <div ref={containerRef} style={{ height: '100%' }} />
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center text-text-dim">
          Loading NAV data…
        </div>
      )}
      {!isLoading && !series.length && (
        <div className="absolute inset-0 flex items-center justify-center text-text-dim">
          No NAV data available for the selected period
        </div>
      )}
    </div>
  )
}