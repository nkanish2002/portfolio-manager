/**
 * Basket store — manages basket list and CRUD operations.
 *
 * Fetches baskets on init. Supports create, update, and delete.
 */

import { create } from 'zustand'
import { type Basket, type BasketCreate, type BasketUpdate, basketsApi } from '@/services/api'

interface BasketState {
  baskets: Basket[]
  isLoading: boolean
  error: string | null

  /* ── Actions ─────────────────────────────────────────────────────── */
  init: () => Promise<void>
  create: (data: BasketCreate) => Promise<Basket | undefined>
  update: (id: string, data: BasketUpdate) => Promise<void>
  remove: (id: string) => Promise<void>
  refresh: () => Promise<void>
}

export const useBasketStore = create<BasketState>((set) => ({
  baskets: [],
  isLoading: false,
  error: null,

  init: async () => {
    set({ isLoading: true, error: null })
    try {
      const baskets = await basketsApi.list()
      set({ baskets, isLoading: false })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to load baskets', isLoading: false })
    }
  },

  create: async (data) => {
    set({ error: null })
    try {
      const basket = await basketsApi.create(data)
      set((state) => ({ baskets: [...state.baskets, basket] }))
      return basket
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to create basket' })
    }
  },

  update: async (id, data) => {
    set({ error: null })
    try {
      await basketsApi.update(id, data)
      // Refresh full list to get correct types back from API
      const baskets = await basketsApi.list()
      set({ baskets })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to update basket' })
    }
  },

  remove: async (id) => {
    set({ error: null })
    try {
      await basketsApi.remove(id)
      set((state) => ({ baskets: state.baskets.filter((b) => b.id !== id) }))
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to delete basket' })
    }
  },

  refresh: async () => {
    set({ isLoading: true, error: null })
    try {
      const baskets = await basketsApi.list()
      set({ baskets, isLoading: false })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Failed to refresh', isLoading: false })
    }
  },
}))
