/**
 * Dashboard page — KPI cards, basket allocation, position summary.
 *
 * Shows empty state when no portfolios/positions exist.
 */

import { useEffect, useState } from 'react'
import { type Position, positionsApi } from '@/services/api'
import { useBasketStore } from '@/store/basketStore'
import { usePortfolioStore } from '@/store/portfolioStore'

/* ── KPI card ───────────────────────────────────────────────────────── */

function KpiCard({ label, value, sub, positive }: { label: string; value: string; sub?: string; positive?: boolean }) {
  return (
    <div className="rounded border border-border bg-surface p-4">
      <p className="text-text-dim text-xs">{label}</p>
      <p
        className={`mt-1 font-mono-financial font-semibold text-xl ${positive ? 'text-positive' : positive === false ? 'text-negative' : 'text-text'}`}
      >
        {value}
      </p>
      {sub && <p className="mt-0.5 text-text-dim text-xs">{sub}</p>}
    </div>
  )
}

/* ── Basket progress bar ────────────────────────────────────────────── */

function BasketRow({ name, color, target, actual }: { name: string; color: string; target: number; actual: number }) {
  const barWidth = Math.min(target, 100)

  return (
    <div className="mb-3">
      <div className="mb-1 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
          <span className="font-medium text-text">{name}</span>
        </div>
        <span className="text-text-dim">
          {actual.toFixed(1)}% / {target.toFixed(0)}%
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded bg-bg">
        <div className="h-full rounded transition-all" style={{ width: `${barWidth}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

/* ── Position table (simplified for dashboard) ──────────────────────── */

function PositionTable({ positions }: { positions: Position[] | null }) {
  if (!positions) return <p className="text-sm text-text-dim">Loading positions…</p>
  if (positions.length === 0) return <p className="text-sm text-text-dim">No positions yet</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-border border-b text-left text-text-dim">
            <th className="pr-4 pb-2">Symbol</th>
            <th className="pr-4 pb-2 text-right">Qty</th>
            <th className="pr-4 pb-2 text-right">Price</th>
            <th className="pr-4 pb-2 text-right">Value</th>
            <th className="pb-2 text-right">P&L</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const gain = parseFloat(pos.unrealized_gain)
            const gainPct = parseFloat(pos.unrealized_gain_pct)
            return (
              <tr key={pos.id} className="border-border/50 border-b">
                <td className="py-2 pr-4 font-medium text-text">{pos.asset_id}</td>
                <td className="py-2 pr-4 text-right font-mono-financial text-text">
                  {parseFloat(pos.quantity).toLocaleString()}
                </td>
                <td className="py-2 pr-4 text-right font-mono-financial text-text">
                  ${parseFloat(pos.current_price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td className="py-2 pr-4 text-right font-mono-financial text-text">
                  ${parseFloat(pos.market_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td className={`py-2 text-right font-mono-financial ${gain >= 0 ? 'text-positive' : 'text-negative'}`}>
                  {gain >= 0 ? '+' : ''}${Math.abs(gain).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  <span className="ml-1 text-xs">
                    ({gainPct >= 0 ? '+' : ''}
                    {gainPct.toFixed(2)}%)
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/* ── Dashboard page ─────────────────────────────────────────────────── */

export default function DashboardPage() {
  const { portfolios, selectedId } = usePortfolioStore()
  const { baskets } = useBasketStore()

  // Fetched on demand (positions require a portfolio)
  const [positions, setPositions] = useState<Position[] | null>(null)
  const [posError, setPosError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedId) {
      setPositions(null)
      setPosError(null)
      return
    }

    let cancelled = false
    setPositions(null)
    setPosError(null)
    positionsApi.list(selectedId).then(
      (data) => {
        if (!cancelled) setPositions(data)
      },
      (err) => {
        if (!cancelled) setPosError(err instanceof Error ? err.message : 'Failed to load')
      },
    )
    return () => {
      cancelled = true
    }
  }, [selectedId])

  /* ── Compute KPIs from positions ──────────────────────────────────── */
  const totalValue = positions?.reduce((sum, p) => sum + parseFloat(p.market_value), 0) ?? 0
  const totalGain = positions?.reduce((sum, p) => sum + parseFloat(p.unrealized_gain), 0) ?? 0
  const totalGainPct = totalValue > 0 ? (totalGain / totalValue) * 100 : 0

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* ── KPI cards ──────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Value"
          value={`$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
        />
        <KpiCard
          label="Total P&L"
          value={`${totalGain >= 0 ? '+' : ''}$${Math.abs(totalGain).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
          sub={`${totalGainPct >= 0 ? '+' : ''}${totalGainPct.toFixed(2)}%`}
          positive={totalGain >= 0}
        />
        <KpiCard
          label="Positions"
          value={String(positions?.length ?? 0)}
          sub={selectedId ? portfolios.find((p) => p.id === selectedId)?.name : 'No portfolio selected'}
        />
        <KpiCard label="Baskets" value={String(baskets.length)} />
      </div>

      {/* ── Basket allocation ──────────────────────────────────────── */}
      <div className="mt-6 rounded border border-border bg-surface p-4">
        <h2 className="mb-3 font-semibold text-sm text-text">Basket Allocation</h2>
        {baskets.length === 0 ? (
          <p className="text-sm text-text-dim">No baskets configured. Create one in Settings.</p>
        ) : (
          baskets.map((basket) => (
            <BasketRow
              key={basket.id}
              name={basket.name}
              color={basket.color}
              target={parseFloat(basket.target_allocation)}
              actual={0} // actual computed from positions in 4.x
            />
          ))
        )}
      </div>

      {/* ── Positions table ────────────────────────────────────────── */}
      <div className="mt-6 rounded border border-border bg-surface p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-sm text-text">Positions</h2>
          {posError && <p className="text-negative text-xs">{posError}</p>}
        </div>
        <PositionTable positions={positions} />
      </div>
    </div>
  )
}
