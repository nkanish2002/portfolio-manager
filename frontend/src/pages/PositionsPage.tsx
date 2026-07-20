/**
 * Positions page — detailed position table with empty state.
 *
 * Full version of the position table shown on the dashboard.
 * Buy/Sell modals and live WebSocket updates come in later segments.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { type Position, positionsApi } from '@/services/api'
import { usePortfolioStore } from '@/store/portfolioStore'

export default function PositionsPage() {
  const { selectedId } = usePortfolioStore()
  const [positions, setPositions] = useState<Position[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedId) {
      setPositions(null)
      return
    }

    let cancelled = false
    positionsApi.list(selectedId).then(
      (data) => {
        if (!cancelled) setPositions(data)
      },
      (err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load')
      },
    )
    return () => {
      cancelled = true
    }
  }, [selectedId])

  if (!selectedId) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Select a portfolio to view positions</p>
      </div>
    )
  }

  if (!positions) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Loading positions…</p>
      </div>
    )
  }

  if (positions.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-text-dim">
        <p className="text-lg">No positions yet</p>
        <p className="text-sm">Record a trade or import holdings to get started</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="rounded border border-border bg-surface p-4">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="font-semibold text-lg text-text">Positions</h1>
          <div className="flex gap-2">
            <Link
              to="/dashboard"
              className="rounded border border-border px-3 py-1 text-sm text-text-dim transition hover:border-accent hover:text-accent"
            >
              ← Dashboard
            </Link>
            {/* Buy button — wired in 5.1 */}
            <button
              type="button"
              className="rounded bg-accent px-3 py-1 font-medium text-bg text-sm opacity-50"
              disabled
            >
              Buy (coming soon)
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-3 py-2 text-negative text-sm">
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-border border-b text-left text-text-dim">
                <th className="pr-4 pb-2">Symbol</th>
                <th className="pr-4 pb-2 text-right">Qty</th>
                <th className="pr-4 pb-2 text-right">Avg Cost</th>
                <th className="pr-4 pb-2 text-right">Price</th>
                <th className="pr-4 pb-2 text-right">Market Value</th>
                <th className="pb-2 text-right">Unrealized P&L</th>
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
                      ${parseFloat(pos.avg_cost_basis).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono-financial text-text">
                      ${parseFloat(pos.current_price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 pr-4 text-right font-mono-financial text-text">
                      ${parseFloat(pos.market_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td
                      className={`py-2 text-right font-mono-financial ${gain >= 0 ? 'text-positive' : 'text-negative'}`}
                    >
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
      </div>
    </div>
  )
}
