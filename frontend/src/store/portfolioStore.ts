/**
 * Portfolio store — manages portfolio list and current selection.
 *
 * Fetches portfolios on init. Persists selected portfolio ID in
 * sessionStorage so it survives page reloads within the same tab.
 */

import { create } from 'zustand'
import { type Portfolio, portfoliosApi } from '@/services/api'

const SELECTED_KEY = 'selected_portfolio_id'

interface PortfolioState {
  portfolios: Portfolio[]
  selectedId: string | null
  isLoading: boolean
  error: string | null

  /* ── Actions ─────────────────────────────────────────────────────── */
  init: () => Promise<void>
  select: (id: string | null) => void
  refresh: () => Promise<void>
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  portfolios: [],
  selectedId: sessionStorage.getItem(SELECTED_KEY),
  isLoading: false,
  error: null,

  init: async () => {
    set({ isLoading: true, error: null })
    try {
      const portfolios = await portfoliosApi.list()
      set({ portfolios, isLoading: false })

      // Auto-select first portfolio if none selected yet
      const { selectedId } = get()
      if (!selectedId && portfolios.length > 0) {
        const first = portfolios[0].id
        set({ selectedId: first })
        sessionStorage.setItem(SELECTED_KEY, first)
      }
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to load portfolios', isLoading: false })
    }
  },

  select: (id) => {
    set({ selectedId: id })
    if (id) {
      sessionStorage.setItem(SELECTED_KEY, id)
    } else {
      sessionStorage.removeItem(SELECTED_KEY)
    }
  },

  refresh: async () => {
    set({ isLoading: true, error: null })
    try {
      const portfolios = await portfoliosApi.list()
      set({ portfolios, isLoading: false })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to refresh', isLoading: false })
    }
  },
}))
