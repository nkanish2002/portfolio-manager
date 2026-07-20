/**
 * Positions page — detailed position table with live WebSocket updates.
 *
 * Uses positionStore for state. Flash animations on price change.
 * Subscribes to position tickers via the WebSocket hook.
 */

import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { usePositionStore, type FlashEntry } from '@/store/positionStore'
import { usePortfolioStore } from '@/store/portfolioStore'
import { useWebSocket } from '@/hooks/useWebSocket'

/** Clean up expired flashes periodically */
function useFlashCleanup(flashes: Record<string, FlashEntry>): Record<string, FlashEntry> {
  const now = Date.now()
  const cleaned: Record<string, FlashEntry> = {}
  for (const [sym, entry] of Object.entries(flashes)) {
    if (entry.expiresAt > now) cleaned[sym] = entry
  }
  return cleaned
}

export default function PositionsPage() {
  const { selectedId } = usePortfolioStore()
  const { positions, isLoading, error, flashes, fetchPositions, applyPriceUpdate, getSymbols } = usePositionStore()
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
  }, [positions.length, subscribe, getSymbols]) // re-subscribe when position count changes

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

  // Derive clean flashes (drop expired)
  const activeFlashes = useFlashCleanup(flashes)

  /* ── Empty / loading states ──────────────────────────────────────── */

  if (!selectedId) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Select a portfolio to view positions</p>
      </div>
    )
  }

  if (isLoading) {
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

  /* ── Position row renderer ───────────────────────────────────────── */

  const renderRow = (pos: typeof positions[0]) => {
    const gain = parseFloat(pos.unrealized_gain)
    const gainPct = parseFloat(pos.unrealized_gain_pct)
    const flash = activeFlashes[pos.asset_id]
    const flashClass = flash
      ? flash.direction === 'up'
        ? 'flash-green'
        : 'flash-red'
      : ''

    return (
      <tr key={pos.id} className={`border-border/50 border-b ${flashClass}`}>
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
  }

  /* ── Render ──────────────────────────────────────────────────────── */

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
            <tbody>{positions.map(renderRow)}</tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
