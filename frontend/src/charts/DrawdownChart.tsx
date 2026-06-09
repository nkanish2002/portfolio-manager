import { useEffect, useRef, useMemo } from 'react';
import { createChart, ColorType, HistogramSeries } from 'lightweight-charts';
import type { IChartApi } from 'lightweight-charts';

interface DrawdownPoint {
  time: string;
  value: number;
}

interface DrawdownChartProps {
  data: DrawdownPoint[];
  className?: string;
}

export function DrawdownChart({ data, className = '' }: DrawdownChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<any>(null);

  const maxDrawdown = useMemo(() => {
    if (!data.length) return 0;
    return Math.min(...data.map(d => d.value));
  }, [data]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 250,
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#94A3B8',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#1E293B' },
        horzLines: { color: '#1E293B' },
      },
      rightPriceScale: {
        borderColor: '#1E293B',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#1E293B',
        timeVisible: false,
        rightOffset: 5,
      },
      handleScroll: { vertTouchDrag: false },
    });

    const series = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'percent', minMove: 0.01 },
      priceScaleId: 'drawdown',
    });

    chart.priceScale('drawdown').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    seriesRef.current = series;
    series.setData(data);
    chart.timeScale().fitContent();

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current!.clientWidth });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (seriesRef.current) {
      seriesRef.current.setData(data);
    }
    if (chartRef.current) chartRef.current.timeScale().fitContent();
  }, [data]);

  return (
    <div className={`space-y-3 ${className}`}>
      <h2 className="text-lg font-semibold text-white">Drawdown Analysis</h2>
      <div ref={chartContainerRef} className="w-full rounded-none" style={{ minHeight: 250 }} />
      {data.length > 0 && (
        <div className="flex items-center gap-4 text-sm">
          <span className="text-slate-400">Max Drawdown: <span className="text-red-400 font-semibold">{maxDrawdown.toFixed(2)}%</span></span>
          <span className="text-slate-400">Points: <span className="text-white">{data.length}</span></span>
        </div>
      )}
    </div>
  );
}
