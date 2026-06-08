export function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Settings</h1>
      
      <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Data Sources</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-white font-medium">Yahoo Finance</div>
              <div className="text-sm text-slate-400">Development data source</div>
            </div>
            <span className="px-2 py-1 bg-emerald-900/30 text-emerald-400 text-xs rounded">Active</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-white font-medium">Polygon.io</div>
              <div className="text-sm text-slate-400">Production data source (pending)</div>
            </div>
            <span className="px-2 py-1 bg-slate-800 text-slate-400 text-xs rounded">Pending</span>
          </div>
        </div>
      </div>

      <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Display Preferences</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-white">Theme</div>
            <div className="text-sm text-slate-400">Dark (default)</div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-white">Currency</div>
            <div className="text-sm text-slate-400">USD</div>
          </div>
        </div>
      </div>

      <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">About</h2>
        <div className="text-slate-400">
          <p>Portfolio Manager v0.1.0</p>
          <p className="mt-2">A professional portfolio management tool for tracking and analyzing holdings.</p>
        </div>
      </div>
    </div>
  );
}
