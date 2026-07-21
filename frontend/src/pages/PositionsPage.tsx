/**
 * Positions page — detailed position table with live WebSocket updates.
 *
 * Uses positionStore for state. Flash animations on price change.
 * Subscribes to position tickers via the WebSocket hook.
 *
 * Segment 5.1: Buy/Sell modals with trade execution.
 * Segment 7.3: Move-to-basket dropdown + rebalancing suggestions.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useWebSocket } from '@/hooks/useWebSocket'
import { basketsApi, type Basket, type Portfolio, type Position } from '@/services/api'
import { usePortfolioStore } from '@/store/portfolioStore'
import { type FlashEntry, usePositionStore } from '@/store/positionStore'
import { useTradeStore } from '@/store/tradeStore'
import BuyModal from '@/components/BuyModal'
import SellModal from '@/components/SellModal'

/* ── Helpers ────────────────────────────────────────────────────────── */

/** Drop flash entries that have passed their animation window. */
function activeFlashes(flashes: Record<string, FlashEntry>): Record<string, FlashEntry> {
  const now = Date.now()
  const cleaned: Record<string, FlashEntry> = {}
  for (const [sym, entry] of Object.entries(flashes)) {
    if (entry.expiresAt > now) cleaned[sym] = entry
  }
  return cleaned
}

/** Resolve the basket name for a portfolio (given basket list). */
function portfolioBasketName(
  portfolio: Portfolio,
  baskets: Basket[],
): string | null {
  if (!portfolio.basket_id) return null
  const basket = baskets.find((b) => b.id === portfolio.basket_id)
  return basket?.name ?? null
}

/** Resolve the basket color for a portfolio. */
function portfolioBasketColor(
  portfolio: Portfolio,
  baskets: Basket[],
): string | null {
  if (!portfolio.basket_id) return null
  const basket = baskets.find((b) => b.id === portfolio.basket_id)
  return basket?.color ?? null
}

/* ── Rebalancing suggestions panel ──────────────────────────────────── */

interface BasketDeviation {
  basket: Basket
  targetPct: number
  actualPct: number
  deviation: number
  nav: number
}

