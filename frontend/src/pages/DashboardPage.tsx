/**
 * Dashboard page — KPI cards, basket allocation, position summary.
 *
 * Uses positionStore for live WebSocket price updates.
 * Shows empty state when no portfolios/positions exist.
 */

import { useEffect, useMemo } from 'react'
import { type Position } from '@/services/api'
import { useBasketStore } from '@/store/basketStore'
import { usePortfolioStore } from '@/store/portfolioStore'
import { usePositionStore } from '@/store/positionStore'
import { useWebSocket } from '@/hooks/useWebSocket'

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

function PositionTable({ positions, flashes }: { positions: Position[]; flashes: Record<string, { direction: 'up' | 'down'; expiresAt: number }> }) {
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
            const flash = flashes[pos.asset_id]
            const flashClass = flash
              ? flash.expiresAt > Date.now()
                ? flash.direction === 'up'
                  ? 'flash-green'
                  : 'flash-red'
                : ''
              : ''

            return (
              <tr key={pos.id} className={`border-border/50 border-b ${flashClass}`}>
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
  const { positions, isLoading, flashes, fetchPositions, applyPriceUpdate, getSymbols } = usePositionStore()
  const { subscribe } = useWebSocket()

  // Fetch positions when portfolio changes
  useEffect(() => {
    if (!selectedId) return
    fetchPositions(selectedId)
  }, [selectedId, fetchPositions])

  // Subscribe to WS tickers when positions load
  useEffect(() => {
    const symbols = getSymbols()
    if (symbols.length > 0) subscribe(symbols)
  }, [positions.length, subscribe, getSymbols])

  // Listen for live price updates from WebSocket
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { type: string; updates?: { symbol: string; price: number; prev: number | null }[] }
      if (detail.type !== 'batch' || !detail.updates) return
      for (const update of detail.updates) {
        applyPriceUpdate(update.symbol, update.price, update.prev)
      }
    }
    window.addEventListener('ws-message', handler)
    return () => window.removeEventListener('ws-message', handler)
  }, [applyPriceUpdate])

  /* ── Compute KPIs from positions ──────────────────────────────────── */
  const kpis = useMemo(() => {
    const totalValue = positions.reduce((sum, p) => sum + parseFloat(p.market_value), 0)
    const totalGain = positions.reduce((sum, p) => sum + parseFloat(p.unrealized_gain), 0)
    const totalGainPct = totalValue > 0 ? (totalGain / totalValue) * 100 : 0
    return { totalValue, totalGain, totalGainPct }
  }, [positions])

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Loading…</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* ── KPI cards ──────────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Value"
          value={`$${kpis.totalValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
        />
        <KpiCard
          label="Total P&L"
          value={`${kpis.totalGain >= 0 ? '+' : ''}$${Math.abs(kpis.totalGain).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
          sub={`${kpis.totalGainPct >= 0 ? '+' : ''}${kpis.totalGainPct.toFixed(2)}%`}
          positive={kpis.totalGain >= 0}
        />
        <KpiCard
          label="Positions"
          value={String(positions.length)}
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
        </div>
        <PositionTable positions={positions} flashes={flashes} />
      </div>
    </div>
  )
}
