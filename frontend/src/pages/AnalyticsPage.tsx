export function AnalyticsPage() {
  return (
    <div className="space-y-4 sm:space-y-6">
      <h1 className="text-2xl sm:text-3xl font-bold text-white">Analytics</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-none p-4 sm:p-6">
          <h2 className="text-lg sm:text-xl font-semibold text-white mb-4">Portfolio Comparison</h2>
          <div className="h-48 sm:h-64 flex items-center justify-center text-slate-400 text-sm sm:text-base">
            Chart placeholder
          </div>
        </div>
        
        <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-none p-4 sm:p-6">
          <h2 className="text-lg sm:text-xl font-semibold text-white mb-4">Risk Metrics</h2>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-slate-dark">
              <span className="text-slate-400 text-sm sm:text-base">Sharpe Ratio</span>
              <span className="text-white text-sm sm:text-base">—</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-dark">
              <span className="text-slate-400 text-sm sm:text-base">Sortino Ratio</span>
              <span className="text-white text-sm sm:text-base">—</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-dark">
              <span className="text-slate-400 text-sm sm:text-base">Max Drawdown</span>
              <span className="text-white text-sm sm:text-base">—</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
