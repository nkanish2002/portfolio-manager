import type { Portfolio } from '../services/api';

interface PortfolioCardProps {
  portfolio: Portfolio;
  onClick: () => void;
}

export function PortfolioCard({ portfolio, onClick }: PortfolioCardProps) {
  const { name, currency, position_count, total_value, created_at, updated_at } = portfolio;

  // Format dates safely
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return '—';
    }
  };

  return (
    <div
      onClick={onClick}
      className="bg-gray-900/80 backdrop-blur border border-slate-800 p-6 cursor-pointer hover:border-slate-600 transition-all"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-white">{name}</h3>
        <span className="text-sm text-slate-500">{currency}</span>
      </div>
      
      <div className="space-y-2 mb-4">
        <div className="flex justify-between">
          <span className="text-sm text-slate-500">Total Value</span>
          <span className="text-lg font-bold text-white">${total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-slate-500">Positions</span>
          <span className="text-sm text-white">{position_count}</span>
        </div>
      </div>
      
      <div className="pt-4 border-t border-slate-800">
        <div className="flex justify-between text-xs text-slate-600">
          <span>Created {formatDate(created_at)}</span>
          <span>Updated {formatDate(updated_at)}</span>
        </div>
      </div>
    </div>
  );
}
