export function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Analytics</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Portfolio Comparison</h2>
          <div className="h-64 flex items-center justify-center text-slate-400">
            Chart placeholder
          </div>
        </div>
        
        <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Risk Metrics</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-slate-400">Sharpe Ratio</span>
              <span className="text-white">—</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Sortino Ratio</span>
              <span className="text-white">—</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Max Drawdown</span>
              <span className="text-white">—</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
