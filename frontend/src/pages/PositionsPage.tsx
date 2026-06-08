import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router';
import { usePortfolioStore, usePositionStore } from '../store';
import { PositionTable } from '../components/PositionTable';

export function PositionsPage() {
  const { portfolioId } = useParams<{ portfolioId: string }>();
  const navigate = useNavigate();
  const { currentPortfolio, setCurrentPortfolio, clearCurrentPortfolio } = usePortfolioStore();
  const { positions, loading, error, fetchPositions, refreshPrices } = usePositionStore();

  useEffect(() => {
    if (portfolioId) {
      setCurrentPortfolio(portfolioId);
      fetchPositions(portfolioId);
    }
    return () => clearCurrentPortfolio();
  }, [portfolioId, setCurrentPortfolio, fetchPositions, clearCurrentPortfolio]);

  if (!portfolioId || !currentPortfolio) {
    navigate('/dashboard');
    return null;
  }

  const handleRefresh = async () => {
    await refreshPrices(portfolioId);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-sm text-slate-400 hover:text-white mb-2"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-white">{currentPortfolio.name}</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={handleRefresh}
            className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-md bg-slate-700 text-emerald-400 hover:bg-slate-600 transition-colors"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Prices
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-500 text-red-400 p-4 rounded">
          {error}
        </div>
      )}

      <PositionTable positions={positions} />
    </div>
  );
}
