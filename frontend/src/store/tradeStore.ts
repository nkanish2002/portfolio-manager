/**
 * Trade store — buy/sell modal state + trade execution.
 *
 * Manages form state for both modals, calls the backend APIs, and
 * refreshes positions after a successful trade.
 */

import { create } from 'zustand'
import { type Position, type TickerSearchResult, transactionsApi, tickerApi } from '@/services/api'

interface BuyForm {
  symbol: string
  qty: number
  price: number
  fees: number
}

interface SellForm {
  qty: number
  price: number
  fees: number
}

/* ── Store shape ────────────────────────────────────────────────────── */

interface TradeState {
  /* ── Shared ──────────────────────────────────────────────────────── */
  portfolioId: string | null
  isLoading: boolean
  error: string | null

  /* ── Buy modal ───────────────────────────────────────────────────── */
  buyOpen: boolean
  buyForm: BuyForm
  buySearchResults: TickerSearchResult[]

  openBuy: (portfolioId?: string) => void
  closeBuy: () => void
  setBuyField: <K extends keyof BuyForm>(key: K, value: BuyForm[K]) => void
  selectTicker: (result: TickerSearchResult) => void
  searchTicker: (query: string) => Promise<void>
  submitBuy: (portfolioId: string) => Promise<void>

  /* ── Sell modal ──────────────────────────────────────────────────── */
  sellOpen: boolean
  sellPosition: Position | null
  sellForm: SellForm
  sellMaxQty: number
  sellAvgCostBasis: number
  sellRealizedGain: number | null

  openSell: (position: Position) => void
  closeSell: () => void
  setSellField: <K extends keyof SellForm>(key: K, value: SellForm[K]) => void
  updateSellPreview: () => Promise<void>
  submitSell: (portfolioId: string) => Promise<void>
}

const defaultBuyForm: BuyForm = { symbol: '', qty: 1, price: 0, fees: 0 }
const defaultSellForm: SellForm = { qty: 1, price: 0, fees: 0 }

export const useTradeStore = create<TradeState>((set, get) => ({
  portfolioId: null,
  isLoading: false,
  error: null,

  /* ── Buy ─────────────────────────────────────────────────────────── */
  buyOpen: false,
  buyForm: { ...defaultBuyForm },
  buySearchResults: [],

  openBuy: (portfolioId?: string) => {
    if (portfolioId) set({ portfolioId })
    set({ buyOpen: true, error: null })
  },

  closeBuy: () => set({ buyOpen: false, buyForm: { ...defaultBuyForm }, buySearchResults: [], error: null }),

  setBuyField: (key, value) =>
    set((state) => {
      const next = { ...state.buyForm, [key]: value }
      const updates: Record<string, unknown> = { buyForm: next }

      // Auto-search when symbol changes
      if (key === 'symbol' && typeof value === 'string' && value.trim().length > 0) {
        void get().searchTicker(value.trim())
      }
      return updates
    }),

  // Selecting a result from the dropdown: set symbol + clear results so the
  // dropdown closes (avoids re-triggering a search for the selected symbol).
  selectTicker: (result) =>
    set((state) => ({
      buyForm: { ...state.buyForm, symbol: result.symbol },
      buySearchResults: [],
    })),

  searchTicker: async (query: string) => {
    const { portfolioId } = get()
    if (!portfolioId) return
    try {
      const results = await tickerApi.search(portfolioId, query)
      set({ buySearchResults: results })
    } catch {
      // Silently ignore search failures (user may be typing)
    }
  },

  submitBuy: async (portfolioId: string) => {
    const { buyForm } = get()
    if (buyForm.price <= 0 || buyForm.qty <= 0) {
      set({ error: 'Price and quantity must be positive' })
      return
    }
    set({ isLoading: true, error: null })
    try {
      await transactionsApi.create(portfolioId, {
        symbol: buyForm.symbol.trim().toUpperCase(),
        type: 'buy',
        quantity: buyForm.qty,
        price: buyForm.price,
        fees: buyForm.fees,
      })
      get().closeBuy()
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Buy failed' })
    } finally {
      set({ isLoading: false })
    }
  },

  /* ── Sell ────────────────────────────────────────────────────────── */
  sellOpen: false,
  sellPosition: null,
  sellForm: { ...defaultSellForm },
  sellMaxQty: 0,
  sellAvgCostBasis: 0,
  sellRealizedGain: null,

  openSell: (position: Position) => {
    const maxQty = parseFloat(position.quantity)
    const price = parseFloat(position.current_price)
    const avgCost = parseFloat(position.avg_cost_basis)
    set({
      sellOpen: true,
      sellPosition: position,
      sellForm: { qty: 1, price: price, fees: 0 },
      sellMaxQty: maxQty,
      sellAvgCostBasis: avgCost,
      sellRealizedGain: null,
      error: null,
    })
  },

  closeSell: () =>
    set({
      sellOpen: false,
      sellPosition: null,
      sellForm: { ...defaultSellForm },
      sellMaxQty: 0,
      sellAvgCostBasis: 0,
      sellRealizedGain: null,
      error: null,
    }),

  setSellField: (key, value) => {
    set((state) => ({ sellForm: { ...state.sellForm, [key]: value } }))
    // Auto-update preview when qty or price changes
    if (key === 'qty' || key === 'price') {
      void get().updateSellPreview()
    }
  },

  updateSellPreview: async () => {
    const { sellPosition, sellForm, portfolioId } = get()
    if (!sellPosition || !portfolioId) return
    const qty = sellForm.qty
    const price = sellForm.price
    if (qty <= 0 || price <= 0) return

    try {
      const preview = await transactionsApi.sellPreview(portfolioId, {
        asset_id: sellPosition.asset_id,
        quantity: qty,
        price: price,
      })
      set({ sellRealizedGain: parseFloat(preview.realized_gain) })
    } catch {
      // Fallback: simple calc if preview fails
      const avgCost = get().sellAvgCostBasis
      const rg = (price - avgCost) * qty
      set({ sellRealizedGain: rg })
    }
  },

  submitSell: async (portfolioId: string) => {
    const { sellPosition, sellForm } = get()
    if (!sellPosition) return
    const maxQty = get().sellMaxQty
    if (sellForm.qty > maxQty) {
      set({ error: `Cannot sell more than ${maxQty} shares` })
      return
    }
    if (sellForm.qty <= 0 || sellForm.price <= 0) {
      set({ error: 'Price and quantity must be positive' })
      return
    }
    set({ isLoading: true, error: null })
    try {
      await transactionsApi.create(portfolioId, {
        asset_id: sellPosition.asset_id,
        type: 'sell',
        quantity: sellForm.qty,
        price: sellForm.price,
        fees: sellForm.fees,
      })
      get().closeSell()
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : 'Sell failed' })
    } finally {
      set({ isLoading: false })
    }
  },
}))
