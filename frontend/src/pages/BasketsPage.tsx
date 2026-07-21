/**
 * Baskets page — full basket management with analytics, create/edit/delete modals.
 *
 * Renders N basket cards (not hardcoded 3). Each card shows:
 * - Name, color swatch
 * - Target vs actual allocation progress bar
 * - NAV, P&L, position count
 * - Sector breakdown
 * - Edit / Delete actions
 *
 * Includes "New Basket" modal and delete confirmation.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Basket, BasketCreate, BasketUpdate } from '@/services/api'
import { basketsApi, type BasketAnalyticsData } from '@/services/api'
import { BasketAllocationGroup } from '@/components/BasketAllocation'
import { useBasketStore } from '@/store/basketStore'

/* ── Target allocation summary ──────────────────────────────────────── */

function TargetSummary({ baskets }: { baskets: Basket[] }) {
  const total = useMemo(() => baskets.reduce((sum, b) => sum + parseFloat(b.target_allocation), 0), [baskets])
  const isOk = Math.abs(total - 100) < 0.01
  const isClose = Math.abs(total - 100) < 5

  return (
    <div className="mb-6 flex items-center justify-between rounded border border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="font-medium text-sm text-text">Total Target</span>
        <span
          className={`font-mono-financial font-semibold text-base ${isOk ? 'text-positive' : isClose ? 'text-warning' : 'text-negative'}`}
        >
          {total.toFixed(1)}%
        </span>
      </div>
      {!isOk && (
        <span className={`text-xs ${isClose ? 'text-warning' : 'text-negative'}`}>
          {total > 100 ? 'Over-' : 'Under-'}allocated by {Math.abs(total - 100).toFixed(1)}%
        </span>
      )}
      {isOk && <span className="text-positive text-xs">✓ Balanced</span>}
    </div>
  )
}

/* ── Sector breakdown ───────────────────────────────────────────────── */

