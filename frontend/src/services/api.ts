/**
 * API client — Axios instance with JWT auto-attach + TypeScript interfaces.
 *
 * All model types mirror the backend SQLModel schemas (see models/*.py).
 * Decimal fields are serialised as strings by Pydantic; we keep them as
 * string here so numeric precision is preserved through the full round-trip.
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

/* ── Axios instance ─────────────────────────────────────────────────── */

const api = axios.create({
  baseURL: '',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

/** Attach stored JWT to every outgoing request */
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('jwt_token')
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

/** On 401 → clear token + redirect to login */
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token')
      window.location.hash = '#/login'
    }
    return Promise.reject(error)
  },
)

export default api

/* ── Model interfaces (read / response shapes) ──────────────────────── */

/** fastapi-users base fields + our display_name extension */
export interface User {
  id: string
  email: string
  display_name: string | null
  is_active: boolean
  is_superuser: boolean
  is_verified: boolean
  created_at: string
}

export interface Asset {
  id: string
  symbol: string
  name: string
  asset_class: string
  exchange: string | null
  cusip: string | null
  sector: string | null
  industry: string | null
  region: string | null
  created_at: string
  updated_at: string
}

export interface Account {
  id: string
  user_id: string
  name: string
  institution: string | null
  account_number: string | null
  created_at: string
}

export interface Basket {
  id: string
  user_id: string
  name: string
  description: string | null
  color: string
  target_allocation: string // Decimal → string from Pydantic
  sort_order: number
  is_preset: boolean
  created_at: string
  updated_at: string
}

export interface Portfolio {
  id: string
  user_id: string
  name: string
  account_id: string
  basket_id: string | null
  currency: string
  created_at: string
  updated_at: string
}

export interface Position {
  id: string
  portfolio_id: string
  asset_id: string
  quantity: string
  avg_cost_basis: string
  current_price: string
  market_value: string
  unrealized_gain: string
  unrealized_gain_pct: string
  created_at: string
  updated_at: string
}

export interface Transaction {
  id: string
  portfolio_id: string
  asset_id: string
  type: string
  quantity: string
  price: string
  fees: string
  trade_date: string
  notes: string | null
  realized_gain: string | null
  created_at: string
}

export interface Benchmark {
  id: string
  symbol: string
  name: string
  created_at: string
}

export interface BenchmarkData {
  id: string
  benchmark_id: string
  date: string
  close: string
}

/* ── Create / Update payloads ───────────────────────────────────────── */

