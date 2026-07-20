/**
 * Position store — manages positions list with live WebSocket price updates.
 *
 * Fetches positions from REST API on mount/portfolio change.
 * Listens for `ws-message` custom events from the WebSocket hook and
 * applies price deltas in-place, recalculating derived fields.
 *
 * Tracks per-symbol flash state (up/down) for ~1 s so tables can animate.
 */

import { create } from 'zustand'
import { type Position, positionsApi } from '@/services/api'

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

  /* ── Actions ─────────────────────────────────────────────────────── */
  fetchPositions: (portfolioId: string) => Promise<void>
  applyPriceUpdate: (symbol: string, newPrice: number, prevPrice: number | null) => void
  /** Return tickers for all current positions (for WS subscription) */
  getSymbols: () => string[]
}

export const usePositionStore = create<PositionState>((set, get) => ({
  positions: [],
  isLoading: false,
  error: null,
  flashes: {},

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
    const priceUp = prevPrice == null || newPrice > prevPrice

    const updated = positions.map((pos) => {
      if (pos.asset_id !== symbol) return pos

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

    // Skip if nothing matched
    if (updated === positions) return

    set({
      positions: updated,
      flashes: { ...flashes, [symbol]: { direction: priceUp ? 'up' : 'down', expiresAt: now + 1000 } },
    })
  },

  getSymbols: () => get().positions.map((p) => p.asset_id),
}))
