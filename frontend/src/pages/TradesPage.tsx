/**
 * Trades page — transaction history with filters, pagination, CSV export.
 *
 * Segment 5.2: Trade audit page.
 * Shows all transactions for the selected portfolio with:
 *  - Filters: date range, type (BUY/SELL), symbol
 *  - Paginated table (25 per page)
 *  - CSV export for trades and positions
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type Position, type Transaction, positionsApi, transactionsApi } from '@/services/api'
import { usePortfolioStore } from '@/store/portfolioStore'

/* ── Types ──────────────────────────────────────────────────────────── */

interface Filters {
  type: string
  symbol: string
  dateFrom: string
  dateTo: string
}

const DEFAULT_FILTERS: Filters = { type: '', symbol: '', dateFrom: '', dateTo: '' }
const PAGE_SIZE = 25

/* ── CSV helpers ────────────────────────────────────────────────────── */

function downloadCSV(filename: string, header: string[], rows: string[][]) {
  const csvContent = [header, ...rows]
    .map((row) => row.map((cell: string) => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function exportTradesCSV(trades: Transaction[]) {
  const header = ['Date', 'Type', 'Symbol', 'Qty', 'Price', 'Fees', 'Realized P&L', 'Notes']
  const rows = trades.map((t) => [
    new Date(t.trade_date).toLocaleDateString(),
    t.type.toUpperCase(),
    t.symbol ?? '',
    parseFloat(t.quantity).toLocaleString(),
    parseFloat(t.price).toFixed(2),
    parseFloat(t.fees).toFixed(2),
    t.realized_gain != null ? parseFloat(t.realized_gain).toFixed(2) : '',
    t.notes ?? '',
  ])
  downloadCSV('trades.csv', header, rows)
}

function exportPositionsCSV(positions: Position[]) {
  const header = ['Symbol', 'Qty', 'Avg Cost', 'Price', 'Market Value', 'Unrealized P&L', 'P&L %']
  const rows = positions.map((p) => [
    p.symbol,
    parseFloat(p.quantity).toLocaleString(),
    parseFloat(p.avg_cost_basis).toFixed(2),
    parseFloat(p.current_price).toFixed(2),
    parseFloat(p.market_value).toFixed(2),
    parseFloat(p.unrealized_gain).toFixed(2),
    `${parseFloat(p.unrealized_gain_pct).toFixed(2)}%`,
  ])
  downloadCSV('positions.csv', header, rows)
}

/* ── Page ───────────────────────────────────────────────────────────── */

export default function TradesPage() {
  const { selectedId } = usePortfolioStore()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>({ ...DEFAULT_FILTERS })
  const [page, setPage] = useState(1)

  // Unique symbols from current transactions (for filter dropdown)
  const symbols = useMemo(() => {
    const s = new Set(transactions.map((t) => t.symbol).filter(Boolean) as string[])
    return Array.from(s).sort()
  }, [transactions])

  // Fetch data on portfolio change
  useEffect(() => {
    if (!selectedId) return
    setIsLoading(true)
    setError(null)
    Promise.all([transactionsApi.list(selectedId), positionsApi.list(selectedId)])
      .then(([txns, pos]) => {
        setTransactions(txns)
        setPositions(pos)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load trades')
      })
      .finally(() => setIsLoading(false))
  }, [selectedId])

  // Reset page when filters change
  const filterKey = `${filters.type}-${filters.symbol}-${filters.dateFrom}-${filters.dateTo}`
  useEffect(() => {
    setPage(1)
  }, [filterKey])

  // Apply filters
  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      if (filters.type && t.type !== filters.type) return false
      if (filters.symbol && (t.symbol ?? '') !== filters.symbol) return false
      if (filters.dateFrom) {
        const d = new Date(t.trade_date)
        const from = new Date(filters.dateFrom)
        if (d < from) return false
      }
      if (filters.dateTo) {
        const d = new Date(t.trade_date)
        const to = new Date(filters.dateTo)
        to.setUTCHours(23, 59, 59, 999)
        if (d > to) return false
      }
      return true
    })
  }, [transactions, filters])

  // Paginate
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // Filter handler helper
  const setFilter = useCallback(<K extends keyof Filters>(key: K, value: Filters[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  // Reset filters
  const resetFilters = useCallback(() => {
    setFilters({ ...DEFAULT_FILTERS })
  }, [])

  // Summary stats
  const totalBuys = filtered.filter((t) => t.type === 'buy').length
  const totalSells = filtered.filter((t) => t.type === 'sell').length
  const totalRealized = filtered.reduce((sum, t) => {
    return sum + (t.realized_gain ? parseFloat(t.realized_gain) : 0)
  }, 0)

  /* ── Empty / loading states ──────────────────────────────────────── */

  if (!selectedId) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Select a portfolio to view trades</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-text-dim">
        <p>Loading trades…</p>
      </div>
    )
  }

  /* ── Render ──────────────────────────────────────────────────────── */

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="rounded border border-border bg-surface p-4">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h1 className="font-semibold text-lg text-text">Trade History</h1>
          <div className="flex gap-2">
            <Link
              to="/dashboard"
              className="rounded border border-border px-3 py-1 text-sm text-text-dim transition hover:border-accent hover:text-accent"
            >
              ← Dashboard
            </Link>
            <button
              type="button"
              onClick={() => exportTradesCSV(filtered)}
              disabled={filtered.length === 0}
              className="rounded border border-border px-3 py-1 text-sm text-text-dim transition hover:border-accent hover:text-accent disabled:opacity-50"
            >
              ↓ Trades CSV
            </button>
            <button
              type="button"
              onClick={() => exportPositionsCSV(positions)}
              disabled={positions.length === 0}
              className="rounded border border-border px-3 py-1 text-sm text-text-dim transition hover:border-accent hover:text-accent disabled:opacity-50"
            >
              ↓ Positions CSV
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-3 py-2 text-negative text-sm">
            {error}
          </div>
        )}

        {/* Summary stats */}
        <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded border border-border/50 px-3 py-2">
            <div className="text-xs text-text-dim">Total trades</div>
            <div className="font-mono-financial text-text">{filtered.length}</div>
          </div>
          <div className="rounded border border-border/50 px-3 py-2">
            <div className="text-xs text-text-dim">Buys / Sells</div>
            <div className="font-mono-financial text-text">
              <span className="text-positive">{totalBuys}</span>
              {' / '}
              <span className="text-negative">{totalSells}</span>
            </div>
          </div>
          <div className="rounded border border-border/50 px-3 py-2">
            <div className="text-xs text-text-dim">Realized P&L</div>
            <div className={`font-mono-financial ${totalRealized >= 0 ? 'text-positive' : 'text-negative'}`}>
              {totalRealized >= 0 ? '+' : ''}$
              {Math.abs(totalRealized).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
          </div>
          <div className="rounded border border-border/50 px-3 py-2">
            <div className="text-xs text-text-dim">Showing</div>
            <div className="font-mono-financial text-text">
              {paginated.length} of {filtered.length}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-end gap-3">
          {/* Type filter */}
          <label className="block text-xs text-text-dim">
            Type
            <select
              value={filters.type}
              onChange={(e) => setFilter('type', e.target.value)}
              className="mt-1 rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent"
            >
              <option value="">All</option>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>

          {/* Symbol filter */}
          {symbols.length > 0 && (
            <label className="block text-xs text-text-dim">
              Symbol
              <select
                value={filters.symbol}
                onChange={(e) => setFilter('symbol', e.target.value)}
                className="mt-1 rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent"
              >
                <option value="">All</option>
                {symbols.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          )}

          {/* Date range */}
          <label className="block text-xs text-text-dim">
            From
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => setFilter('dateFrom', e.target.value)}
              className="mt-1 rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent"
            />
          </label>

          <label className="block text-xs text-text-dim">
            To
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => setFilter('dateTo', e.target.value)}
              className="mt-1 rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent"
            />
          </label>

          {/* Reset */}
          {(filters.type || filters.symbol || filters.dateFrom || filters.dateTo) && (
            <button
              type="button"
              onClick={resetFilters}
              className="rounded border border-border px-3 py-1 text-xs text-text-dim transition hover:border-text hover:text-text"
            >
              Reset
            </button>
          )}
        </div>

        {/* Table */}
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-text-dim">
            <p className="text-lg">No trades found</p>
            <p className="mt-1 text-sm">
              {transactions.length === 0 ? 'Record a trade to get started' : 'Try adjusting your filters'}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-border border-b text-left text-text-dim">
                    <th className="pr-4 pb-2">Date</th>
                    <th className="pr-4 pb-2">Type</th>
                    <th className="pr-4 pb-2">Symbol</th>
                    <th className="pr-4 pb-2 text-right">Qty</th>
                    <th className="pr-4 pb-2 text-right">Price</th>
                    <th className="pr-4 pb-2 text-right">Fees</th>
                    <th className="pr-4 pb-2 text-right">Realized P&L</th>
                    {transactions.some((t) => t.notes) && <th className="pb-2 text-right">Notes</th>}
                  </tr>
                </thead>
                <tbody>
                  {paginated.map((t) => (
                    <tr key={t.id} className="border-border/50 border-b">
                      <td className="py-2 pr-4 text-text-dim">
                        {new Date(t.trade_date).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td className="py-2 pr-4">
                        <span
                          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                            t.type === 'buy'
                              ? 'bg-positive/10 text-positive'
                              : t.type === 'sell'
                                ? 'bg-negative/10 text-negative'
                                : 'bg-border/30 text-text-dim'
                          }`}
                        >
                          {t.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 pr-4 font-medium text-text">{t.symbol ?? '-'}</td>
                      <td className="py-2 pr-4 text-right font-mono-financial text-text">
                        {parseFloat(t.quantity).toLocaleString()}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono-financial text-text">
                        ${parseFloat(t.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2 pr-4 text-right font-mono-financial text-text-dim">
                        ${parseFloat(t.fees).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td
                        className={`py-2 pr-4 text-right font-mono-financial ${
                          t.realized_gain == null
                            ? 'text-text-dim'
                            : parseFloat(t.realized_gain) >= 0
                              ? 'text-positive'
                              : 'text-negative'
                        }`}
                      >
                        {t.realized_gain != null
                          ? `${parseFloat(t.realized_gain) >= 0 ? '+' : ''}$${Math.abs(parseFloat(t.realized_gain)).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                          : '-'}
                      </td>
                      {transactions.some((tx) => tx.notes) && (
                        <td className="py-2 text-right text-text-dim" title={t.notes ?? ''}>
                          {t.notes && <span className="max-w-48 truncate">{t.notes}</span>}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <div className="text-xs text-text-dim">
                  Page {page} of {totalPages} ({filtered.length} trades)
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded border border-border px-3 py-1 text-sm text-text-dim transition hover:border-accent hover:text-accent disabled:opacity-50"
                  >
                    ← Prev
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    // Show pages around current page
                    let startPage = Math.max(1, page - 2)
                    if (startPage + 4 > totalPages) startPage = Math.max(1, totalPages - 4)
                    const p = startPage + i
                    if (p > totalPages) return null
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPage(p)}
                        className={`rounded border px-3 py-1 text-sm transition ${
                          p === page
                            ? 'border-accent bg-accent/10 text-accent'
                            : 'border-border text-text-dim hover:border-accent hover:text-accent'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  })}
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="rounded border border-border px-3 py-1 text-sm text-text-dim transition hover:border-accent hover:text-accent disabled:opacity-50"
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
