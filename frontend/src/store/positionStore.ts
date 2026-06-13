import { create } from 'zustand';
import { positionService } from '../services/api';
import type { Position } from '../services/api';

interface PositionState {
  positions: Position[];
  loading: boolean;
  error: string | null;
  priceCache: Record<string, number>;
  autoRefreshInterval: number | null;
  fetchPositions: (portfolioId: string) => Promise<void>;
  refreshPrices: (portfolioId: string) => Promise<void>;
  startAutoRefresh: (portfolioId: string, intervalMs?: number) => void;
  stopAutoRefresh: () => void;
  applyLivePrices: (updates: Array<{ symbol: string; price: number; prev: number }>) => void;
}

const priceCache: Record<string, number> = {};
let autoRefreshInterval: number | null = null;

function recomputePositions(
  positions: Position[],
  updates: Array<{ symbol: string; price: number }>
): Position[] {
  const map = new Map(updates.map((u) => [u.symbol, u.price]));
  if (map.size === 0) return positions;

  return positions.map((p) => {
    const newPrice = map.get(p.symbol);
    if (newPrice === undefined) return p;

    const marketValue = p.quantity * newPrice;
    const cost = p.quantity * p.avg_cost_basis;
    const gain = marketValue - cost;
    const gainPct = cost > 0 ? (gain / cost) * 100 : 0;

    return {
      ...p,
      current_price: newPrice,
      market_value: marketValue,
      gain,
      gain_pct: gainPct,
    };
  });
}

export const usePositionStore = create<PositionState>((set, get) => ({
  positions: [],
  loading: false,
  error: null,
  priceCache: priceCache,
  autoRefreshInterval: null,

  fetchPositions: async (portfolioId: string) => {
    set({ loading: true, error: null });
    try {
      const response = await positionService.list(portfolioId);
      set({ positions: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  refreshPrices: async (portfolioId: string) => {
    set({ loading: true, error: null });
    try {
      const response = await positionService.refreshPrices(portfolioId);
      set({ positions: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  startAutoRefresh: (portfolioId: string, intervalMs: number = 30000) => {
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
    }
    
    const refresh = async () => {
      const { refreshPrices } = get();
      await refreshPrices(portfolioId);
    };
    
    autoRefreshInterval = window.setInterval(refresh, intervalMs);
    set({ autoRefreshInterval: autoRefreshInterval });
    
    // Initial fetch
    refresh();
  },

  stopAutoRefresh: () => {
    if (autoRefreshInterval) {
      clearInterval(autoRefreshInterval);
      autoRefreshInterval = null;
    }
    set({ autoRefreshInterval: null });
  },

  /**
   * Apply WebSocket live price updates without a full API refetch.
   * Recomputes market_value, gain, and gain_pct for each affected position.
   */
  applyLivePrices: (updates) => {
    set((state) => ({
      positions: recomputePositions(state.positions, updates),
    }));
  },
}));
