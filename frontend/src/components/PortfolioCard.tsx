import type { Portfolio } from '../services/api';

interface PortfolioCardProps {
  portfolio: Portfolio;
  onClick: () => void;
}

export function PortfolioCard({ portfolio, onClick }: PortfolioCardProps) {
  return (
    <div
      onClick={onClick}
      className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6 cursor-pointer hover:border-emerald-500/50 transition-all hover:shadow-lg hover:shadow-emerald-500/10"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-white">{portfolio.name}</h3>
        <span className="text-sm text-slate-400">{portfolio.currency}</span>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between">
          <span className="text-sm text-slate-400">Created</span>
          <span className="text-sm text-white">
            {new Date(portfolio.created_at).toLocaleDateString()}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-slate-400">Last Updated</span>
          <span className="text-sm text-white">
            {new Date(portfolio.updated_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
}
