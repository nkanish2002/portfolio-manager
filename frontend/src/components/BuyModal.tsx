/**
 * Buy Modal — symbol search, quantity, price, fees.
 *
 * Opens from the Buy button on the Positions page.
 * Calls ticker search on symbol change, records a BUY transaction on submit.
 */

import { useCallback, useEffect } from 'react'
import type { TickerSearchResult } from '@/services/api'
import { usePortfolioStore } from '@/store/portfolioStore'
import { useTradeStore } from '@/store/tradeStore'

/* ── Shared input style ─────────────────────────────────────────────── */

const INPUT = 'w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent'

/* ── Ticker search dropdown ─────────────────────────────────────────── */

function TickerSearchDropdown({
  results,
  onSelect,
  query,
}: {
  results: TickerSearchResult[]
  onSelect: (result: TickerSearchResult) => void
  query: string
}) {
  if (!query || results.length === 0) return null

  return (
    <ul className="absolute left-0 top-full z-20 mt-1 max-h-48 w-full overflow-auto rounded border border-border bg-surface shadow-lg">
      {results.map((r) => (
        <li
          key={r.symbol}
          className="cursor-pointer px-3 py-2 text-sm text-text hover:bg-border"
          onMouseDown={(e) => {
            e.preventDefault()
            onSelect(r)
          }}
        >
          <span className="font-medium">{r.symbol}</span>
          <span className="ml-2 text-text-dim">
            {r.name} {r.exchange && `(${r.exchange})`}
          </span>
        </li>
      ))}
    </ul>
  )
}

/* ── Modal ──────────────────────────────────────────────────────────── */

export default function BuyModal({ onTradeSuccess }: { onTradeSuccess: () => void }) {
  const { selectedId } = usePortfolioStore()
  const { buyOpen, buyForm, buySearchResults, isLoading, error, closeBuy, setBuyField, selectTicker, submitBuy } =
    useTradeStore()

  // Close on Escape
  useEffect(() => {
    if (!buyOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeBuy()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [buyOpen, closeBuy])

  const handleSelectTicker = useCallback(
    (result: TickerSearchResult) => {
      selectTicker(result)
    },
    [selectTicker],
  )

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!selectedId) return
      void submitBuy(selectedId).then(onTradeSuccess)
    },
    [selectedId, submitBuy, onTradeSuccess],
  )

  if (!buyOpen) return null

  const totalCost = buyForm.qty * buyForm.price + buyForm.fees

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      {/* Backdrop — a real button so it's keyboard-accessible (Escape also closes) */}
      <button
        type="button"
        aria-label="Close dialog"
        className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-sm"
        onClick={closeBuy}
      />
      <div className="relative w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-positive">Buy</h2>
          <button type="button" onClick={closeBuy} className="text-text-dim transition hover:text-text">
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-3 py-2 text-negative text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Symbol with search */}
          <label className="mb-1 block text-xs text-text-dim">
            Symbol
            <div className="relative mt-1">
              <input
                type="text"
                value={buyForm.symbol}
                onChange={(e) => setBuyField('symbol', e.target.value.toUpperCase())}
                placeholder="AAPL"
                className={INPUT}
                maxLength={10}
              />
              <TickerSearchDropdown results={buySearchResults} onSelect={handleSelectTicker} query={buyForm.symbol} />
            </div>
          </label>

          {/* Quantity */}
          <label className="mb-1 block text-xs text-text-dim">
            Quantity
            <input
              type="number"
              min={1}
              step={1}
              value={buyForm.qty}
              onChange={(e) => setBuyField('qty', parseInt(e.target.value, 10) || 0)}
              className={`mt-1 ${INPUT}`}
            />
          </label>

          {/* Price */}
          <label className="mb-1 block text-xs text-text-dim">
            Price ($)
            <input
              type="number"
              min={0.01}
              step={0.01}
              value={buyForm.price || ''}
              onChange={(e) => setBuyField('price', parseFloat(e.target.value) || 0)}
              className={`mt-1 ${INPUT}`}
              placeholder="0.00"
            />
          </label>

          {/* Fees */}
          <label className="mb-1 block text-xs text-text-dim">
            Fees ($)
            <input
              type="number"
              min={0}
              step={0.01}
              value={buyForm.fees || ''}
              onChange={(e) => setBuyField('fees', parseFloat(e.target.value) || 0)}
              className={`mt-1 ${INPUT}`}
              placeholder="0.00"
            />
          </label>

          {/* Total estimate */}
          {buyForm.price > 0 && buyForm.qty > 0 && (
            <div className="rounded border border-border/50 px-3 py-2">
              <div className="flex justify-between text-sm">
                <span className="text-text-dim">Estimated total</span>
                <span className="font-mono-financial font-medium text-text">
                  ${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={closeBuy}
              className="flex-1 rounded border border-border px-4 py-2 text-sm text-text-dim transition hover:border-text hover:text-text"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !buyForm.symbol || buyForm.price <= 0 || buyForm.qty <= 0}
              className="flex-1 rounded bg-positive/20 px-4 py-2 font-medium text-positive text-sm transition hover:bg-positive/30 disabled:opacity-50"
            >
              {isLoading ? 'Buying…' : 'Buy'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
