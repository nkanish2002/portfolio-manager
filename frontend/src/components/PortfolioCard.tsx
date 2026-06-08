import type { Portfolio } from '../services/api';

interface PortfolioCardProps {
  portfolio: Portfolio;
  onClick: () => void;
}

export function PortfolioCard({ portfolio, onClick }: PortfolioCardProps) {
  const { name, currency, position_count, total_value, created_at, updated_at } = portfolio;

  return (
    <div
      onClick={onClick}
      className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6 cursor-pointer hover:border-emerald-500/50 transition-all hover:shadow-lg hover:shadow-emerald-500/10"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-white">{name}</h3>
        <span className="text-sm text-slate-400">{currency}</span>
      </div>
      
      <div className="space-y-2 mb-4">
        <div className="flex justify-between">
          <span className="text-sm text-slate-400">Total Value</span>
          <span className="text-lg font-bold text-emerald-400">${total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-slate-400">Positions</span>
          <span className="text-sm text-white">{position_count}</span>
        </div>
      </div>
      
      <div className="pt-4 border-t border-slate-dark">
        <div className="flex justify-between text-xs text-slate-500">
          <span>Created {new Date(created_at).toLocaleDateString()}</span>
          <span>Updated {new Date(updated_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