export interface CreateUser {
  email: string
  password: string
  name?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface BasketCreate {
  name: string
  description?: string | null
  color?: string
  target_allocation: number
  sort_order?: number
}

export interface BasketUpdate {
  name?: string
  description?: string | null
  color?: string
  target_allocation?: number
  sort_order?: number
}

export interface AccountCreate {
  name: string
  institution?: string | null
  account_number?: string | null
}

export interface AccountUpdate {
  name?: string
  institution?: string | null
  account_number?: string | null
}

export interface PortfolioCreate {
  name: string
  account_id: string
  basket_id?: string | null
  currency?: string
}

export interface PortfolioUpdate {
  name?: string
  basket_id?: string | null
  currency?: string
}

export interface PositionCreate {
  asset_id: string
  quantity: number
  avg_cost_basis: number
  current_price: number
}

export interface PositionUpdate {
  quantity?: number
  avg_cost_basis?: number
  current_price?: number
}

export interface TransactionCreate {
  asset_id: string
  type: string
  quantity: number
  price: number
  fees?: number
  trade_date: string | Date
  notes?: string | null
}

/* ── Common response wrappers ───────────────────────────────────────── */

export interface HealthResponse {
  status: string
}

/* ── Typed API helpers (auth) ───────────────────────────────────────── */

export const authApi = {
  register: (data: CreateUser) => api.post<User>('/auth/jwt/register', data).then((r) => r.data),

  login: (data: LoginCredentials) =>
    api.post<{ access_token: string; token_type: string }>('/auth/jwt/login', data).then((r) => r.data),

  logout: () => api.post('/auth/jwt/logout').then((r) => r.data),

  me: () => api.get<User>('/users/me').then((r) => r.data),

  updateMe: (patch: Partial<User>) => api.patch<User>('/users/me', patch).then((r) => r.data),
}

/* ── Typed API helpers (resources) ──────────────────────────────────── */

export const basketsApi = {
  list: () => api.get<Basket[]>('/api/v1/baskets/').then((r) => r.data),

  create: (data: BasketCreate) => api.post<Basket>('/api/v1/baskets/', data).then((r) => r.data),

  update: (id: string, data: BasketUpdate) => api.put<Basket>(`/api/v1/baskets/${id}`, data).then((r) => r.data),

  remove: (id: string) => api.delete<void>(`/api/v1/baskets/${id}`).then((r) => r.data),

  analytics: (id: string) => api.get<Record<string, unknown>>(`/api/v1/baskets/${id}/analytics`).then((r) => r.data),
}

export const accountsApi = {
  list: () => api.get<Account[]>('/api/v1/accounts/').then((r) => r.data),

  create: (data: AccountCreate) => api.post<Account>('/api/v1/accounts/', data).then((r) => r.data),

  update: (id: string, data: AccountUpdate) => api.put<Account>(`/api/v1/accounts/${id}`, data).then((r) => r.data),

  remove: (id: string) => api.delete<void>(`/api/v1/accounts/${id}`).then((r) => r.data),
}

export const portfoliosApi = {
  list: () => api.get<Portfolio[]>('/api/v1/portfolios/').then((r) => r.data),

  create: (data: PortfolioCreate) => api.post<Portfolio>('/api/v1/portfolios/', data).then((r) => r.data),

  get: (id: string) => api.get<Portfolio>(`/api/v1/portfolios/${id}`).then((r) => r.data),

  update: (id: string, data: PortfolioUpdate) =>
    api.put<Portfolio>(`/api/v1/portfolios/${id}`, data).then((r) => r.data),

  remove: (id: string) => api.delete<void>(`/api/v1/portfolios/${id}`).then((r) => r.data),
}

export const positionsApi = {
  list: (portfolioId: string) => api.get<Position[]>(`/api/v1/portfolios/${portfolioId}/positions`).then((r) => r.data),

  create: (portfolioId: string, data: PositionCreate) =>
    api.post<Position>(`/api/v1/portfolios/${portfolioId}/positions`, data).then((r) => r.data),

  refresh: (portfolioId: string) => api.post(`/api/v1/portfolios/${portfolioId}/positions/refresh`).then((r) => r.data),

  move: (portfolioId: string, positionId: string, basketId: string) =>
    api
      .post(`/api/v1/portfolios/${portfolioId}/positions/${positionId}/move`, { basket_id: basketId })
      .then((r) => r.data),
}

export const transactionsApi = {
  list: (portfolioId: string, params?: { type?: string; asset_id?: string }) =>
    api.get<Transaction[]>(`/api/v1/portfolios/${portfolioId}/transactions`, { params }).then((r) => r.data),

  create: (portfolioId: string, data: TransactionCreate) =>
    api.post<Transaction>(`/api/v1/portfolios/${portfolioId}/transactions`, data).then((r) => r.data),
}

export const analyticsApi = {
  risk: (portfolioId: string) =>
    api.get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/analytics/risk`).then((r) => r.data),

  allocations: (portfolioId: string) =>
    api.get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/analytics/allocations`).then((r) => r.data),

  navChart: (portfolioId: string) =>
    api.get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/charts/nav`).then((r) => r.data),

  drawdownChart: (portfolioId: string) =>
    api.get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/charts/drawdown`).then((r) => r.data),

  allocationChart: (portfolioId: string) =>
    api.get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/charts/allocation`).then((r) => r.data),

  monthlyReturns: (portfolioId: string) =>
    api.get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/charts/monthly-returns`).then((r) => r.data),

  benchmarkComparison: (portfolioId: string) =>
    api
      .get<Record<string, unknown>>(`/api/v1/portfolios/${portfolioId}/charts/benchmark-comparison`)
      .then((r) => r.data),
}

/* ── Health check ───────────────────────────────────────────────────── */

export const healthApi = {
  check: () => api.get<HealthResponse>('/health').then((r) => r.data),
}
