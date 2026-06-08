import { create } from 'zustand';
import { positionService } from '../services/api';
import type { Position } from '../services/api';

interface PositionState {
  positions: Position[];
  loading: boolean;
  error: string | null;
  fetchPositions: (portfolioId: string) => Promise<void>;
  refreshPrices: (portfolioId: string) => Promise<void>;
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
      // Fetch updated positions after refresh
      const response = await positionService.list(portfolioId);
      set({ positions: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },
}));
