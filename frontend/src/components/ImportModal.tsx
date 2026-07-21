/**
 * Import Modal — PDF upload for statement import + report generation.
 *
 * Provides two actions:
 *  1. Upload a Schwab statement PDF → parsed into positions
 *  2. Generate a standalone HTML report → downloaded as file
 *
 * Controlled via ``isOpen``, ``onClose`` props. Uses the selected portfolio
 * from the global portfolioStore.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { importApi } from '@/services/api'
import { usePortfolioStore } from '@/store/portfolioStore'

/* ── Import result summary ─────────────────────────────────────────── */

function ImportResult({ created, updated, total }: { created: string[]; updated: string[]; total: number }) {
  return (
    <div className="mt-4 rounded border border-positive/30 bg-positive/5 p-3">
      <p className="font-semibold text-positive text-sm">Import complete</p>
      <p className="text-text-dim text-xs mt-1">
        {total} holding{total !== 1 ? 's' : ''} processed
        {created.length > 0 && <> — <span className="text-positive">{created.length} new</span></>}
        {updated.length > 0 && <> · <span className="text-text">{updated.length} updated</span></>}
      </p>
      {(created.length > 0 || updated.length > 0) && (
        <div className="mt-2 flex flex-wrap gap-1">
          {created.map((s) => (
            <span key={s} className="rounded bg-positive/10 px-1.5 py-0.5 text-positive text-xs">
              {s}
            </span>
          ))}
          {updated.map((s) => (
            <span key={s} className="rounded bg-accent/10 px-1.5 py-0.5 text-accent text-xs">
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Error display ─────────────────────────────────────────────────── */

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mt-4 rounded border border-negative/30 bg-negative/5 p-3">
      <p className="font-semibold text-negative text-sm">Import failed</p>
      <p className="text-text-dim text-xs mt-1">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="mt-2 text-xs text-text-dim underline hover:text-text"
      >
        Dismiss
      </button>
    </div>
  )
}

/* ── Modal ─────────────────────────────────────────────────────────── */

interface Props {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function ImportModal({ isOpen, onClose, onSuccess }: Props) {
  const { portfolios, selectedId } = usePortfolioStore()
  const [activeTab, setActiveTab] = useState<'import' | 'report'>('import')
  const [portfolioId, setPortfolioId] = useState(selectedId ?? '')
  const [file, setFile] = useState<File | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<{ created: string[]; updated: string[]; total: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reportPeriod, setReportPeriod] = useState('1y')
  const [reportBenchmark, setReportBenchmark] = useState('SPY')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Sync portfolio when selection changes
  useEffect(() => {
    if (selectedId) setPortfolioId(selectedId)
  }, [selectedId])

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setFile(null)
      setResult(null)
      setError(null)
      if (selectedId) setPortfolioId(selectedId)
    }
  }, [isOpen, selectedId])

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  /* ── Handlers ─────────────────────────────────────────────────── */

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const dropped = e.dataTransfer.files[0]
      if (dropped && dropped.type === 'application/pdf') {
        setFile(dropped)
      }
    },
    [],
  )

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = e.target.files?.[0]
    if (chosen) setFile(chosen)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!file || !portfolioId) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await importApi.uploadStatement(portfolioId, file)
      setResult({ created: data.created, updated: data.updated, total: data.holdings_imported })
      onSuccess()
    } catch (err: unknown) {
      const msg =
        err instanceof Error && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Upload failed'
          : 'Upload failed'
      setError(typeof msg === 'string' ? msg : String(msg))
    } finally {
      setIsLoading(false)
    }
  }, [file, portfolioId, onSuccess])

  const handleReport = useCallback(async () => {
    if (!portfolioId) return
    setIsLoading(true)
    try {
      const response = await importApi.generateReport(portfolioId, {
        period: reportPeriod,
        benchmark: reportBenchmark,
      })
      // Trigger download
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/html' }))
      const link = document.createElement('a')
      link.href = url
      const filename = response.headers['content-disposition']
        ?.match(/filename="?(.+?)"?$/i)?.[1]
        ?? 'portfolio_report.html'
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Report generation failed'
      setError(typeof msg === 'string' ? msg : String(msg))
    } finally {
      setIsLoading(false)
    }
  }, [portfolioId, reportPeriod, reportBenchmark])

  /* ── Render ───────────────────────────────────────────────────── */

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/70"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-lg rounded border border-border bg-surface p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-text">Import & Reports</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-text-dim transition hover:text-text"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="mb-4 flex gap-2 border-b border-border">
          <button
            type="button"
            onClick={() => setActiveTab('import')}
            className={`pb-2 text-sm transition ${
              activeTab === 'import'
                ? 'border-b-2 border-accent text-accent'
                : 'text-text-dim hover:text-text'
            }`}
          >
            Upload Statement
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('report')}
            className={`pb-2 text-sm transition ${
              activeTab === 'report'
                ? 'border-b-2 border-accent text-accent'
                : 'text-text-dim hover:text-text'
            }`}
          >
            Generate Report
          </button>
        </div>

        {/* ── Import tab ─────────────────────────────────────────── */}
        {activeTab === 'import' && (
          <div>
            {/* Portfolio selector */}
            <label className="mb-1 block text-text-dim text-xs">Portfolio</label>
            <select
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="mb-4 w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            >
              {!portfolioId && <option value="">Select a portfolio…</option>}
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            {/* Drop zone */}
            {!file ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragging(true)
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`cursor-pointer rounded border-2 border-dashed p-8 text-center transition ${
                  isDragging
                    ? 'border-accent bg-accent/5'
                    : 'border-border text-text-dim hover:border-accent/50'
                }`}
              >
                <p className="text-sm">Drop a Schwab PDF statement here</p>
                <p className="mt-1 text-text-dim text-xs">or click to browse</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>
            ) : (
              <div className="mb-4 flex items-center justify-between rounded border border-border bg-bg p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm text-text">{file.name}</p>
                  <p className="text-text-dim text-xs">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="ml-2 text-text-dim text-xs underline hover:text-negative"
                >
                  Remove
                </button>
              </div>
            )}

            {/* Submit */}
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!file || !portfolioId || isLoading}
              className="mt-4 w-full rounded bg-accent px-4 py-2 font-medium text-sm text-black disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isLoading ? 'Importing…' : 'Import Holdings'}
            </button>

            {/* Result / Error */}
            {result && <ImportResult created={result.created} updated={result.updated} total={result.total} />}
            {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
          </div>
        )}

        {/* ── Report tab ─────────────────────────────────────────── */}
        {activeTab === 'report' && (
          <div>
            {/* Portfolio selector */}
            <label className="mb-1 block text-text-dim text-xs">Portfolio</label>
            <select
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="mb-4 w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            >
              {!portfolioId && <option value="">Select a portfolio…</option>}
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            {/* Period */}
            <label className="mb-1 block text-text-dim text-xs">History Period</label>
            <div className="mb-4 flex gap-2">
              {['1m', '3m', '6m', '1y', '2y'].map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setReportPeriod(p)}
                  className={`rounded border px-3 py-1 text-xs transition ${
                    reportPeriod === p
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border text-text-dim hover:border-accent/50'
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Benchmark */}
            <label className="mb-1 block text-text-dim text-xs">Benchmark</label>
            <select
              value={reportBenchmark}
              onChange={(e) => setReportBenchmark(e.target.value)}
              className="mb-4 w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none focus:border-accent"
            >
              <option value="SPY">SPY (S&P 500)</option>
              <option value="QQQ">QQQ (Nasdaq-100)</option>
              <option value="DIA">DIA (Dow Jones)</option>
              <option value="VTI">VTI (Total Market)</option>
            </select>

            {/* Generate */}
            <button
              type="button"
              onClick={handleReport}
              disabled={!portfolioId || isLoading}
              className="mt-2 w-full rounded bg-accent px-4 py-2 font-medium text-sm text-black disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isLoading ? 'Generating…' : 'Download HTML Report'}
            </button>

            {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
          </div>
        )}
      </div>
    </div>
  )
}
