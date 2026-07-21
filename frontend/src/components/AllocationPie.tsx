/**
 * AllocationPie — Donut chart showing portfolio allocation breakdown.
 *
 * Uses Recharts for a responsive donut with a centre label.
 * Supports grouping by sector, region, asset class, or basket.
 *
 * Backend response (via allocationChart API):
 *   { group_by: string, slices: [{ key: string, value: number, pct: number }, ...] }
 */

import { useMemo, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface AllocationSlice {
  key: string
  value: number
  pct: number
}

interface AllocationPieProps {
  slices: AllocationSlice[]
  groupBy: string
  onChangeGroupBy: (group: string) => void
  height?: number
}

/* ── Palette for donut segments ─────────────────────────────────────── */

const COLORS = ['#10b981', '#58a6ff', '#bc8cff', '#f0883e', '#f778ba', '#3fb950', '#d29922', '#79c0ff']

const GROUP_OPTIONS = [
  { label: 'Sector', value: 'sector' },
  { label: 'Region', value: 'region' },
  { label: 'Asset Class', value: 'asset_class' },
]

/* ── Custom tooltip ─────────────────────────────────────────────────── */

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ name: string; value: number; payload?: AllocationSlice }>
}) {
  if (!active || !payload?.length) return null
  const entry = payload[0]
  const name = entry.name as string
  const value = entry.value as number
  const pct = entry.payload?.pct ?? 0

  return (
    <div className="rounded border border-border bg-surface px-3 py-2 text-xs">
      <p className="font-medium text-text">{name}</p>
      <p className="font-mono-financial text-text">
        ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </p>
      <p className="font-mono-financial text-text-dim">{(pct * 100).toFixed(1)}%</p>
    </div>
  )
}

/* ── Group-by selector (extracted to avoid duplication) ─────────────── */

function GroupBySelector({
  groupBy,
  onChangeGroupBy,
}: {
  groupBy: string
  onChangeGroupBy: (group: string) => void
}) {
  return (
    <div className="mb-2 flex gap-1">
      {GROUP_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChangeGroupBy(opt.value)}
          className={`rounded border px-2.5 py-1 text-xs transition ${
            groupBy === opt.value
              ? 'border-accent bg-accent/10 text-accent'
              : 'border-border text-text-dim hover:border-accent hover:text-accent'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function AllocationPie({ slices, groupBy, onChangeGroupBy, height = 300 }: AllocationPieProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const data = useMemo(
    () =>
      // Copy before sorting - Array.prototype.sort mutates in place, and
      // `slices` is React state from the parent (mutating it is a bug).
      [...slices]
        .sort((a, b) => b.value - a.value)
        .map((s, i) => ({ ...s, color: COLORS[i % COLORS.length], name: s.key, value: s.value })),
    [slices],
  )

  const totalValue = data.reduce((sum, d) => sum + d.value, 0)

  /* ── Empty state ─────────────────────────────────────────────────── */

  if (!data.length) {
    return (
      <div className="flex flex-col items-center">
        <GroupBySelector groupBy={groupBy} onChangeGroupBy={onChangeGroupBy} />
        <div className="flex items-center justify-center text-text-dim" style={{ height: height - 40 }}>
          No allocation data (no positions in portfolio)
        </div>
      </div>
    )
  }

  /* ── Donut ───────────────────────────────────────────────────────── */
  // The wrapper is `relative` so the centre label overlay positions over the
  // donut hole rather than the nearest positioned ancestor. ResponsiveContainer
  // makes the chart fill the available width instead of a hardcoded 400px.

  return (
    <div className="flex flex-col items-center">
      <GroupBySelector groupBy={groupBy} onChangeGroupBy={onChangeGroupBy} />

      <div className="relative" style={{ height: height - 40, width: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={110}
              paddingAngle={2}
              dataKey="value"
              onMouseEnter={(_, index) => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              strokeWidth={0}
            >
              {data.map((entry, index) => (
                <Cell
                  key={entry.key}
                  fill={entry.color}
                  opacity={hoveredIndex != null && hoveredIndex !== index ? 0.4 : 1}
                  style={{ transition: 'opacity 0.15s' }}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              formatter={(value: string) => <span className="ml-1 text-xs text-text">{value}</span>}
              wrapperStyle={{ fontSize: '12px', color: '#8b949e' }}
            />
          </PieChart>
        </ResponsiveContainer>

        {/* Centre label overlay — positioned over the donut hole */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-text-dim text-xs">Total Value</p>
            <p className="font-mono-financial font-semibold text-text">
              ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}