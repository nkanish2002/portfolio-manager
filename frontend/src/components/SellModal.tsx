/**
 * Sell Modal — quantity, price, FIFO P&L preview.
 *
 * Opens from the Sell button on a position row.
 * Shows expected realized gain/loss via the backend preview endpoint.
 */

import { useCallback, useEffect } from 'react'
import { usePortfolioStore } from '@/store/portfolioStore'
import { useTradeStore } from '@/store/tradeStore'

/* ── Shared input style ─────────────────────────────────────────────── */

const INPUT = 'w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent'

/* ── Modal ──────────────────────────────────────────────────────────── */

export default function SellModal({ onTradeSuccess }: { onTradeSuccess: () => void }) {
  const { selectedId } = usePortfolioStore()
  const {
    sellOpen,
    sellPosition,
    sellForm,
    sellMaxQty,
    sellAvgCostBasis,
    sellRealizedGain,
    isLoading,
    error,
    closeSell,
    setSellField,
    submitSell,
  } = useTradeStore()

  // Close on Escape
  useEffect(() => {
    if (!sellOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeSell()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [sellOpen, closeSell])

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!selectedId) return
      void submitSell(selectedId).then(onTradeSuccess)
    },
    [selectedId, submitSell, onTradeSuccess],
  )

  if (!sellOpen || !sellPosition) return null

  const proceeds = sellForm.qty * sellForm.price - sellForm.fees
  const avgCost = sellAvgCostBasis
  const costBasis = sellForm.qty * avgCost
  // Percentage derived from the FIFO realized gain so it stays consistent
  // with the dollar amount shown (exact for single-lot, weighted-avg for multi-lot).
  const pnlPct = sellRealizedGain !== null && costBasis > 0 ? (sellRealizedGain / costBasis) * 100 : 0

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      {/* Backdrop — a real button so it's keyboard-accessible (Escape also closes) */}
      <button
        type="button"
        aria-label="Close dialog"
        className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-sm"
        onClick={closeSell}
      />
      <div className="relative w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-2xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-negative">Sell</h2>
          <button type="button" onClick={closeSell} className="text-text-dim transition hover:text-text">
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-3 py-2 text-negative text-sm">
            {error}
          </div>
        )}

        {/* Position info */}
        <div className="mb-4 rounded border border-border/50 px-3 py-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium text-text">{sellPosition.symbol}</span>
            <span className="font-mono-financial text-text-dim">{sellMaxQty.toLocaleString()} shares held</span>
          </div>
          <div className="mt-1 flex justify-between text-xs text-text-dim">
            <span>Avg cost: ${avgCost.toFixed(2)}</span>
            <span>Current: ${parseFloat(sellPosition.current_price).toFixed(2)}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Quantity */}
          <label className="mb-1 block text-xs text-text-dim">
            Quantity <span className="text-text/50">(max {sellMaxQty})</span>
            <div className="mt-1 flex gap-2">
              <input
                type="number"
                min={1}
                max={sellMaxQty}
                step={1}
                value={sellForm.qty}
                onChange={(e) => setSellField('qty', parseInt(e.target.value, 10) || 0)}
                className={INPUT}
              />
              <button
                type="button"
                onClick={() => setSellField('qty', sellMaxQty)}
                className="rounded border border-border px-3 py-2 text-xs text-text-dim transition hover:border-accent hover:text-accent"
              >
                All
              </button>
            </div>
          </label>

          {/* Price */}
          <label className="mb-1 block text-xs text-text-dim">
            Price ($)
            <input
              type="number"
              min={0.01}
              step={0.01}
              value={sellForm.price || ''}
              onChange={(e) => setSellField('price', parseFloat(e.target.value) || 0)}
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
              value={sellForm.fees || ''}
              onChange={(e) => setSellField('fees', parseFloat(e.target.value) || 0)}
              className={`mt-1 ${INPUT}`}
              placeholder="0.00"
            />
          </label>

          {/* P&L Preview */}
          {sellForm.qty > 0 && sellForm.price > 0 && (
            <div className="rounded border border-border/50 px-3 py-3">
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-text-dim">Preview</div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-text-dim">Proceeds</span>
                  <span className="font-mono-financial text-text">
                    ${proceeds.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-dim">Cost basis</span>
                  <span className="font-mono-financial text-text-dim">
                    ${costBasis.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                {/* Realized gain from backend preview (or fallback) */}
                {sellRealizedGain !== null && (
                  <div
                    className={`flex justify-between border-t border-border/30 pt-2 font-medium ${
                      sellRealizedGain >= 0 ? 'text-positive' : 'text-negative'
                    }`}
                  >
                    <span>Est. realized P&L</span>
                    <span className="font-mono-financial">
                      {sellRealizedGain >= 0 ? '+' : ''}${Math.abs(sellRealizedGain).toFixed(2)}
                      <span className="ml-1 text-xs">
                        ({pnlPct >= 0 ? '+' : ''}
                        {pnlPct.toFixed(1)}%)
                      </span>
                    </span>
                  </div>
                )}
                <div className="flex justify-between pt-1 text-xs text-text-dim">
                  <span>Remaining shares</span>
                  <span className="font-mono-financial">{(sellMaxQty - sellForm.qty).toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={closeSell}
              className="flex-1 rounded border border-border px-4 py-2 text-sm text-text-dim transition hover:border-text hover:text-text"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || sellForm.qty <= 0 || sellForm.price <= 0 || sellForm.qty > sellMaxQty}
              className="flex-1 rounded bg-negative/20 px-4 py-2 font-medium text-negative text-sm transition hover:bg-negative/30 disabled:opacity-50"
            >
              {isLoading ? 'Selling…' : 'Sell'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
