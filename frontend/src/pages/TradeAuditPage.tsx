import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router';
import { tradeService, type Trade, type TradeSummary } from '../services/api';
import { usePortfolioStore } from '../store';

function formatCurrency(n: number): string {
  return n >= 0 ? `+$${n.toFixed(2)}` : `-$${Math.abs(n).toFixed(2)}`;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDateForInput(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toISOString().split('T')[0];
}

interface SummaryCardProps {
  title: string;
  value: number;
  positive?: boolean;
  negative?: boolean;
}

function SummaryCard({ title, value, positive, negative }: SummaryCardProps) {
  const colorClass = positive ? 'text-white' : negative ? 'text-white' : 'text-white';
  return (
    <div className="bg-gray-900/80 border border-slate-800 rounded-none p-4">
      <div className="text-slate-400 text-xs mb-1">{title}</div>
      <div className={`font-bold text-xl ${colorClass}`}>
        {value.toLocaleString()}
      </div>
    </div>
  );
}

export function TradeAuditPage() {
  const navigate = useNavigate();
  const { portfolioId: routeId } = useParams<{ portfolioId: string }>();
  const { currentPortfolio } = usePortfolioStore();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [summary, setSummary] = useState<TradeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [symbolFilter, setSymbolFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  const portfolioId = currentPortfolio?.id || routeId || null;

  const fetchTrades = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (symbolFilter) params.symbol = symbolFilter;
      if (typeFilter) params.trade_type = typeFilter;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      params.sort_by = sortBy;
      params.sort_order = sortOrder;

      const [tradesRes, summaryRes] = await Promise.all([
        tradeService.list(portfolioId, params),
        tradeService.summary(portfolioId),
      ]);

      setTrades(tradesRes.data);
      setSummary(summaryRes.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load trades');
    } finally {
      setLoading(false);
    }
  }, [portfolioId, symbolFilter, typeFilter, startDate, endDate, sortBy, sortOrder]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades, currentPortfolio]);

  const handleExportCSV = useCallback(() => {
    if (trades.length === 0) return;

    const headers = ['Date', 'Symbol', 'Type', 'Quantity', 'Price', 'Fees', 'P&L', 'Notes'];
    const rows = trades.map((t) => [
      formatDate(t.transaction_date),
      t.symbol,
      t.type,
      t.quantity.toString(),
      `$${t.price.toFixed(2)}`,
      `$${t.fees.toFixed(2)}`,
      formatCurrency(t.p_and_l),
      `"${(t.notes || '').replace(/"/g, '""')}"`,
    ]);

    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_${currentPortfolio?.name || 'export'}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [trades, currentPortfolio]);

  if (!portfolioId || !currentPortfolio) {
    navigate('/dashboard');
    return null;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-sm text-slate-400 hover:text-white mb-2 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Dashboard
          </button>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">{currentPortfolio.name} — Trade Audit</h1>
        </div>
        <button
          onClick={handleExportCSV}
          disabled={trades.length === 0}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 text-sm font-medium px-4 py-3 rounded-none bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-50 transition-colors min-h-[44px]"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          <SummaryCard title="Total Trades" value={summary.total_trades} />
          <SummaryCard title="Buys" value={summary.total_buys} />
          <SummaryCard title="Sells" value={summary.total_sells} />
          <SummaryCard title="Realized Gains" value={summary.realized_gain} positive />
          <SummaryCard title="Realized Losses" value={summary.realized_loss} negative />
          <SummaryCard
            title="Net P&L"
            value={summary.net_realized_p_and_l}
            positive={summary.net_realized_p_and_l > 0}
            negative={summary.net_realized_p_and_l < 0}
          />
        </div>
      )}

      {/* Filters */}
      <div className="bg-gray-900/80 border border-slate-800 rounded-none p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">CUSIP</label>
            <input
              type="text"
              placeholder="123456789"
              value=""
              readOnly
              className="w-full bg-gray-800 border border-slate-800 text-slate-500 px-3 py-2 rounded-none focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Symbol</label>
            <input
              type="text"
              placeholder="AAPL, TSLA..."
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="w-full bg-gray-800 border border-slate-800 text-white px-3 py-2 rounded-none focus:outline-none focus:border-slate-600 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Type</label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full bg-gray-800 border border-slate-800 text-white px-3 py-2 rounded-none focus:outline-none focus:border-slate-600 text-sm"
            >
              <option value="">All Types</option>
              <option value="BUY">Buy</option>
              <option value="SELL">Sell</option>
              <option value="DIVIDEND">Dividend</option>
              <option value="SPLIT">Split</option>
              <option value="FEE">Fee</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(formatDateForInput(e.target.value))}
              className="w-full bg-gray-800 border border-slate-800 text-white px-3 py-2 rounded-none focus:outline-none focus:border-slate-600 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(formatDateForInput(e.target.value))}
              className="w-full bg-gray-800 border border-slate-800 text-white px-3 py-2 rounded-none focus:outline-none focus:border-slate-600 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Sort</label>
            <div className="flex gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="flex-1 bg-gray-800 border border-slate-800 text-white px-2 py-2 rounded-none focus:outline-none focus:border-slate-600 text-sm"
              >
                <option value="date">Date</option>
                <option value="symbol">Symbol</option>
                <option value="type">Type</option>
              </select>
              <button
                type="button"
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="px-3 py-2 bg-gray-800 border border-slate-800 text-slate-300 hover:text-white rounded-none text-sm min-h-[38px]"
              >
                {sortOrder === 'asc' ? '↑' : '↓'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Loading/Error */}
      {loading && (
        <div className="flex items-center justify-center py-8 sm:py-12">
          <div className="animate-spin rounded-none h-8 w-8 sm:h-10 sm:w-10 border-b-2 border-emerald-400"></div>
        </div>
      )}

      {error && (
        <div className="bg-slate-900/30 border border-slate-800 text-white p-3 sm:p-4 rounded">
          {error}
        </div>
      )}

      {/* Trades Table */}
      {!loading && (
        <div className="bg-gray-900/80 border border-slate-800 rounded-none overflow-hidden">
          {/* Desktop Table View (≥768px) */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-black/50">
                  <th className="px-4 sm:px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Date</th>
                  <th className="px-4 sm:px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">CUSIP</th>
                  <th className="px-4 sm:px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Symbol</th>
                  <th className="px-4 sm:px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Type</th>
                  <th className="px-4 sm:px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Quantity</th>
                  <th className="px-4 sm:px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Price</th>
                  <th className="px-4 sm:px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Fees</th>
                  <th className="px-4 sm:px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">P&L</th>
                  <th className="px-4 sm:px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-dark">
                {trades.map((trade) => (
                  <tr key={trade.id} className="hover:bg-black/30">
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-sm text-slate-300">
                      {formatDate(trade.transaction_date)}
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-sm text-slate-300 font-mono">
                      {trade.cusip || '—'}
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-sm font-medium text-white">
                      {trade.symbol}
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-none ${
                        trade.type === 'SELL' ? 'bg-slate-900/30 text-white' :
                        trade.type === 'DIVIDEND' ? 'bg-slate-800 text-slate-300' :
                        trade.type === 'SPLIT' ? 'bg-slate-800 text-slate-300' :
                        'bg-slate-800 text-white'
                      }`}>
                        {trade.type}
                      </span>
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-right text-sm text-white">
                      {trade.quantity.toLocaleString()}
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-right text-sm text-slate-300">
                      ${trade.price.toFixed(2)}
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-right text-sm text-slate-300">
                      ${trade.fees.toFixed(2)}
                    </td>
                    <td className={`px-4 sm:px-6 py-3 whitespace-nowrap text-right text-sm font-medium ${
                      trade.p_and_l >= 0 ? 'text-white' : 'text-white'
                    }`}>
                      {formatCurrency(trade.p_and_l)}
                    </td>
                    <td className="px-4 sm:px-6 py-3 whitespace-nowrap text-sm text-slate-400 max-w-xs truncate">
                      {trade.notes || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View (<768px) */}
          <div className="sm:hidden">
            {trades.map((trade) => (
              <div key={trade.id} className="border-b border-slate-800 p-4 last:border-b-0">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-bold font-mono text-sm">{trade.cusip || trade.symbol}</span>
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-none ${
                      trade.type === 'SELL' ? 'bg-slate-900/30 text-white' :
                      trade.type === 'DIVIDEND' ? 'bg-slate-800 text-slate-300' :
                      trade.type === 'SPLIT' ? 'bg-slate-800 text-slate-300' :
                      'bg-slate-800 text-white'
                    }`}>
                      {trade.type}
                    </span>
                  </div>
                  <span className={`font-bold ${trade.p_and_l >= 0 ? 'text-white' : 'text-white'}`}>
                    {formatCurrency(trade.p_and_l)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-slate-500 text-xs">Date</span>
                    <div className="text-slate-300">{formatDate(trade.transaction_date)}</div>
                  </div>
                  <div>
                    <span className="text-slate-500 text-xs">Quantity</span>
                    <div className="text-slate-300">{trade.quantity.toLocaleString()}</div>
                  </div>
                  <div>
                    <span className="text-slate-500 text-xs">Price</span>
                    <div className="text-slate-300">${trade.price.toFixed(2)}</div>
                  </div>
                  <div>
                    <span className="text-slate-500 text-xs">Fees</span>
                    <div className="text-slate-300">${trade.fees.toFixed(2)}</div>
                  </div>
                </div>
                {trade.notes && (
                  <div className="mt-2 text-xs text-slate-500">
                    {trade.notes}
                  </div>
                )}
              </div>
            ))}
          </div>

          {trades.length === 0 && !loading && (
            <div className="text-center py-10 sm:py-12">
              <p className="text-slate-400 text-lg">No trades found</p>
              <p className="text-slate-500 text-sm mt-2">Try adjusting your filters</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
