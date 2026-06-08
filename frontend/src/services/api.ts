import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Portfolio {
  id: string;
  name: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: string;
  portfolio_id: string;
  symbol: string;
  quantity: number;
  avg_cost_basis: number;
  market_price?: number;
  asset_class?: string;
  sector?: string;
  industry?: string;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  portfolio_id: string;
  position_id?: string;
  type: string;
  symbol: string;
  quantity: number;
  price: number;
  fees?: number;
  notes?: string;
  created_at: string;
}

export const portfolioService = {
  list: () => api.get('/portfolios/'),
  getById: (id: string) => api.get(`/portfolios/${id}`),
  create: (data: { name: string; currency?: string }) => api.post('/portfolios/', data),
  delete: (id: string) => api.delete(`/portfolios/${id}`),
};

export const positionService = {
  list: (portfolioId: string) => api.get(`/portfolios/${portfolioId}/positions`),
  create: (portfolioId: string, data: { symbol: string; quantity: number; price: number }) =>
    api.post(`/portfolios/${portfolioId}/positions`, data),
  refreshPrices: (portfolioId: string) => api.post(`/portfolios/${portfolioId}/positions/refresh`),
};

export const transactionService = {
  list: (portfolioId: string) => api.get(`/portfolios/${portfolioId}/transactions`),
  create: (portfolioId: string, data: Transaction) =>
    api.post(`/portfolios/${portfolioId}/transactions`, data),
};

export default api;
