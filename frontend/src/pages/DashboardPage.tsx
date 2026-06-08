import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { usePortfolioStore } from '../store';
import { PortfolioCard } from '../components/PortfolioCard';

interface CreatePortfolioModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function CreatePortfolioModal({ isOpen, onClose }: CreatePortfolioModalProps) {
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [loading, setLoading] = useState(false);
  const { createPortfolio } = usePortfolioStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    setLoading(true);
    try {
      const newPortfolio = await createPortfolio({ name: name.trim(), currency });
      navigate(`/dashboard/${newPortfolio.id}`);
      onClose();
    } catch (error) {
      console.error('Failed to create portfolio:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-4 sm:p-6">
      <div className="bg-gray-900 border border-slate-dark rounded-lg p-5 sm:p-6 w-full max-w-md mx-auto shadow-2xl" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white">Create New Portfolio</h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white min-w-[44px] min-h-[44px] flex items-center justify-center"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Portfolio Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My Growth Portfolio"
              className="w-full bg-black border border-slate-dark rounded px-3 py-3 text-white focus:outline-none focus:border-emerald-500 text-base"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Currency</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-black border border-slate-dark rounded px-3 py-3 text-white focus:outline-none focus:border-emerald-500 text-base"
            >
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="INR">INR (₹)</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 text-slate-300 hover:text-white hover:bg-slate-dark/50 rounded-lg transition-colors text-base font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex-1 px-4 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-base font-medium"
            >
              {loading ? 'Creating...' : 'Create Portfolio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { portfolios, loading, error, fetchPortfolios } = usePortfolioStore();
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    fetchPortfolios();
  }, [fetchPortfolios]);

  const handlePortfolioClick = (id: string) => {
    navigate(`/dashboard/${id}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 sm:h-96">
        <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-b-2 border-emerald-400"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-500 text-red-400 p-3 sm:p-4 rounded">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">Dashboard</h1>
          <span className="text-sm text-slate-400 mt-1 block">
            {portfolios.length} {portfolios.length === 1 ? 'portfolio' : 'portfolios'}
          </span>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="w-full sm:w-auto px-4 py-3 sm:py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium text-base sm:text-sm"
        >
          + New Portfolio
        </button>
      </div>

      {portfolios.length === 0 ? (
        <div className="text-center py-10 sm:py-12 bg-gray-900/50 rounded-lg border border-slate-dark">
          <p className="text-slate-400 text-lg mb-4">No portfolios yet</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="w-full sm:w-auto px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium"
          >
            Create your first portfolio
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {portfolios.map((portfolio) => (
            <PortfolioCard
              key={portfolio.id}
              portfolio={portfolio}
              onClick={() => handlePortfolioClick(portfolio.id)}
            />
          ))}
        </div>
      )}

      <CreatePortfolioModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
    </div>
  );
}
