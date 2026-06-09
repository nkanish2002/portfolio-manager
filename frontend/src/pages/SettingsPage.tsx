export function SettingsPage() {
  return (
    <div className="space-y-4 sm:space-y-6">
      <h1 className="text-2xl sm:text-3xl font-bold text-white">Settings</h1>
      
      <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-none p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold text-white mb-4">Data Sources</h2>
        <div className="space-y-3 sm:space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 sm:p-0">
            <div>
              <div className="text-white font-medium">Yahoo Finance</div>
              <div className="text-xs sm:text-sm text-slate-400">Development data source</div>
            </div>
            <span className="self-start sm:self-center px-3 py-1 bg-emerald-900/30 text-emerald-400 text-xs rounded-none">Active</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 sm:p-0">
            <div>
              <div className="text-white font-medium">Polygon.io</div>
              <div className="text-xs sm:text-sm text-slate-400">Production data source (pending)</div>
            </div>
            <span className="self-start sm:self-center px-3 py-1 bg-slate-800 text-slate-400 text-xs rounded-none">Pending</span>
          </div>
        </div>
      </div>

      <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-none p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold text-white mb-4">Display Preferences</h2>
        <div className="space-y-3 sm:space-y-4">
          <div className="flex items-center justify-between py-2 border-b border-slate-dark">
            <div className="text-white">Theme</div>
            <div className="text-xs sm:text-sm text-slate-400">Dark (default)</div>
          </div>
          <div className="flex items-center justify-between py-2">
            <div className="text-white">Currency</div>
            <div className="text-xs sm:text-sm text-slate-400">USD</div>
          </div>
        </div>
      </div>

      <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-none p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold text-white mb-4">About</h2>
        <div className="text-slate-400 text-xs sm:text-sm space-y-2">
          <p>Portfolio Manager v0.1.0</p>
          <p>A professional portfolio management tool for tracking and analyzing holdings.</p>
        </div>
      </div>
    </div>
  );
}
