import { useEffect, useState } from 'react';
import type { Position } from '../services/api';

interface PositionTableProps {
  positions: Position[];
  onSell?: (position: Position) => void;
}

interface FlashState {
  [symbol: string]: { direction: 'up' | 'down'; ts: number };
}

function PositionCard({ position, onSell }: { position: Position; onSell?: () => void }) {
  const currentPrice = position.current_price || 0;
  const totalValue = position.market_value || (position.quantity * currentPrice);
  const gain = position.gain || 0;
  const gainPct = position.gain_pct || 0;

  return (
    <div className="bg-gray-900/80 backdrop-blur border border-slate-800 p-4 mb-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-none bg-slate-800 flex items-center justify-center">
            <span className="text-white font-bold text-sm">
              {position.name.slice(0, 2).toUpperCase()}
            </span>
          </div>
          <div>
            <h4 className="text-white font-semibold text-lg">{position.name}</h4>
            <div className="text-xs text-slate-500 font-mono">{position.cusip || position.symbol}</div>
            <span className="px-2 inline-flex text-xs leading-5 font-semibold bg-slate-800 text-slate-400">
              {position.asset_class || 'N/A'}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-white">
            {gain >= 0 ? '+' : ''}${gain.toFixed(2)}
          </div>
          <div className="text-sm text-slate-400">
            ({gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%)
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm mb-3">
        <div>
          <div className="text-slate-500 text-xs mb-0.5">Qty</div>
          <div className="text-white font-medium">{position.quantity.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-slate-500 text-xs mb-0.5">Price</div>
          <div className="text-white font-medium">${currentPrice.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-500 text-xs mb-0.5">Value</div>
          <div className="text-white font-medium">${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
        </div>
      </div>

      {onSell && (
        <button
          onClick={onSell}
          className="w-full py-2 text-sm font-medium bg-slate-800 text-white hover:bg-slate-700 transition-colors"
        >
          Sell
        </button>
      )}
    </div>
  );
}

export function PositionTable({ positions, onSell }: PositionTableProps) {
  const [flashState, setFlashState] = useState<FlashState>({});

  useEffect(() => {
    if (Object.keys(flashState).length === 0) return;
    const interval = setInterval(() => {
      setFlashState((prev) => {
        const now = Date.now();
        const next = { ...prev };
        for (const sym in next) {
          if (now - next[sym].ts > 1500) {
            delete next[sym];
          }
        }
        return next;
      });
    }, 250);
    return () => clearInterval(interval);
  }, [flashState]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { symbol: string; prev: number; price: number } | null;
      if (!detail) return;
      setFlashState((prev) => ({
        ...prev,
        [detail.symbol]: { direction: detail.price > detail.prev ? 'up' : 'down', ts: Date.now() },
      }));
    };
    window.addEventListener('ws-price-flash', handler);
    return () => window.removeEventListener('ws-price-flash', handler);
  }, []);

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
      <div className="hidden sm:block bg-gray-900/80 backdrop-blur border border-slate-800 rounded-none overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-black/50">
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider sticky left-0 bg-black/70 backdrop-blur">CUSIP</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Class</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Quantity</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Value</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">P&L</th>
                {onSell && <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wider">Action</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {positions.map((position) => {
                const currentPrice = position.current_price || 0;
                const totalValue = position.market_value || (position.quantity * currentPrice);
                const gain = position.gain || 0;
                const gainPct = position.gain_pct || 0;
                const flashKey = position.cusip || position.symbol;
                const flash = flashState[flashKey];
                const isFlash = flash && (Date.now() - flash.ts < 1500);

                return (
                  <tr key={position.id} className="hover:bg-black/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap sticky left-0 bg-gray-900/90 backdrop-blur">
                      <div className="text-sm font-medium text-white font-mono">{flashKey}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{position.symbol}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold bg-slate-800 text-slate-400">{position.asset_class || 'N/A'}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-white">{position.quantity}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-slate-300">
                      ${currentPrice.toFixed(2)}
                      {isFlash && <span className="ml-1 text-xs">{flash.direction === 'up' ? '▲' : '▼'}</span>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-white">${totalValue.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-white">
                      {gain >= 0 ? '+' : ''}${gain.toFixed(2)} ({gainPct >= 0 ? '+' : ''}{gainPct.toFixed(2)}%)
                    </td>
                    {onSell && (
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); onSell(position); }}
                          className="px-3 py-1.5 text-xs font-medium bg-slate-800 text-white hover:bg-slate-700 transition-colors"
                        >
                          Sell
                        </button>
                      </td>
                    )}
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
          <PositionCard key={position.id} position={position} onSell={onSell ? () => onSell(position) : undefined} />
        ))}
      </div>
    </>
  );
}
