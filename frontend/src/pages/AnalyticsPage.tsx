import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router';
import { usePortfolioStore, usePositionStore } from '../store';
import { chartService } from '../services/api';
import type {
  NavChartData,
  DrawdownData,
  MonthlyReturnsData,
  BenchmarkComparisonData,
  RiskReportData,
} from '../services/api';
import { NavBenchmarkChart } from '../charts/NavBenchmarkChart';
import { DrawdownChart as DrawdownChartComp } from '../charts/DrawdownChart';
import { MonthlyReturnsChart } from '../charts/MonthlyReturnsChart';
import { BenchmarkComparison } from '../charts/BenchmarkComparison';
import { RiskMetricsWidget } from '../charts/RiskMetricsWidget';

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="animate-spin rounded-none h-8 w-8 border-b-2 border-white"></div>
    </div>
  );
}

export function AnalyticsPage() {
  const { portfolioId: routeId } = useParams<{ portfolioId: string }>();
  const { currentPortfolio, setCurrentPortfolio, clearCurrentPortfolio } = usePortfolioStore();
  const { fetchPositions } = usePositionStore();
  const [navData, setNavData] = useState<NavChartData | null>(null);
  const [drawdownData, setDrawdownData] = useState<DrawdownData | null>(null);
  const [monthlyReturns, setMonthlyReturns] = useState<MonthlyReturnsData | null>(null);
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkComparisonData | null>(null);
  const [riskReport, setRiskReport] = useState<RiskReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const portfolioId = routeId || currentPortfolio?.id;

  const fetchData = useCallback(async (pid: string) => {
    setLoading(true);
    setError(null);

    // Ensure currentPortfolio is set
    if (!currentPortfolio || currentPortfolio.id !== pid) {
      await setCurrentPortfolio(pid);
    }

    try {
      const [nav, dd, mr, bm, risk] = await Promise.all([
        chartService.navHistory(pid, 'SPY').catch(() => ({ data: null })),
        chartService.drawdown(pid).catch(() => ({ data: null })),
        chartService.monthlyReturns(pid).catch(() => ({ data: null })),
        chartService.benchmarkComparison(pid, 'SPY').catch(() => ({ data: null })),
        chartService.riskReport(pid).catch(() => ({ data: null })),
      ]);

      // Also load positions
      await fetchPositions(pid).catch(() => {});

      if (nav.data) setNavData(nav.data);
      if (dd.data) setDrawdownData(dd.data);
      if (mr.data) setMonthlyReturns(mr.data);
      if (bm.data) setBenchmarkData(bm.data);
      if (risk.data) setRiskReport(risk.data);
    } catch (err) {
      console.error('Failed to fetch analytics data:', err);
      setError('Failed to load analytics data. Make sure your portfolio has transaction history.');
    } finally {
      setLoading(false);
    }
  }, [currentPortfolio, setCurrentPortfolio, fetchPositions]);

  useEffect(() => {
    if (portfolioId) {
      fetchData(portfolioId);
    } else {
      setLoading(false);
    }
    return () => clearCurrentPortfolio();
  }, [portfolioId, currentPortfolio]);

  // Format drawdown data for TradingView chart
  const drawdownChartData = drawdownData?.dates.map((date, i) => ({
    time: date,
    value: drawdownData.drawdown[i] ?? 0,
  })) ?? [];

  // Format monthly returns data
  const mrYears = monthlyReturns?.years ?? [];
  const mrMonths = monthlyReturns?.months ?? [];
  const mrValues = monthlyReturns?.values ?? [];

  // Format benchmark data for overlay chart
  const benchmarkOverlayData = benchmarkData?.dates.map((date, i) => ({
    time: date,
    value: benchmarkData.benchmark[i] ?? 0,
  })) ?? (navData?.benchmark ? navData.benchmark.map((d, i) => ({
    time: navData.portfolio[i]?.time,
    value: d.value,
  })) : []);

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Analytics</h1>
        {portfolioId && (
          <button
            onClick={() => fetchData(portfolioId)}
            className="inline-flex items-center gap-2 text-sm px-3 py-2 bg-slate-800 text-white hover:bg-slate-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-900/30 border border-slate-800 text-white p-3 sm:p-4 rounded-none">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}

      {!portfolioId && !error && (
        <div className="bg-gray-900/50 border border-slate-800 rounded-none p-6 sm:p-8 text-center">
          <p className="text-slate-400">Select a portfolio from the dropdown above to view analytics.</p>
        </div>
      )}

      {/* NAV + Benchmark Chart */}
      {navData?.portfolio?.length ? (
        <div className="bg-gray-900/50 border border-slate-800 rounded-none p-4 sm:p-6">
          <NavBenchmarkChart
            portfolioData={navData.portfolio}
            benchmarkData={navData.benchmark || null}
            benchmarkSymbol={navData.benchmark_symbol}
          />
        </div>
      ) : null}

      {/* Drawdown + Monthly Returns row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {drawdownData?.dates?.length ? (
          <div className="bg-gray-900/50 border border-slate-800 rounded-none p-4 sm:p-6">
            <DrawdownChartComp data={drawdownChartData} />
          </div>
        ) : null}

        {mrYears?.length ? (
          <div className="bg-gray-900/50 border border-slate-800 rounded-none p-4 sm:p-6">
            <MonthlyReturnsChart
              years={mrYears}
              months={mrMonths}
              values={mrValues}
            />
          </div>
        ) : null}
      </div>

      {/* Benchmark Comparison */}
      {benchmarkData?.dates?.length ? (
        <div className="bg-gray-900/50 border border-slate-800 rounded-none p-4 sm:p-6">
          <BenchmarkComparison
            portfolioData={benchmarkData.dates.map((date, i) => ({
              time: date,
              value: benchmarkData.portfolio[i] ?? 0,
            }))}
            benchmarkData={benchmarkOverlayData.length ? benchmarkOverlayData : null}
            benchmarkSymbol={benchmarkData.benchmark_symbol || 'SPY'}
            excessReturn={benchmarkData.excess_return}
            trackingError={benchmarkData.tracking_error}
            informationRatio={benchmarkData.information_ratio}
            correlation={benchmarkData.correlation}
          />
        </div>
      ) : null}

      {/* Risk Metrics */}
      {riskReport && (
        <div className="bg-gray-900/50 border border-slate-800 rounded-none p-4 sm:p-6">
          <RiskMetricsWidget
            sharpeRatio={riskReport.sharpe_ratio}
            sortinoRatio={riskReport.sortino_ratio}
            maxDrawdown={riskReport.max_drawdown}
            valueAtRisk={riskReport.var_95}
            beta={riskReport.beta}
            alpha={riskReport.alpha}
            treynorRatio={riskReport.treynor_ratio}
            calmarRatio={riskReport.calmar_ratio}
            ulcerIndex={riskReport.ulcer_index}
          />
        </div>
      )}

      {/* Empty state */}
      {!navData?.portfolio?.length && !drawdownData?.dates?.length && !mrYears?.length && !benchmarkData?.dates?.length && !riskReport && !loading && portfolioId && (
        <div className="bg-gray-900/50 border border-slate-800 rounded-none p-6 sm:p-8 text-center">
          <svg className="w-16 h-16 mx-auto text-slate-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-slate-400 mb-2">No analytics data available</p>
          <p className="text-slate-500 text-sm">Add some transactions to your portfolio to see analytics.</p>
        </div>
      )}
    </div>
  );
}
