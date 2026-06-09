import { useEffect, useRef, useMemo } from 'react';
import { createChart, ColorType, LineSeries } from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';

interface BenchmarkComparisonProps {
  portfolioData: { time: string; value: number }[];
  benchmarkData: { time: string; value: number }[] | null;
  benchmarkSymbol: string;
  excessReturn: number;
  trackingError: number;
  informationRatio: number;
  correlation: number;
  className?: string;
}

function MetricCard({ label, value, subtext, color = 'white' }: {
  label: string;
  value: string;
  subtext?: string;
  color?: string;
}) {
  return (
    <div className="bg-slate-900/80 border border-slate-700 rounded-none p-3 sm:p-4">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-lg sm:text-xl font-bold ${color}`}>{value}</div>
      {subtext && <div className="text-xs text-slate-500 mt-1">{subtext}</div>}
    </div>
  );
}

export function BenchmarkComparison({
  portfolioData,
  benchmarkData,
  benchmarkSymbol,
  excessReturn,
  trackingError,
  informationRatio,
  correlation,
  className = '',
}: BenchmarkComparisonProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<{ port: any; bm: any }>({ port: null, bm: null });

  const portfolioChange = useMemo(() => {
    if (!portfolioData.length) return 0;
    return ((portfolioData[portfolioData.length - 1].value - portfolioData[0].value) / portfolioData[0].value) * 100;
  }, [portfolioData]);

  const benchmarkChange = useMemo(() => {
    if (!benchmarkData?.length) return null;
    return ((benchmarkData[benchmarkData.length - 1].value - benchmarkData[0].value) / benchmarkData[0].value) * 100;
  }, [benchmarkData]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 200,
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#94A3B8',
        fontSize: 11,
      },
      grid: { vertLines: { color: '#1E293B' }, horzLines: { color: '#1E293B' } },
      rightPriceScale: { borderColor: '#1E293B', scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: '#1E293B', timeVisible: false, rightOffset: 3 },
    });

    const portSeries = chart.addSeries(LineSeries, { color: '#10B981', lineWidth: 2 });
    const bmSeries = chart.addSeries(LineSeries, { color: '#F59E0B', lineWidth: 2, lineStyle: 2 });
    seriesRef.current = { port: portSeries, bm: bmSeries };

    chartRef.current = chart;
    portSeries.setData(portfolioData);
    if (benchmarkData) bmSeries.setData(benchmarkData);
    chart.timeScale().fitContent();

    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current!.clientWidth });
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    const { port, bm } = seriesRef.current;
    if (port) port.setData(portfolioData);
    if (bm && benchmarkData) bm.setData(benchmarkData);
    else if (bm) bm.setData([]);
    chartRef.current.timeScale().fitContent();
  }, [portfolioData, benchmarkData]);

  const isPositive = excessReturn >= 0;
  const corrColor = Math.abs(correlation) > 0.7 ? 'text-emerald-400' : Math.abs(correlation) > 0.4 ? 'text-amber-400' : 'text-red-400';

  return (
    <div className={`space-y-4 ${className}`}>
      <h2 className="text-lg font-semibold text-white">Benchmark Comparison</h2>
      <div ref={chartContainerRef} className="w-full rounded-none" style={{ minHeight: 200 }} />
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-emerald-500"></span>
          <span className="text-slate-400">Portfolio ({portfolioChange >= 0 ? '+' : ''}{portfolioChange.toFixed(1)}%)</span>
        </div>
        {benchmarkData && benchmarkData.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-amber-500 border-dashed border-b"></span>
            <span className="text-slate-400">{benchmarkSymbol} ({(benchmarkChange ?? 0) >= 0 ? '+' : ''}{(benchmarkChange ?? 0).toFixed(1)}%)</span>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
        <MetricCard label="Excess Return" value={`${isPositive ? '+' : ''}${excessReturn.toFixed(2)}%`} color={isPositive ? 'text-emerald-400' : 'text-red-400'} />
        <MetricCard label="Tracking Error" value={`${trackingError.toFixed(2)}%`} subtext="Annualized" />
        <MetricCard label="Information Ratio" value={informationRatio.toFixed(2)} subtext="Excess / TE" />
        <MetricCard label="Correlation" value={correlation.toFixed(3)} color={corrColor} subtext="vs SPY" />
      </div>
    </div>
  );
}
