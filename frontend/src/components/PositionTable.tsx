import type { Position } from '../services/api';

interface PositionTableProps {
  positions: Position[];
}

function PositionCard({ position }: { position: Position }) {
  const currentPrice = position.current_price || 0;
  const totalValue = position.market_value || (position.quantity * currentPrice);
  const gain = position.gain || 0;
  const gainPct = position.gain_pct || 0;

  return (
    <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg p-4 mb-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-900/30 flex items-center justify-center">
            <span className="text-emerald-400 font-bold text-sm">
              {position.symbol.slice(0, 2)}
            </span>
          </div>
          <div>
            <h4 className="text-white font-semibold text-lg">{position.symbol}</h4>
            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-emerald-900/30 text-emerald-400">
              {position.asset_class || 'N/A'}
            </span>
          </div>
        </div>
        <div className={`text-right ${gain >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          <div className="text-lg font-bold">
            {gain >= 0 ? '+' : ''}${gain.toFixed(2)}
          </div>
          <div className="text-sm">
            ({gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%)
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 text-sm">
        <div>
          <div className="text-slate-400 text-xs mb-0.5">Qty</div>
          <div className="text-white font-medium">{position.quantity.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-slate-400 text-xs mb-0.5">Price</div>
          <div className="text-white font-medium">${currentPrice.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-400 text-xs mb-0.5">Value</div>
          <div className="text-white font-medium">${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </div>
      </div>
    </div>
  );
}

export function PositionTable({ positions }: PositionTableProps) {
  if (positions.length === 0) {
    return (
      <div className="text-center py-10 sm:py-12">
        <p className="text-slate-400 text-lg">No positions yet</p>
        <p className="text-slate-500 text-sm mt-2">Add your first position to get started</p>
      </div>
    );
  }

  return (
    <>
      {/* Desktop Table View (≥768px) */}
      <div className="hidden sm:block bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-black/50">
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider sticky left-0 bg-black/70 backdrop-blur">
                  Symbol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Class
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Quantity
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Price
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Value
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                  P&L
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-dark">
              {positions.map((position) => {
                const currentPrice = position.current_price || 0;
                const totalValue = position.market_value || (position.quantity * currentPrice);
                const gain = position.gain || 0;
                const gainPct = position.gain_pct || 0;

                return (
                  <tr key={position.id} className="hover:bg-black/30">
                    <td className="px-6 py-4 whitespace-nowrap sticky left-0 bg-gray-900/90 backdrop-blur">
                      <div className="text-sm font-medium text-white">{position.symbol}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-emerald-900/30 text-emerald-400">
                        {position.asset_class || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-white">
                      {position.quantity}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-slate-300">
                      ${currentPrice.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-white">
                      ${totalValue.toFixed(2)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${gain >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {gain >= 0 ? '+' : ''}${gain.toFixed(2)} ({gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%)
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile Card View (<768px) */}
      <div className="sm:hidden">
        {positions.map((position) => (
          <PositionCard key={position.id} position={position} />
        ))}
      </div>
    </>
  );
}
