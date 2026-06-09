import { useState, useEffect, useCallback } from 'react';
import { positionService, type Position, type SellResponse } from '../services/api';

interface SellModalProps {
  position: Position | null;
  portfolioId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSellComplete: () => void;
}

export function SellModal({ position, portfolioId, isOpen, onClose, onSellComplete }: SellModalProps) {
  const [step, setStep] = useState<'details' | 'confirm'>('details');
  const [quantity, setQuantity] = useState(0);
  const [price, setPrice] = useState(0);
  const [fees, setFees] = useState(0);
  const [notes, setNotes] = useState('');
  const [selling, setSelling] = useState(false);
  const [sellResult, setSellResult] = useState<SellResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setStep('details');
    setQuantity(0);
    setPrice(0);
    setFees(0);
    setNotes('');
    setSellResult(null);
    setError(null);
  }, []);

  useEffect(() => {
    if (isOpen && position) {
      setPrice(position.current_price || position.avg_cost_basis || 0);
      setQuantity(Math.round(position.quantity * 100) / 100);
      reset();
    }
  }, [isOpen, position]);

  const handleQuantityChange = (newQty: number) => {
    if (!position) return;
    const maxQty = Math.round(position.quantity * 100) / 100;
    setQuantity(Math.min(Math.max(0, newQty), maxQty));
  };

  const estimatedPnL = (() => {
    if (!position || price <= 0 || quantity <= 0) return 0;
    const cost = position.avg_cost_basis * quantity;
    const proceeds = price * quantity;
    return proceeds - cost - fees;
  })();

  const handleConfirm = async () => {
    if (!portfolioId || !position || quantity <= 0 || price <= 0) return;
    setSelling(true);
    setError(null);
    try {
      const response = await positionService.sell(portfolioId, {
        symbol: position.symbol,
        quantity,
        price,
        fees,
        notes: notes || undefined,
      });
      setSellResult(response.data);
      setStep('confirm');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Sell failed');
    } finally {
      setSelling(false);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
    if (sellResult) {
      onSellComplete();
    }
  };

  if (!isOpen || !position) return null;

  const maxQty = Math.round(position.quantity * 100) / 100;
  const pctOfPosition = maxQty > 0 ? (quantity / maxQty) * 100 : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg bg-gray-900 border border-slate-dark rounded-xl shadow-2xl p-6 max-h-[90vh] overflow-y-auto">
        {/* Close button */}
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
          aria-label="Close"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <h2 className="text-2xl font-bold text-white mb-4">
          Sell {position.symbol}
        </h2>

        {/* Error */}
        {error && (
          <div className="mb-4 bg-red-900/30 border border-red-500/50 text-red-400 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {step === 'details' && (
          <>
            {/* Position Info */}
            <div className="mb-6 p-4 bg-gray-800/50 rounded-lg border border-slate-dark">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400 text-sm">Current Position</span>
                <span className="text-white font-bold text-lg">
                  {maxQty.toLocaleString()} shares
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">Avg Cost Basis</span>
                <span className="text-slate-300">${position.avg_cost_basis.toFixed(2)}</span>
              </div>
            </div>

            {/* Quantity */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Quantity to Sell
              </label>
              <div className="flex items-center gap-3 mb-2">
                <input
                  type="number"
                  min="0"
                  max={maxQty}
                  step="0.01"
                  value={quantity}
                  onChange={(e) => handleQuantityChange(parseFloat(e.target.value) || 0)}
                  className="flex-1 bg-gray-800 border border-slate-dark text-white px-4 py-3 rounded-lg focus:outline-none focus:border-emerald-500 transition-colors text-lg"
                />
                <span className="text-slate-400 text-sm whitespace-nowrap">
                  ({pctOfPosition.toFixed(1)}% of position)
                </span>
              </div>
              {/* Quick buttons */}
              <div className="flex gap-2">
                {[25, 50, 75, 100].map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => handleQuantityChange(Math.round((maxQty * pct) / 10000) / 100 * 100)}
                    className="flex-1 py-2 text-sm bg-gray-800 hover:bg-gray-700 border border-slate-dark rounded-lg text-slate-300 hover:text-white transition-colors min-h-[44px]"
                  >
                    {pct}%
                  </button>
                ))}
              </div>
            </div>

            {/* Price */}
            <div className="mb-6">
              <label htmlFor="sell-price" className="block text-sm font-medium text-slate-300 mb-2">
                Sell Price ($)
              </label>
              <input
                id="sell-price"
                type="number"
                min="0"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                className="w-full bg-gray-800 border border-slate-dark text-white px-4 py-3 rounded-lg focus:outline-none focus:border-emerald-500 transition-colors text-lg"
              />
            </div>

            {/* Fees */}
            <div className="mb-6">
              <label htmlFor="sell-fees" className="block text-sm font-medium text-slate-300 mb-2">
                Fees ($)
              </label>
              <input
                id="sell-fees"
                type="number"
                min="0"
                step="0.01"
                value={fees}
                onChange={(e) => setFees(parseFloat(e.target.value) || 0)}
                className="w-full bg-gray-800 border border-slate-dark text-white px-4 py-3 rounded-lg focus:outline-none focus:border-emerald-500 transition-colors text-lg"
              />
            </div>

            {/* Notes */}
            <div className="mb-6">
              <label htmlFor="sell-notes" className="block text-sm font-medium text-slate-300 mb-2">
                Notes (optional)
              </label>
              <textarea
                id="sell-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full bg-gray-800 border border-slate-dark text-white px-4 py-3 rounded-lg focus:outline-none focus:border-emerald-500 transition-colors resize-none"
                placeholder="Why are you selling?"
              />
            </div>

            {/* P&L Preview */}
            <div className={`mb-6 p-4 rounded-lg border ${estimatedPnL >= 0 ? 'bg-emerald-900/20 border-emerald-500/30' : 'bg-red-900/20 border-red-500/30'}`}>
              <div className="text-sm text-slate-400 mb-1">Estimated P&L</div>
              <div className={`text-2xl font-bold ${estimatedPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {estimatedPnL >= 0 ? '+' : ''}${estimatedPnL.toFixed(2)}
              </div>
              {quantity > 0 && price > 0 && (
                <div className="text-sm text-slate-500 mt-1">
                  {((estimatedPnL / (position.avg_cost_basis * quantity)) * 100).toFixed(2)}% return
                </div>
              )}
            </div>

            {/* Confirm button */}
            <button
              onClick={() => setStep('confirm')}
              disabled={quantity <= 0 || price <= 0}
              className="w-full py-4 text-lg font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors min-h-[44px]"
            >
              Review Sale
            </button>
          </>
        )}

        {step === 'confirm' && (
          <>
            {!sellResult ? (
              // Pre-sell confirmation summary
              <div className="space-y-4">
                <div className="text-center text-lg text-white font-semibold">
                  Confirm Sale
                </div>
                <div className="bg-gray-800/50 rounded-lg border border-slate-dark p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Symbol</span>
                    <span className="text-white font-bold">{position.symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Quantity</span>
                    <span className="text-white">{quantity.toLocaleString()} shares</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Price</span>
                    <span className="text-white">${price.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Fees</span>
                    <span className="text-white">${fees.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-dark pt-3">
                    <span className="text-slate-400">Proceeds</span>
                    <span className="text-white font-bold">
                      ${(price * quantity - fees).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between border-t border-slate-dark pt-3">
                    <span className="text-slate-400">Est. P&L</span>
                    <span className={`font-bold text-lg ${estimatedPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {estimatedPnL >= 0 ? '+' : ''}${estimatedPnL.toFixed(2)}
                    </span>
                  </div>
                  {notes && (
                    <div className="flex justify-between border-t border-slate-dark pt-3">
                      <span className="text-slate-400">Notes</span>
                      <span className="text-slate-300 text-sm">{notes}</span>
                    </div>
                  )}
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep('details')}
                    className="flex-1 py-4 text-lg font-semibold bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors min-h-[44px]"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={selling}
                    className="flex-1 py-4 text-lg font-semibold bg-red-600 hover:bg-red-500 disabled:opacity-50 rounded-lg transition-colors min-h-[44px]"
                  >
                    {selling ? 'Selling...' : 'Sell'}
                  </button>
                </div>
              </div>
            ) : (
              // Post-sell success
              <div className="space-y-4">
                <div className="text-center">
                  <div className="text-4xl mb-2">✅</div>
                  <div className="text-xl font-bold text-white">Sale Completed</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg border border-slate-dark p-4 space-y-3">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Symbol</span>
                    <span className="text-white font-bold">{sellResult.symbol}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Sold</span>
                    <span className="text-white">{sellResult.quantity_sold.toLocaleString()} shares @ ${sellResult.price.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Proceeds</span>
                    <span className="text-white">${sellResult.proceeds.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-dark pt-3">
                    <span className="text-slate-400">Realized P&L</span>
                    <span className={`font-bold text-lg ${sellResult.realized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {sellResult.realized_pnl >= 0 ? '+' : ''}${sellResult.realized_pnl.toFixed(2)}
                    </span>
                  </div>
                  {sellResult.remaining_quantity > 0 && (
                    <div className="flex justify-between border-t border-slate-dark pt-3">
                      <span className="text-slate-400">Remaining</span>
                      <span className="text-white">{sellResult.remaining_quantity.toLocaleString()} shares</span>
                    </div>
                  )}
                </div>
                <button
                  onClick={handleClose}
                  className="w-full py-4 text-lg font-semibold bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors min-h-[44px]"
                >
                  Done
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
