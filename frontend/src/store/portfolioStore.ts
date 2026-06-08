import { create } from 'zustand';
import { portfolioService } from '../services/api';
import type { Portfolio } from '../services/api';

interface PortfolioState {
  portfolios: Portfolio[];
  currentPortfolio: Portfolio | null;
  loading: boolean;
  error: string | null;
  fetchPortfolios: () => Promise<void>;
  setCurrentPortfolio: (id: string) => Promise<void>;
  clearCurrentPortfolio: () => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  portfolios: [],
  currentPortfolio: null,
  loading: false,
  error: null,

  fetchPortfolios: async () => {
    set({ loading: true, error: null });
    try {
      const response = await portfolioService.list();
      set({ portfolios: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  setCurrentPortfolio: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const response = await portfolioService.getById(id);
      set({ currentPortfolio: response.data, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  clearCurrentPortfolio: () => {
    set({ currentPortfolio: null });
  },
}));