function SectorBreakdown({ analytics }: { analytics: BasketAnalyticsData }) {
  const sectors = Object.entries(analytics.allocation_by_sector)
    .sort((a, b) => b[1] - a[1])

  if (sectors.length === 0) return null

  return (
    <div className="mt-3 space-y-1">
      {sectors.map(([sector, pct]) => (
        <div key={sector} className="flex items-center justify-between text-xs">
          <span className="text-text-dim">{sector}</span>
          <span className="font-mono-financial text-text">{(pct * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  )
}

/* ── Basket card ────────────────────────────────────────────────────── */

function BasketCard({
  basket,
  analytics,
  totalNav,
  onEdit,
  onDelete,
}: {
  basket: Basket
  analytics: BasketAnalyticsData | null
  totalNav: number
  onEdit: () => void
  onDelete: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="rounded border border-border bg-surface p-4 transition hover:border-border/80"
    >
      <BasketAllocationGroup
        baskets={[basket]}
        analyticsMap={analytics ? new Map([[basket.id, analytics]]) : new Map()}
        totalPortfolioNav={totalNav}
        showActions={true}
        onEdit={() => onEdit()}
        onDelete={() => onDelete()}
      />
      {analytics && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-text-dim text-xs transition hover:text-text"
        >
          {expanded ? '▲ Hide' : '▼ Show'} sector breakdown
        </button>
      )}
      {expanded && analytics && <SectorBreakdown analytics={analytics} />}
    </div>
  )
}

/* ── New Basket Modal ───────────────────────────────────────────────── */

function NewBasketModal({
  onClose,
  onCreate,
  existingNames,
}: {
  onClose: () => void
  onCreate: (data: BasketCreate) => void
  existingNames: string[]
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [target, setTarget] = useState(10)
  const [color, setColor] = useState('#58a6ff')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const defaultColors = ['#58a6ff', '#bc8cff', '#f0883e', '#3fb950', '#f778ba', '#d29922', '#79c0ff']

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) {
      setError('Name is required')
      return
    }
    if (existingNames.includes(name.trim())) {
      setError('A basket with this name already exists')
      return
    }

    setSaving(true)
    try {
      onCreate({
        name: name.trim(),
        description: description.trim() || null,
        target_allocation: target,
        color,
      })
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create basket')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-md rounded border border-border bg-surface p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 font-semibold text-text">New Basket</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Name <span className="text-negative">*</span></span>
            <input
              type="text"
              required
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
              placeholder="e.g. Cash Reserve"
            />
          </label>

          {/* Description */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Description</span>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
              placeholder="e.g. Money market + T-bills"
            />
          </label>

          {/* Target allocation */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Target Allocation (%)</span>
            <input
              type="number"
              min={1}
              max={100}
              step={1}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
            />
          </label>

          {/* Color picker */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Color</span>
            <div className="flex flex-wrap gap-2">
              {defaultColors.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded border-2 transition ${color === c ? 'border-white scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
              <label className="relative flex h-7 w-7 cursor-pointer items-center justify-center rounded border-2 border-border bg-bg">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="absolute inset-0 h-full w-full opacity-0"
                />
                <span className="h-4 w-4 rounded-full" style={{ backgroundColor: color }} />
              </label>
            </div>
          </label>

          {/* Error */}
          {error && <p className="text-negative text-xs">{error}</p>}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-border px-3 py-1.5 text-sm text-text-dim transition hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded bg-accent px-3 py-1.5 font-medium text-bg text-sm transition disabled:opacity-50"
            >
              {saving ? 'Creating…' : 'Create Basket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Edit Basket Modal ──────────────────────────────────────────────── */

function EditBasketModal({
  basket,
  onClose,
  onUpdate,
  existingNames,
}: {
  basket: Basket
  onClose: () => void
  onUpdate: (id: string, data: BasketUpdate) => void
  existingNames: string[]
}) {
  const [name, setName] = useState(basket.name)
  const [description, setDescription] = useState(basket.description || '')
  const [target, setTarget] = useState(parseFloat(basket.target_allocation))
  const [color, setColor] = useState(basket.color)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const defaultColors = ['#58a6ff', '#bc8cff', '#f0883e', '#3fb950', '#f778ba', '#d29922', '#79c0ff']

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) {
      setError('Name is required')
      return
    }
    if (existingNames.includes(name.trim()) && name.trim() !== basket.name) {
      setError('A basket with this name already exists')
      return
    }

    setSaving(true)
    try {
      onUpdate(basket.id, {
        name: name.trim(),
        description: description.trim() || null,
        target_allocation: target,
        color,
      })
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update basket')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-md rounded border border-border bg-surface p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 font-semibold text-text">Edit Basket</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Name <span className="text-negative">*</span></span>
            <input
              type="text"
              required
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
            />
          </label>

          {/* Description */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Description</span>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
            />
          </label>

          {/* Target allocation */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Target Allocation (%)</span>
            <input
              type="number"
              min={1}
              max={100}
              step={1}
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm text-text outline-none transition focus:border-accent"
            />
          </label>

          {/* Color picker */}
          <label className="block">
            <span className="mb-1 block text-text-dim text-xs">Color</span>
            <div className="flex flex-wrap gap-2">
              {defaultColors.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded border-2 transition ${color === c ? 'border-white scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                />
              ))}
              <label className="relative flex h-7 w-7 cursor-pointer items-center justify-center rounded border-2 border-border bg-bg">
                <input
                  type="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  className="absolute inset-0 h-full w-full opacity-0"
                />
                <span className="h-4 w-4 rounded-full" style={{ backgroundColor: color }} />
              </label>
            </div>
          </label>

          {/* Error */}
          {error && <p className="text-negative text-xs">{error}</p>}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-border px-3 py-1.5 text-sm text-text-dim transition hover:text-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded bg-accent px-3 py-1.5 font-medium text-bg text-sm transition disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Delete confirmation dialog ─────────────────────────────────────── */

function DeleteConfirm({
  basket,
  onClose,
  onConfirm,
}: {
  basket: Basket
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded border border-border bg-surface p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-2 font-semibold text-text">Delete Basket</h2>
        <p className="mb-4 text-sm text-text-dim">
          Are you sure you want to delete{' '}
          <span className="font-medium text-text">{basket.name}</span>?
          {' '}Positions in this basket will become unassigned.
        </p>
        {basket.is_preset && (
          <p className="mb-4 rounded bg-warning/10 px-3 py-2 text-warning text-xs">
            ⚠ This is a preset basket. Deleting it is permanent.
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-border px-3 py-1.5 text-sm text-text-dim transition hover:text-text"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded bg-negative px-3 py-1.5 font-medium text-bg text-sm transition"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Loading skeleton ───────────────────────────────────────────────── */

function SkeletonCard() {
  return (
    <div className="rounded border border-border bg-surface p-4 animate-pulse">
      <div className="h-4 w-24 rounded bg-border mb-3" />
      <div className="h-3 w-full rounded bg-border" />
      <div className="mt-3 flex gap-4">
        <div className="h-3 w-16 rounded bg-border" />
        <div className="h-3 w-16 rounded bg-border" />
      </div>
    </div>
  )
}

/* ── Baskets page ───────────────────────────────────────────────────── */

export default function BasketsPage() {
  const { baskets, isLoading, init, create, update, remove } = useBasketStore()

  // Analytics state: Map<basket_id, BasketAnalyticsData | null>
  const [analyticsMap, setAnalyticsMap] = useState<Map<string, BasketAnalyticsData | null>>(new Map())
  const [analyticsLoading, setAnalyticsLoading] = useState(true)

  // Modal state
  const [showNew, setShowNew] = useState(false)
  const [editingBasket, setEditingBasket] = useState<Basket | null>(null)
  const [deletingBasket, setDeletingBasket] = useState<Basket | null>(null)

  // Fetch baskets on mount
  useEffect(() => {
    init()
  }, [init])

  // Fetch analytics for each basket once the list is loaded
  useEffect(() => {
    if (!baskets.length) return
    setAnalyticsLoading(true)
    Promise.all(
      baskets.map(async (b) => {
        try {
          const data = await basketsApi.analytics(b.id) as BasketAnalyticsData
          return [b.id, data] as const
        } catch {
          return [b.id, null] as const
        }
      }),
    ).then((results) => {
      setAnalyticsMap(new Map(results))
      setAnalyticsLoading(false)
    })
  }, [baskets])

  const totalNav = useMemo(
    () => Array.from(analyticsMap.values()).reduce((sum, a) => sum + (a?.nav ?? 0), 0),
    [analyticsMap],
  )

  const existingNames = useMemo(() => baskets.map((b) => b.name), [baskets])

  const handleCreate = useCallback(
    (data: BasketCreate) => {
      create(data)
    },
    [create],
  )

  const handleUpdate = useCallback(
    (id: string, data: BasketUpdate) => {
      update(id, data)
    },
    [update],
  )

  const handleDelete = useCallback(() => {
    if (!deletingBasket) return
    remove(deletingBasket.id)
    setDeletingBasket(null)
  }, [deletingBasket, remove])

  const allLoading = isLoading || analyticsLoading

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-xl text-text">Baskets</h1>
          <p className="mt-1 text-text-dim text-sm">
            Manage your allocation baskets. Create, edit, or delete baskets to organize your portfolio.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowNew(true)}
          className="rounded bg-accent px-4 py-2 font-medium text-bg text-sm transition hover:brightness-110"
        >
          + New Basket
        </button>
      </div>

      {/* Target summary */}
      <TargetSummary baskets={baskets} />

      {/* Basket cards */}
      {allLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            {baskets.map((basket) => (
              <BasketCard
                key={basket.id}
                basket={basket}
                analytics={analyticsMap.get(basket.id) ?? null}
                totalNav={totalNav}
                onEdit={() => setEditingBasket(basket)}
                onDelete={() => setDeletingBasket(basket)}
              />
            ))}
          </div>

          {/* Empty state */}
          {baskets.length === 0 && (
            <div className="mt-8 rounded border border-border bg-surface p-8 text-center">
              <p className="text-text-dim">No baskets yet.</p>
              <p className="mt-1 text-text-dim text-sm">
                Create your first basket to start organizing your portfolio.
              </p>
            </div>
          )}
        </>
      )}

      {/* Total portfolio summary */}
      {baskets.length > 0 && !allLoading && (
        <div className="mt-6 rounded border border-border bg-surface p-4">
          <h3 className="mb-2 font-medium text-sm text-text">Portfolio Summary</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <span className="text-text-dim text-xs">Total Value</span>
              <p className="font-mono-financial font-semibold text-text">
                ${totalNav.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </p>
            </div>
            <div>
              <span className="text-text-dim text-xs">Baskets</span>
              <p className="font-mono-financial font-semibold text-text">{baskets.length}</p>
            </div>
            <div>
              <span className="text-text-dim text-xs">Total Positions</span>
              <p className="font-mono-financial font-semibold text-text">
                {Array.from(analyticsMap.values()).reduce((sum, a) => sum + (a?.position_count ?? 0), 0)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Modals ──────────────────────────────────────────────────── */}
      {showNew && (
        <NewBasketModal
          onClose={() => setShowNew(false)}
          onCreate={handleCreate}
          existingNames={existingNames}
        />
      )}

      {editingBasket && (
        <EditBasketModal
          basket={editingBasket}
          onClose={() => setEditingBasket(null)}
          onUpdate={handleUpdate}
          existingNames={existingNames.filter((_, i) => baskets[i]?.id !== editingBasket.id)}
        />
      )}

      {deletingBasket && (
        <DeleteConfirm
          basket={deletingBasket}
          onClose={() => setDeletingBasket(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}
