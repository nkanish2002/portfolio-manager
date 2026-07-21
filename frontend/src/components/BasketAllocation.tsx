/**
 * Basket allocation — reusable progress bar showing target vs actual allocation.
 *
 * Used on BasketsPage and DashboardPage for consistent rendering.
 */

import type { Basket, BasketAnalyticsData } from '@/services/api'

interface BasketAllocationProps {
  basket: Basket
  analytics: BasketAnalyticsData | null
  totalPortfolioNav: number
  onEdit?: () => void
  onDelete?: () => void
  showActions?: boolean
}

/**
 * Render a single basket row: color swatch, name, progress bar (target vs actual).
 */
export function BasketRow({
  basket,
  analytics,
  totalPortfolioNav,
  onEdit,
  onDelete,
  showActions = false,
}: BasketAllocationProps) {
  const target = parseFloat(basket.target_allocation)
  const actualNav = analytics?.nav ?? 0
  const actualPct = totalPortfolioNav > 0 ? (actualNav / totalPortfolioNav) * 100 : 0

  // Deviation from target
  const deviation = actualPct - target
  const isOver = deviation > 1
  const isUnder = deviation < -1

  return (
    <div className="mb-4">
      {/* Header row */}
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full" style={{ backgroundColor: basket.color }} />
          <span className="font-medium text-sm text-text">{basket.name}</span>
          {basket.description && (
            <span className="hidden text-text-dim text-xs sm:inline">{basket.description}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-mono-financial ${isOver ? 'text-negative' : isUnder ? 'text-warning' : 'text-text-dim'}`}>
            {actualPct.toFixed(1)}% / {target.toFixed(0)}%
            {deviation !== 0 && (
              <span className="ml-1">
                ({deviation > 0 ? '+' : ''}{deviation.toFixed(1)}%)
              </span>
            )}
          </span>
          {showActions && (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={onEdit}
                className="rounded px-1.5 py-0.5 text-text-dim text-xs transition hover:border hover:border-accent hover:text-accent"
              >
                Edit
              </button>
              <button
                type="button"
                onClick={onDelete}
                className="rounded px-1.5 py-0.5 text-text-dim text-xs transition hover:border hover:border-negative hover:text-negative"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Progress bar — target as outer track, actual as fill */}
      <div className="relative h-3 overflow-hidden rounded bg-bg">
        {/* Target marker (thin white line at target%) */}
        <div
          className="absolute top-0 z-10 h-full w-px bg-white/30"
          style={{ left: `${Math.min(target, 100)}%` }}
        />
        {/* Actual fill */}
        <div
          className="h-full rounded transition-all duration-500"
          style={{
            width: `${Math.min(actualPct, 100)}%`,
            backgroundColor: basket.color,
            opacity: 0.8,
          }}
        />
      </div>

      {/* Stats row */}
      {analytics && (
        <div className="mt-1 flex items-center gap-4 text-xs text-text-dim">
          <span>${analytics.nav.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
          <span className={analytics.unrealized_gain >= 0 ? 'text-positive' : 'text-negative'}>
            {analytics.unrealized_gain >= 0 ? '+' : ''}
            ${Math.abs(analytics.unrealized_gain).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            ({analytics.unrealized_gain_pct >= 0 ? '+' : ''}
            {analytics.unrealized_gain_pct.toFixed(2)}%)
          </span>
          <span>{analytics.position_count} positions</span>
          <span>{analytics.portfolio_count} portfolio{analytics.portfolio_count !== 1 ? 's' : ''}</span>
        </div>
      )}
    </div>
  )
}

/**
 * Render all baskets as allocation rows.
 */
interface BasketAllocationGroupProps {
  baskets: Basket[]
  analyticsMap: Map<string, BasketAnalyticsData | null>
  totalPortfolioNav: number
  showActions?: boolean
  onEdit?: (basket: Basket) => void
  onDelete?: (basket: Basket) => void
}

export function BasketAllocationGroup({
  baskets,
  analyticsMap,
  totalPortfolioNav,
  showActions = false,
  onEdit,
  onDelete,
}: BasketAllocationGroupProps) {
  return (
    <div>
      {baskets.length === 0 ? (
        <p className="text-sm text-text-dim">No baskets configured.</p>
      ) : (
        baskets.map((basket) => (
          <BasketRow
            key={basket.id}
            basket={basket}
            analytics={analyticsMap.get(basket.id) ?? null}
            totalPortfolioNav={totalPortfolioNav}
            showActions={showActions}
            onEdit={() => onEdit?.(basket)}
            onDelete={() => onDelete?.(basket)}
          />
        ))
      )}
    </div>
  )
}

export default BasketAllocationGroup
