import { create } from 'zustand';
import { positionService } from '../services/api';
import type { Position } from '../services/api';

interface PositionState {
  positions: Position[];
  loading: boolean;
  error: string | null;
  fetchPositions: (portfolioId: string) => Promise<void>;
  refreshPrices: (portfolioId: string) => Promise<void>;
  applyLivePrices: (updates: Array<{ symbol: string; price: number; prev: number }>) => void;
}

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

export const usePositionStore = create<PositionState>((set) => ({
  positions: [],
  loading: false,
  error: null,

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
      await positionService.refreshPrices(portfolioId);
      const response = await positionService.list(portfolioId);
      set({ positions: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
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
