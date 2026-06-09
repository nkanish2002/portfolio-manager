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
  description?: string;
  currency: string;
  position_count: number;
  total_value: number;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: string;
  portfolio_id: string;
  symbol: string;
  quantity: number;
  avg_cost_basis: number;
  current_price?: number;
  market_value?: number;
  gain?: number;
  gain_pct?: number;
  asset_class?: string;
  sector?: string;
  industry?: string;
  created_at: string;
  updated_at: string;
}

export interface Trade {
  id: string;
  portfolio_id: string;
  symbol: string;
  type: 'BUY' | 'SELL' | 'DIVIDEND' | 'SPLIT' | 'FEE';
  quantity: number;
  price: number;
  fees: number;
  p_and_l: number;
  notes?: string;
  transaction_date: string;
}

export interface TradeSummary {
  total_trades: number;
  total_buys: number;
  total_sells: number;
  realized_gain: number;
  realized_loss: number;
  net_realized_p_and_l: number;
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

export interface SellResponse {
  status: 'sold';
  symbol: string;
  quantity_sold: number;
  price: number;
  fees: number;
  proceeds: number;
  realized_pnl: number;
  remaining_quantity: number;
  avg_cost_basis: number;
}

// Chart data types
export interface NavChartData {
  portfolio: Array<{ time: string; value: number }>;
  benchmark: Array<{ time: string; value: number }> | null;
  benchmark_symbol: string;
}

export interface DrawdownData {
  dates: string[];
  drawdown: number[];
  nav: number[];
}

export interface AllocationData {
  labels: string[];
  values: number[];
  colors: string[];
  total_value: number;
}

export interface MonthlyReturnsData {
  years: number[];
  months: string[];
  values: number[][];
}

export interface ReturnsDistributionData {
  bins: number[];
  counts: number[];
  mean_return: number;
  std_return: number;
}

export interface BenchmarkComparisonData {
  dates: string[];
  portfolio: number[];
  benchmark: number[];
  excess_return: number;
  tracking_error: number;
  information_ratio: number;
  correlation: number;
  benchmark_symbol: string;
}

export interface RiskReportData {
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  var_95: number;
  beta: number;
  alpha: number;
  treynor_ratio: number;
  calmar_ratio: number;
  ulcer_index: number;
  portfolio_returns_count: number;
  benchmark_sharpe?: number;
  benchmark_sortino?: number;
  benchmark_max_drawdown?: number;
  excess_return?: number;
  tracking_error?: number;
  information_ratio?: number;
  correlation?: number;
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
  sell: (portfolioId: string, data: { symbol: string; quantity: number; price: number; fees?: number; notes?: string }) =>
    api.post(`/portfolios/${portfolioId}/positions/sell`, data),
  refreshPrices: (portfolioId: string) => api.post(`/portfolios/${portfolioId}/positions/refresh`),
};

export const tradeService = {
  list: (portfolioId: string, params?: {
    symbol?: string;
    trade_type?: string;
    start_date?: string;
    end_date?: string;
    sort_by?: string;
    sort_order?: string;
  }) => api.get(`/portfolios/${portfolioId}/trades`, { params }),
  summary: (portfolioId: string) => api.get(`/portfolios/${portfolioId}/trades/summary`),
};

export const transactionService = {
  list: (portfolioId: string) => api.get(`/portfolios/${portfolioId}/transactions`),
  create: (portfolioId: string, data: Transaction) =>
    api.post(`/portfolios/${portfolioId}/transactions`, data),
};

// Chart API endpoints
export const chartService = {
  nav: (portfolioId: string, benchmark = 'SPY') =>
    api.get<NavChartData>(`/portfolios/${portfolioId}/charts/nav?benchmark=${benchmark}`),
  navHistory: (portfolioId: string, benchmark = 'SPY') =>
    api.get<NavChartData>(`/portfolios/${portfolioId}/charts/nav-history?benchmark=${benchmark}`),
  drawdown: (portfolioId: string) =>
    api.get<DrawdownData>(`/portfolios/${portfolioId}/charts/drawdown`),
  allocation: (portfolioId: string) =>
    api.get<AllocationData>(`/portfolios/${portfolioId}/charts/allocation`),
  monthlyReturns: (portfolioId: string) =>
    api.get<MonthlyReturnsData>(`/portfolios/${portfolioId}/charts/monthly-returns`),
  returnsDistribution: (portfolioId: string) =>
    api.get<ReturnsDistributionData>(`/portfolios/${portfolioId}/charts/returns-distribution`),
  benchmarkComparison: (portfolioId: string, benchmark = 'SPY') =>
    api.get<BenchmarkComparisonData>(`/portfolios/${portfolioId}/charts/benchmark-comparison?benchmark=${benchmark}`),
  riskReport: (portfolioId: string) =>
    api.get<RiskReportData>(`/portfolios/${portfolioId}/risk-report`),
};

export default api;
