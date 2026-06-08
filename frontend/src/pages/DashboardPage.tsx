import { useEffect } from 'react';
import { useNavigate } from 'react-router';
import { usePortfolioStore } from '../store';
import { PortfolioCard } from '../components/PortfolioCard';

export function DashboardPage() {
  const navigate = useNavigate();
  const { portfolios, loading, error, fetchPortfolios } = usePortfolioStore();

  useEffect(() => {
    fetchPortfolios();
  }, [fetchPortfolios]);

  const handlePortfolioClick = (id: string) => {
    navigate(`/dashboard/${id}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-500 text-red-400 p-4 rounded">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <span className="text-sm text-slate-400">
          {portfolios.length} {portfolios.length === 1 ? 'portfolio' : 'portfolios'}
        </span>
      </div>

      {portfolios.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-slate-400 text-lg">No portfolios yet</p>
          <button
            onClick={() => navigate('/settings')}
            className="mt-4 px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700"
          >
            Create your first portfolio
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {portfolios.map((portfolio) => (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              onClick={() => handlePortfolioClick(portfolio.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
