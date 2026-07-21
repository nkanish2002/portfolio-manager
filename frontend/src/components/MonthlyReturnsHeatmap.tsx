/**
 * MonthlyReturnsHeatmap — green/red grid of monthly returns by year/month.
 *
 * Backend response (via monthlyReturns API):
 *   { series: [{ month: "YYYY-MM", return: number }, ...] }
 *
 * The flat series is pivoted into a year×month grid (rows = years,
 * columns = Jan..Dec). Cells are colour-coded by return magnitude:
 *   - positive → green (intensity scales with magnitude)
 *   - negative → red (intensity scales with magnitude)
 *   - zero / missing → neutral
 */

import { useMemo } from 'react'

interface MonthlyReturnsHeatmapProps {
  series: { month: string; return: number }[]
  isLoading?: boolean
}

/* ── Constants ──────────────────────────────────────────────────────── */

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/* ── Helpers ────────────────────────────────────────────────────────── */

interface YearRow {
  year: number
  /** 12 entries; null = no data for that month */
  months: (number | null)[]
  /** Calendar-year return (product of available monthly returns) */
  yearReturn: number | null
}

/** Pivot the flat `[{month, return}]` series into rows per year. */
function pivotToGrid(series: { month: string; return: number }[]): YearRow[] {
  const byYear = new Map<number, (number | null)[]>()

  for (const point of series) {
    const [yearStr, monthStr] = point.month.split('-')
    const year = Number.parseInt(yearStr, 10)
    const month = Number.parseInt(monthStr, 10) // 1-12
    if (!byYear.has(year)) {
      byYear.set(year, Array.from({ length: 12 }, () => null))
    }
    byYear.get(year)![month - 1] = point.return
  }

  // Compute calendar-year return = product(1 + r) - 1 over available months
  const rows: YearRow[] = []
  for (const [year, months] of byYear) {
    const available = months.filter((m): m is number => m != null)
    let yearReturn: number | null = null
    if (available.length > 0) {
      yearReturn = available.reduce((acc, r) => acc * (1 + r), 1) - 1
    }
    rows.push({ year, months, yearReturn })
  }

  return rows.sort((a, b) => a.year - b.year)
}

/** Map a return value to a background colour (green/red intensity). */
function returnToColor(value: number | null): string {
  if (value == null) return 'transparent'

  // Clamp intensity at ±10% so extreme months don't blow out the palette.
  const clamped = Math.max(-0.1, Math.min(0.1, value))
  const intensity = Math.min(1, Math.abs(clamped) / 0.1)

  if (value > 0) {
    // green: rgba(63, 185, 80, intensity)
    return `rgba(63, 185, 80, ${0.15 + intensity * 0.7})`
  }
  if (value < 0) {
    // red: rgba(248, 81, 73, intensity)
    return `rgba(248, 81, 73, ${0.15 + intensity * 0.7})`
  }
  return 'transparent'
}

/** Foreground colour for a cell (dark text on light backgrounds). */
function returnToTextColor(value: number | null): string {
  if (value == null) return 'var(--color-text-dim)'
  return Math.abs(value) >= 0.05 ? '#0d1117' : 'var(--color-text)'
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function MonthlyReturnsHeatmap({ series, isLoading }: MonthlyReturnsHeatmapProps) {
  const rows = useMemo(() => pivotToGrid(series), [series])

  if (isLoading) {
    return (
      <div className="flex h-[200px] items-center justify-center text-text-dim">
        Loading monthly returns…
      </div>
    )
  }

  if (!series.length) {
    return (
      <div className="flex h-[200px] items-center justify-center text-text-dim">
        No monthly returns available for the selected period
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="text-text-dim">
            <th className="px-2 py-1 text-left text-xs">Year</th>
            {MONTH_LABELS.map((m) => (
              <th key={m} className="px-1 py-1 text-center text-xs font-medium">
                {m}
              </th>
            ))}
            <th className="px-2 py-1 text-right text-xs font-medium">YTD</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year} className="border-border/50 border-t">
              <td className="px-2 py-1 font-mono-financial text-text text-xs">{row.year}</td>
              {row.months.map((value, idx) => {
                const bg = returnToColor(value)
                const monthKey = MONTH_LABELS[idx] + row.year
                return (
                  <td
                    key={monthKey}
                    className="px-1 py-1 text-center font-mono-financial text-xs"
                    style={{
                      backgroundColor: bg,
                      color: returnToTextColor(value),
                      borderRadius: '2px',
                    }}
                    title={
                      value != null
                        ? `${MONTH_LABELS[idx]} ${row.year}: ${(value * 100).toFixed(2)}%`
                        : `${MONTH_LABELS[idx]} ${row.year}: no data`
                    }
                  >
                    {value != null ? `${(value * 100).toFixed(1)}` : '—'}
                  </td>
                )
              })}
              <td
                className={`px-2 py-1 text-right font-mono-financial text-xs ${
                  row.yearReturn == null
                    ? 'text-text-dim'
                    : row.yearReturn >= 0
                      ? 'text-positive'
                      : 'text-negative'
                }`}
              >
                {row.yearReturn != null ? `${(row.yearReturn * 100).toFixed(1)}%` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}