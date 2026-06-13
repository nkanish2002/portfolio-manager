import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import { usePortfolioStore, usePositionStore } from '../store';
import { PositionTable } from '../components/PositionTable';
import { SellModal } from '../components/SellModal';
import useWebSocket, { type WebSocketMessage } from '../hooks/useWebSocket';
import type { Position } from '../services/api';

interface SummaryStatsProps {
  positions: Array<{
    market_value?: number;
    gain?: number;
    quantity?: number;
    avg_cost_basis?: number;
    current_price?: number;
  }>;
}

function SummaryStats({ positions }: SummaryStatsProps) {
  const totalValue = positions.reduce((sum, p) => sum + (p.market_value || (p.quantity || 0) * (p.current_price || 0)), 0);
  const totalCost = positions.reduce((sum, p) => sum + (p.quantity || 0) * (p.avg_cost_basis || 0), 0);
  const totalGain = totalValue - totalCost;
  const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
      <div className="bg-gray-900/80 border border-slate-800 p-3 sm:p-4">
        <div className="text-slate-500 text-xs mb-1">Total Value</div>
        <div className="text-white font-bold text-lg sm:text-xl">${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
      </div>
      <div className="bg-gray-900/80 border border-slate-800 p-3 sm:p-4">
        <div className="text-slate-500 text-xs mb-1">Cost Basis</div>
        <div className="text-white font-bold text-lg sm:text-xl">${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
      </div>
      <div className="bg-gray-900/80 border border-slate-800 p-3 sm:p-4">
        <div className="text-slate-500 text-xs mb-1">P&L</div>
        <div className="font-bold text-lg sm:text-xl text-white">
          {totalGain >= 0 ? '+' : ''}${totalGain.toFixed(2)}
          <span className="text-xs ml-1">({totalGainPct >= 0 ? '+' : ''}{totalGainPct.toFixed(2)}%)</span>
        </div>
      </div>
      <div className="bg-gray-900/80 border border-slate-800 p-3 sm:p-4">
        <div className="text-slate-500 text-xs mb-1">Positions</div>
        <div className="text-white font-bold text-lg sm:text-xl">{positions.length}</div>
      </div>
    </div>
  );
}

export function PositionsPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const { currentPortfolio } = usePortfolioStore();
  const { positions, loading, error, fetchPositions, refreshPrices } = usePositionStore();
  const [refreshing, setRefreshing] = useState(false);
  const [pullStart, setPullStart] = useState(0);
  const [pullDistance, setPullDistance] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const isPulling = useRef(false);

  // Sell modal state
  const [sellPosition, setSellPosition] = useState<Position | null>(null);
  const [sellOpen, setSellOpen] = useState(false);

  // Pull-to-refresh handlers — defined AFTER handleRefresh so it's available
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (window.scrollY > 0) return;
    isPulling.current = true;
    setPullStart(e.touches[0].clientY);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!isPulling.current || window.scrollY > 0) return;
    const distance = Math.max(0, e.touches[0].clientY - pullStart);
    setPullDistance(distance);
  }, [pullStart]);

  // handleRefresh MUST be defined before handleTouchEnd uses it
  const handleRefresh = useCallback(async () => {
    if (!portfolioId || refreshing) return;
    setRefreshing(true);
    try {
      await refreshPrices(portfolioId);
    } finally {
      setRefreshing(false);
    }
  }, [portfolioId, refreshPrices, refreshing]);

  const handleTouchEnd = useCallback(() => {
    if (pullDistance > 80) {
      handleRefresh();
    }
    isPulling.current = false;
    setPullDistance(0);
  }, [pullDistance, handleRefresh]);

  const handleSell = useCallback((position: Position) => {
    setSellPosition(position);
    setSellOpen(true);
  }, []);

  const handleSellComplete = useCallback(() => {
    setSellOpen(false);
    setSellPosition(null);
    if (portfolioId) fetchPositions(portfolioId);
  }, [portfolioId, fetchPositions]);

  // WebSocket
  const handleMessage = useCallback((msg: WebSocketMessage) => {
    if (msg.type === 'batch' && 'updates' in msg) {
      for (const update of msg.updates) {
        window.dispatchEvent(new CustomEvent('ws-price-flash', {
          detail: { symbol: update.cusip || update.symbol, prev: update.prev, price: update.price },
        }));
      }
    }
  }, []);

  const { connected } = useWebSocket('/ws/quotes', handleMessage);

  // Load positions on route change — NO MORE GUARD that redirects to dashboard
  useEffect(() => {
    if (portfolioId) {
      fetchPositions(portfolioId);
    }
  }, [portfolioId, fetchPositions]);

  return (
    <div
      ref={containerRef}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      className="space-y-4 sm:space-y-6"
    >
      {/* Live indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-none ${connected ? 'bg-white animate-pulse' : 'bg-slate-600'}`} />
          <span className="text-xs text-slate-500">{connected ? 'Live' : 'Offline'}</span>
        </div>
        <div className="text-xs text-slate-500">
          {currentPortfolio ? currentPortfolio.name : (portfolioId ? portfolioId.substring(0, 8) : '')}
        </div>
      </div>

      {/* Pull-to-refresh indicator */}
      {pullDistance > 0 && (
        <div className="text-center py-2 text-sm text-slate-400">
          {pullDistance > 80 ? 'Release to refresh...' : 'Pull to refresh...'}
        </div>
      )}

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
          <h1 className="text-2xl sm:text-3xl font-bold text-white">
            {currentPortfolio?.name || (portfolioId ? `Portfolio ${portfolioId.substring(0, 8)}` : 'Select Portfolio')}
          </h1>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 text-sm font-medium px-4 py-3 rounded-none bg-slate-800 text-white hover:bg-slate-700 disabled:opacity-50 transition-colors min-h-[44px]"
        >
          <svg className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh Prices
        </button>
      </div>

      {/* Summary Stats */}
      <SummaryStats positions={positions} />

      {/* Loading/Error */}
      {loading && (
        <div className="flex items-center justify-center py-8 sm:py-12">
          <div className="animate-spin rounded-none h-8 w-8 sm:h-10 sm:w-10 border-b-2 border-white"></div>
        </div>
      )}

      {error && (
        <div className="bg-slate-800 border border-slate-700 text-white p-3 sm:p-4 rounded-none">
          {error}
        </div>
      )}

      {/* Positions */}
      {!loading && <PositionTable positions={positions} onSell={handleSell} />}

      {/* Sell Modal */}
      <SellModal
        position={sellPosition}
        portfolioId={portfolioId ?? null}
        isOpen={sellOpen}
        onClose={() => { setSellOpen(false); setSellPosition(null); }}
        onSellComplete={handleSellComplete}
      />
    </div>
  );
}
