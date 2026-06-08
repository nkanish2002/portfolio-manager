import type { Position } from '../services/api';

interface PositionTableProps {
  positions: Position[];
}

export function PositionTable({ positions }: PositionTableProps) {
  if (positions.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-400 text-lg">No positions yet</p>
        <p className="text-slate-500 text-sm mt-2">Add your first position to get started</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/80 backdrop-blur border border-slate-dark rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-black/50">
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
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
                  <td className="px-6 py-4 whitespace-nowrap">
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
  );
}
