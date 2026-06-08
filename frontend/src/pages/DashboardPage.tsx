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
    <div className="fixed inset-0 bg-black/80 backdrop-blur flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-slate-dark rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-white mb-4">Create New Portfolio</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Portfolio Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My Growth Portfolio"
              className="w-full bg-black border border-slate-dark rounded px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Currency</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-black border border-slate-dark rounded px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
            >
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="INR">INR (₹)</option>
            </select>
          </div>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
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
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <span className="text-sm text-slate-400 mt-1 block">
            {portfolios.length} {portfolios.length === 1 ? 'portfolio' : 'portfolios'}
          </span>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 transition-colors font-medium"
        >
          + New Portfolio
        </button>
      </div>

      {portfolios.length === 0 ? (
        <div className="text-center py-12 bg-gray-900/50 rounded-lg border border-slate-dark">
          <p className="text-slate-400 text-lg mb-4">No portfolios yet</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-emerald-600 text-white rounded hover:bg-emerald-700 font-medium"
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

      <CreatePortfolioModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
    </div>
  );
}
