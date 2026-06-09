import { useEffect, useRef, useState, useMemo } from 'react';
import { createChart, ColorType, LineSeries } from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';

interface SeriesDataPoint {
  time: string;
  value: number;
}

interface NavBenchmarkChartProps {
  portfolioData: SeriesDataPoint[];
  benchmarkData: SeriesDataPoint[] | null;
  benchmarkSymbol: string;
  className?: string;
}

const TIME_RANGES = ['1M', '3M', '6M', '1Y', 'ALL'] as const;
type TimeRange = (typeof TIME_RANGES)[number];
const RANGE_DAYS: Record<TimeRange, number> = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365, 'ALL': 0 };

export function NavBenchmarkChart({
  portfolioData,
  benchmarkData,
  benchmarkSymbol,
  className = '',
}: NavBenchmarkChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('3M');
  const seriesRef = useRef<{ port: any; bm: any }>({ port: null, bm: null });

  const filteredPortfolio = useMemo(() => {
    if (!portfolioData.length || RANGE_DAYS[timeRange] === 0) return portfolioData;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - RANGE_DAYS[timeRange]);
    const cutoffStr = cutoff.toISOString().split('T')[0];
    return portfolioData.filter(d => d.time >= cutoffStr);
  }, [portfolioData, timeRange]);

  const filteredBenchmark = useMemo(() => {
    if (!benchmarkData?.length || RANGE_DAYS[timeRange] === 0) return benchmarkData;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - RANGE_DAYS[timeRange]);
    const cutoffStr = cutoff.toISOString().split('T')[0];
    return benchmarkData.filter(d => d.time >= cutoffStr);
  }, [benchmarkData, timeRange]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#94A3B8',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#1E293B' },
        horzLines: { color: '#1E293B' },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#64748B', labelBackgroundColor: '#334155' },
        horzLine: { color: '#64748B', labelBackgroundColor: '#334155' },
      },
      rightPriceScale: {
        borderColor: '#1E293B',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#1E293B',
        timeVisible: false,
        rightOffset: 5,
        barSpacing: 8,
      },
      handleScroll: { vertTouchDrag: false },
    });

    // Create series and store refs
    const portSeries = chart.addSeries(LineSeries, { color: '#10B981', lineWidth: 2 });
    const bmSeries = chart.addSeries(LineSeries, { color: '#F59E0B', lineWidth: 2, lineStyle: 2 });
    seriesRef.current = { port: portSeries, bm: bmSeries };

    chartRef.current = chart;
    portSeries.setData(portfolioData);
    if (benchmarkData) bmSeries.setData(benchmarkData);
    chart.timeScale().fitContent();

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current!.clientWidth });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // Update data when filtered data changes
  useEffect(() => {
    const { port, bm } = seriesRef.current;
    if (port) port.setData(filteredPortfolio);
    if (bm && benchmarkData) bm.setData(filteredBenchmark);
    else if (bm && !benchmarkData) bm.setData([]);
    if (chartRef.current) chartRef.current.timeScale().fitContent();
  }, [filteredPortfolio, filteredBenchmark, benchmarkData]);

  // Calculate stats
  const stats = useMemo(() => {
    if (portfolioData.length < 2) return null;
    const first = portfolioData[0].value;
    const last = portfolioData[portfolioData.length - 1].value;
    const change = ((last - first) / first) * 100;
    return {
      start: first.toFixed(2),
      end: last.toFixed(2),
      change: change.toFixed(2),
      positive: change >= 0,
    };
  }, [portfolioData]);

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-white">Portfolio Performance</h2>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-emerald-500"></span>
            <span className="text-slate-400">Portfolio</span>
          </div>
          {benchmarkData && benchmarkData.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-amber-500 border-dashed border-b"></span>
              <span className="text-slate-400">{benchmarkSymbol}</span>
            </div>
          )}
        </div>
      </div>

      {/* Time range selector */}
      <div className="flex gap-1">
        {TIME_RANGES.map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-3 py-1 text-xs font-medium transition-colors ${
              timeRange === range
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-slate-500 hover:text-white hover:bg-slate-800'
            }`}
          >
            {range}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div ref={chartContainerRef} className="w-full rounded-none" style={{ minHeight: 300 }} />

      {/* Stats */}
      {stats && (
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <span className="text-slate-400">Start: <span className="text-white">{stats.start}</span></span>
          <span className="text-slate-400">End: <span className="text-white">{stats.end}</span></span>
          <span className={stats.positive ? 'text-emerald-400' : 'text-red-400'}>
            {stats.positive ? '▲' : '▼'} {Math.abs(parseFloat(stats.change)).toFixed(2)}%
          </span>
        </div>
      )}
    </div>
  );
}
