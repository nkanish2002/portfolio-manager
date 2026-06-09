interface MonthlyReturnsChartProps {
  years: number[];
  months: string[];
  values: number[][];
  className?: string;
}

function getCellColor(value: number): string {
  if (value >= 5) return 'bg-emerald-500 text-white';
  if (value >= 2) return 'bg-emerald-600/80 text-white';
  if (value >= 0.5) return 'bg-emerald-700/60 text-white';
  if (value >= 0) return 'bg-emerald-800/40 text-emerald-300';
  if (value >= -0.5) return 'bg-red-800/40 text-red-300';
  if (value >= -2) return 'bg-red-700/60 text-white';
  if (value >= -5) return 'bg-red-600/80 text-white';
  return 'bg-red-500 text-white';
}

function getCellSize(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 10) return 'text-xs font-bold';
  if (abs >= 5) return 'text-xs font-semibold';
  if (abs >= 2) return 'text-xs';
  return 'text-[10px]';
}

export function MonthlyReturnsChart({
  years,
  months,
  values,
  className = '',
}: MonthlyReturnsChartProps) {
  if (!years.length || !months.length || !values.length) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Monthly Returns</h2>
        <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
          Insufficient data for heatmap
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <h2 className="text-lg font-semibold text-white">Monthly Returns Heatmap</h2>

      {/* Month headers */}
      <div className="grid gap-1" style={{ gridTemplateColumns: `60px repeat(${months.length}, 1fr)` }}>
        <div />
        {months.map((month) => (
          <div key={month} className="text-center text-xs text-slate-500 font-medium">
            {month}
          </div>
        ))}
      </div>

      {/* Rows */}
      <div className="space-y-1">
        {years.map((year, rowIdx) => (
          <div
            key={year}
            className="grid gap-1"
            style={{ gridTemplateColumns: `60px repeat(${months.length}, 1fr)` }}
          >
            <div className="text-xs text-slate-400 font-medium flex items-center">{year}</div>
            {months.map((_, colIdx) => {
              const val = values[rowIdx]?.[colIdx] ?? null;
              if (val === null) {
                return <div key={colIdx} className="h-8 bg-slate-900/30 rounded-none" />;
              }
              return (
                <div
                  key={colIdx}
                  className={`h-8 flex items-center justify-center rounded-none transition-colors cursor-default hover:ring-1 hover:ring-white/20 ${getCellColor(val)} ${getCellSize(val)}`}
                  title={`${year} ${months[colIdx]}: ${val >= 0 ? '+' : ''}${val.toFixed(2)}%`}
                >
                  {val >= 0 ? '+' : ''}{val.toFixed(1)}%
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-slate-500 pt-2 border-t border-slate-800">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-red-500 rounded-none inline-block"></span> Negative
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 bg-emerald-500 rounded-none inline-block"></span> Positive
        </span>
      </div>
    </div>
  );
}