function RebalancingPanel({
  baskets,
  positionsCount,
  portfolios,
  selectedPortfolioId,
}: {
  baskets: Basket[]
  /** Position count — used as a refetch trigger (changes on moves/trades, not price ticks) */
  positionsCount: number
  portfolios: Portfolio[]
  selectedPortfolioId: string | null
}) {
  // Compute basket deviations from analytics
  const [deviations, setDeviations] = useState<BasketDeviation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!baskets.length) return
    let cancelled = false
    setLoading(true)
    Promise.all(
      baskets.map(async (basket) => {
        try {
          const data = await basketsApi.analytics(basket.id)
          return {
            basket,
            targetPct: parseFloat(basket.target_allocation),
            actualPct: 0,
            deviation: 0,
            nav: data.nav,
          } as BasketDeviation
        } catch {
          return {
            basket,
            targetPct: parseFloat(basket.target_allocation),
            actualPct: 0,
            deviation: -parseFloat(basket.target_allocation),
            nav: 0,
          } as BasketDeviation
        }
      }),
    ).then((results) => {
      if (cancelled) return
      // Compute actual percentages from the real total across all baskets
      const realTotal = results.reduce((sum, r) => sum + r.nav, 0)
      results.forEach((r) => {
        r.actualPct = realTotal > 0 ? (r.nav / realTotal) * 100 : 0
        r.deviation = r.actualPct - r.targetPct
      })
      setDeviations(results)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [baskets, positionsCount])

  // Find over and under-allocated baskets (threshold: ±2%)
  const overAllocated = useMemo(
    () => deviations.filter((d) => d.deviation > 2),
    [deviations],
  )
  const underAllocated = useMemo(
    () => deviations.filter((d) => d.deviation < -2),
    [deviations],
  )

  if (loading || deviations.length === 0) return null
  if (overAllocated.length === 0 && underAllocated.length === 0) return null

  return (
    <div className="mb-6 rounded border border-warning/30 bg-warning/5 p-4">
      <h3 className="mb-3 flex items-center gap-2 font-semibold text-sm text-warning">
        <span>⚖</span> Rebalancing Suggestions
      </h3>
      <div className="space-y-2">
        {overAllocated.map((d) => {
          const basketPortfolios = portfolios.filter(
            (p) => p.basket_id === d.basket.id && p.id !== selectedPortfolioId,
          )
          const canMove = underAllocated.length > 0 && basketPortfolios.length > 0

          return (
            <div key={d.basket.id} className="flex items-start gap-3 rounded border border-border/50 bg-surface/50 p-3 text-sm">
              <span className="mt-0.5 h-2.5 w-2.5 rounded-full" style={{ backgroundColor: d.basket.color }} />
              <div className="flex-1">
                <p className="text-text">
                  <strong>{d.basket.name}</strong> is over-allocated by{' '}
                  <span className="font-mono-financial text-negative">+{d.deviation.toFixed(1)}%</span>
                  {' '}({d.actualPct.toFixed(1)}% vs {d.targetPct.toFixed(0)}% target)
                </p>
                {canMove && (
                  <p className="mt-1 text-text-dim text-xs">
                    Consider moving positions from this basket to{' '}
                    {underAllocated.map((u, i) => (
                      <span key={u.basket.id} className="font-medium text-accent">
                        {i > 0 ? (i === underAllocated.length - 1 ? ' or ' : ', ') : ''}
                        {u.basket.name}
                      </span>
                    ))}{' '}
                    using the "Move" dropdown on each position row.
                  </p>
                )}
                {!canMove && underAllocated.length === 0 && (
                  <p className="mt-1 text-text-dim text-xs">
                    No under-allocated baskets to move positions into. Consider lowering this basket's target or selling positions.
                  </p>
                )}
              </div>
            </div>
          )
        })}
        {underAllocated.map((d) => (
          <div key={d.basket.id} className="flex items-start gap-3 rounded border border-border/50 bg-surface/50 p-3 text-sm">
            <span className="mt-0.5 h-2.5 w-2.5 rounded-full" style={{ backgroundColor: d.basket.color }} />
            <div className="flex-1">
              <p className="text-text">
                <strong>{d.basket.name}</strong> is under-allocated by{' '}
                <span className="font-mono-financial text-warning">{d.deviation.toFixed(1)}%</span>
                {' '}({d.actualPct.toFixed(1)}% vs {d.targetPct.toFixed(0)}% target)
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Move-to-basket dropdown ────────────────────────────────────────── */

function MoveDropdown({
  position,
  currentPortfolioId,
  portfolios,
  baskets,
  onMove,
}: {
  position: Position
  currentPortfolioId: string
  portfolios: Portfolio[]
  baskets: Basket[]
  onMove: (positionId: string, targetPortfolioId: string) => void
}) {
  const [open, setOpen] = useState(false)

  // Target portfolios: same user, different portfolio, same account
  // (we don't restrict by account — any portfolio is a valid target)
  const targetPortfolios = useMemo(
    () =>
      portfolios
        .filter((p) => p.id !== currentPortfolioId)
        .sort((a, b) => a.name.localeCompare(b.name)),
    [portfolios, currentPortfolioId],
  )

  if (targetPortfolios.length === 0) return null

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="rounded border border-border/50 px-2 py-0.5 text-xs text-text-dim transition hover:border-accent hover:text-accent"
      >
        Move ▾
      </button>
      {open && (
        <>
          {/* Backdrop to close dropdown */}
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-40 mt-1 min-w-[180px] rounded border border-border bg-surface shadow-lg">
            {targetPortfolios.map((p) => {
              const basketName = portfolioBasketName(p, baskets)
              const basketColor = portfolioBasketColor(p, baskets)
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => {
                    onMove(position.id, p.id)
                    setOpen(false)
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text transition hover:bg-border/50"
                >
                  {basketColor && (
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: basketColor }} />
                  )}
                  <span className="flex-1">
                    <span className="font-medium">{p.name}</span>
                    {basketName && (
                      <span className="ml-1.5 text-text-dim text-xs">→ {basketName}</span>
                    )}
                  </span>
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

/* ── Positions page ─────────────────────────────────────────────────── */

export default function PositionsPage() {
  const { selectedId } = usePortfolioStore()
  const {
    positions,
    isLoading,
    error,
    flashes,
    portfolios,
    baskets,
    fetchPositions,
    applyPriceUpdate,
    getSymbols,
    fetchMoveTargets,
    movePosition,
  } = usePositionStore()
  const { subscribe, unsubscribe } = useWebSocket()
  const { openBuy, openSell } = useTradeStore()

  // Refresh positions after a trade completes
  const handleTradeSuccess = useCallback(() => {
    if (selectedId) fetchPositions(selectedId)
  }, [selectedId, fetchPositions])

  // Fetch positions when portfolio changes
  useEffect(() => {
    if (!selectedId) return
    fetchPositions(selectedId)
  }, [selectedId, fetchPositions])

  // Fetch portfolios + baskets for the move dropdown
  useEffect(() => {
    fetchMoveTargets()
  }, [fetchMoveTargets])

  // (Re)subscribe to the current holdings' tickers
  const symbolsKey = getSymbols().join(',')
  useEffect(() => {
    const symbols = symbolsKey ? symbolsKey.split(',') : []
    if (symbols.length > 0) subscribe(symbols)
    return () => {
      if (symbols.length > 0) unsubscribe(symbols)
    }
  }, [symbolsKey, subscribe, unsubscribe])

  // Listen for live price updates from WebSocket
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        type: string
        updates?: { symbol: string; price: number; prev: number | null }[]
      }
      if (detail.type !== 'batch' || !detail.updates) return
      for (const update of detail.updates) {
        applyPriceUpdate(update.symbol, update.price, update.prev)
      }
    }
    window.addEventListener('ws-message', handler)
    return () => window.removeEventListener('ws-message', handler)
  }, [applyPriceUpdate])

  // Derive clean flashes (drop expired)
  const activeFlashMap = activeFlashes(flashes)

  // Count of positions — used as a refetch trigger for the rebalancing panel
  // (changes on moves/trades, not on every WebSocket price tick)

  // Handle move
  const handleMove = useCallback(
    (positionId: string, targetPortfolioId: string) => {
      if (!selectedId) return
      movePosition(selectedId, positionId, targetPortfolioId)
    },
    [selectedId, movePosition],
  )

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
        <button
          type="button"
          onClick={() => openBuy(selectedId)}
          className="rounded bg-accent px-4 py-2 font-medium text-bg text-sm transition hover:bg-accent/80"
        >
          + Buy your first position
        </button>
        {/* Modals */}
        <BuyModal onTradeSuccess={handleTradeSuccess} />
        <SellModal onTradeSuccess={handleTradeSuccess} />
      </div>
    )
  }

  /* ── Position row renderer ───────────────────────────────────────── */

  const renderRow = (pos: Position) => {
    const gain = parseFloat(pos.unrealized_gain)
    const gainPct = parseFloat(pos.unrealized_gain_pct)
    const flash = activeFlashMap[pos.symbol]
    const flashClass = flash ? (flash.direction === 'up' ? 'flash-green' : 'flash-red') : ''

    return (
      <tr key={pos.id} className={`border-border/50 border-b ${flashClass}`}>
        <td className="py-2 pr-4 font-medium text-text">{pos.symbol}</td>
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
        <td className={`py-2 pr-4 text-right font-mono-financial ${gain >= 0 ? 'text-positive' : 'text-negative'}`}>
          {gain >= 0 ? '+' : ''}${Math.abs(gain).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          <span className="ml-1 text-xs">
            ({gainPct >= 0 ? '+' : ''}
            {gainPct.toFixed(2)}%)
          </span>
        </td>
        <td className="py-2">
          <div className="flex items-center justify-end gap-1.5">
            <MoveDropdown
              position={pos}
              currentPortfolioId={selectedId!}
              portfolios={portfolios}
              baskets={baskets}
              onMove={handleMove}
            />
            <button
              type="button"
              onClick={() => openSell(pos)}
              className="rounded border border-negative/30 px-2 py-0.5 text-xs text-negative transition hover:border-negative hover:bg-negative/10"
            >
              Sell
            </button>
          </div>
        </td>
      </tr>
    )
  }

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* ── Rebalancing suggestions ──────────────────────────────── */}
      <RebalancingPanel
        baskets={baskets}
        positionsCount={positions.length}
        portfolios={portfolios}
        selectedPortfolioId={selectedId}
      />

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
            <button
              type="button"
              onClick={() => openBuy(selectedId)}
              className="rounded bg-accent px-3 py-1 font-medium text-bg text-sm transition hover:bg-accent/80"
            >
              + Buy
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
                <th className="pr-4 pb-2 text-right">Unrealized P&L</th>
                <th className="pb-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>{positions.map(renderRow)}</tbody>
          </table>
        </div>
      </div>

      {/* Trade modals */}
      <BuyModal onTradeSuccess={handleTradeSuccess} />
      <SellModal onTradeSuccess={handleTradeSuccess} />
    </div>
  )
}
