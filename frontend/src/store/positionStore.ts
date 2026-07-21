/**
 * Position store — manages positions list with live WebSocket price updates.
 *
 * Fetches positions from REST API on mount/portfolio change.
 * Listens for `ws-message` custom events from the WebSocket hook and
 * applies price deltas in-place, recalculating derived fields.
 *
 * Tracks per-symbol flash state (up/down) for ~1 s so tables can animate.
 *
 * Segment 7.3: Added portfolios/baskets lists + movePosition action.
 */

import { create } from 'zustand'
import {
  type Basket,
  type Position,
  type Portfolio,
  basketsApi,
  portfoliosApi,
  positionsApi,
} from '@/services/api'

/* ── Flash tracking ─────────────────────────────────────────────────── */

export interface FlashEntry {
  direction: 'up' | 'down'
  expiresAt: number
}

/* ── Store shape ────────────────────────────────────────────────────── */

interface PositionState {
  positions: Position[]
  isLoading: boolean
  error: string | null
  flashes: Record<string, FlashEntry>

  /** All user portfolios (for move-to-basket dropdown) */
  portfolios: Portfolio[]

  /** All user baskets (for display names in dropdown) */
  baskets: Basket[]

  /* ── Actions ─────────────────────────────────────────────────────── */
  fetchPositions: (portfolioId: string) => Promise<void>
  applyPriceUpdate: (symbol: string, newPrice: number, prevPrice: number | null) => void
  /** Return tickers for all current positions (for WS subscription) */
  getSymbols: () => string[]
  /** Fetch all portfolios + baskets for the move dropdown */
  fetchMoveTargets: () => Promise<void>
  /** Move a position to a different portfolio (i.e. different basket) */
  movePosition: (
    portfolioId: string,
    positionId: string,
    targetPortfolioId: string,
  ) => Promise<void>
}

export const usePositionStore = create<PositionState>((set, get) => ({
  positions: [],
  isLoading: false,
  error: null,
  flashes: {},
  portfolios: [],
  baskets: [],

  fetchPositions: async (portfolioId: string) => {
    set({ isLoading: true, error: null })
    try {
      const data = await positionsApi.list(portfolioId)
      set({ positions: data, isLoading: false })
    } catch (err: unknown) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load positions',
        isLoading: false,
      })
    }
  },

  applyPriceUpdate: (symbol: string, newPrice: number, prevPrice: number | null) => {
    const { positions, flashes } = get()
    const now = Date.now()
    const priceUp = prevPrice == null ? newPrice >= 0 : newPrice > prevPrice

    let matched = false
    const updated = positions.map((pos) => {
      if (pos.symbol !== symbol) return pos
      matched = true

      const qty = parseFloat(pos.quantity)
      const avgCost = parseFloat(pos.avg_cost_basis)
      const marketValue = qty * newPrice
      const unrealizedGain = qty * (newPrice - avgCost)
      const unrealizedGainPct = avgCost > 0 ? (unrealizedGain / (qty * avgCost)) * 100 : 0

      return {
        ...pos,
        current_price: String(newPrice),
        market_value: String(marketValue),
        unrealized_gain: String(unrealizedGain),
        unrealized_gain_pct: String(unrealizedGainPct),
      }
    })

    // Ignore updates for symbols we don't hold — avoids spurious re-renders
    // and polluting the flash map.
    if (!matched) return

    const expiresAt = now + 1000
    set({
      positions: updated,
      flashes: { ...flashes, [symbol]: { direction: priceUp ? 'up' : 'down', expiresAt } },
    })

    // Clear the flash after the animation window so a subsequent update can
    // re-apply the class and re-trigger the CSS animation. Guarded by
    // ``expiresAt`` so a newer flash within the window isn't wiped.
    setTimeout(() => {
      const current = get().flashes[symbol]
      if (current && current.expiresAt === expiresAt) {
        const next = { ...get().flashes }
        delete next[symbol]
        set({ flashes: next })
      }
    }, 1050)
  },

  getSymbols: () => get().positions.map((p) => p.symbol),

  fetchMoveTargets: async () => {
    try {
      const [portfolios, baskets] = await Promise.all([
        portfoliosApi.list(),
        basketsApi.list(),
      ])
      set({ portfolios, baskets })
    } catch {
      // Non-fatal — dropdown just won't populate
    }
  },

  movePosition: async (
    portfolioId: string,
    positionId: string,
    targetPortfolioId: string,
  ) => {
    try {
      await positionsApi.move(portfolioId, positionId, targetPortfolioId)
      // Refresh positions for the source portfolio (moved position disappears)
      await get().fetchPositions(portfolioId)
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to move position' })
    }
  },
}))
