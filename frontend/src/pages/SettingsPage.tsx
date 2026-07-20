/**
 * Settings page — profile settings and basket management.
 */

import { type FormEvent, useEffect, useState } from 'react'
import { authApi, type Basket, type BasketCreate, basketsApi } from '@/services/api'
import { useAuthStore } from '@/store/authStore'

/* ── Profile settings ───────────────────────────────────────────────── */

function ProfileSettings() {
  const { user } = useAuthStore()
  const [name, setName] = useState(user?.display_name || '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await authApi.updateMe({ display_name: name || null })
      setMessage('Profile updated')
    } catch {
      setMessage('Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSave} className="space-y-4">
      <label className="block">
        <span className="mb-1 block font-medium text-sm text-text-dim">Display name</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded border border-border bg-bg px-3 py-2 text-text outline-none transition focus:border-accent"
          placeholder="Your name"
        />
      </label>
      <label className="block">
        <span className="mb-1 block font-medium text-sm text-text-dim">Email</span>
        <input
          type="email"
          value={user?.email || ''}
          disabled
          className="w-full rounded border border-border bg-bg/50 px-3 py-2 text-text-dim outline-none"
        />
      </label>
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded bg-accent px-4 py-2 font-medium text-bg text-sm transition disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
        {message && (
          <p className={`text-sm ${message.includes('Failed') ? 'text-negative' : 'text-positive'}`}>{message}</p>
        )}
      </div>
    </form>
  )
}

/* ── Basket management ──────────────────────────────────────────────── */

function BasketManager() {
  const [baskets, setBaskets] = useState<Basket[]>([])
  const [loading, setLoading] = useState(true)

  // New basket form
  const [name, setName] = useState('')
  const [target, setTarget] = useState(40)
  const [color, setColor] = useState('#58a6ff')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    basketsApi
      .list()
      .then(setBaskets)
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    try {
      const basket: BasketCreate = { name: name.trim(), target_allocation: target, color }
      const created = await basketsApi.create(basket)
      setBaskets((prev) => [...prev, created])
      setName('')
      setTarget(40)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    await basketsApi.remove(id)
    setBaskets((prev) => prev.filter((b) => b.id !== id))
  }

  if (loading) return <p className="text-sm text-text-dim">Loading baskets…</p>

  return (
    <div>
      {/* Create basket form */}
      <form onSubmit={handleCreate} className="mb-4 flex flex-wrap items-end gap-3">
        <label className="min-w-[140px] flex-1">
          <span className="mb-1 block text-text-dim text-xs">Name</span>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent"
            placeholder="e.g. Super Stable"
          />
        </label>
        <label className="w-24">
          <span className="mb-1 block text-text-dim text-xs">Target %</span>
          <input
            type="number"
            min={1}
            max={100}
            value={target}
            onChange={(e) => setTarget(Number(e.target.value))}
            className="w-full rounded border border-border bg-bg px-2 py-1.5 text-sm text-text outline-none focus:border-accent"
          />
        </label>
        <label className="w-24">
          <span className="mb-1 block text-text-dim text-xs">Color</span>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-[34px] w-full cursor-pointer rounded border border-border bg-bg p-0.5"
          />
        </label>
        <button
          type="submit"
          disabled={creating}
          className="rounded bg-accent px-3 py-1.5 font-medium text-bg text-sm transition disabled:opacity-50"
        >
          {creating ? '…' : '+ Add'}
        </button>
      </form>

      {/* Basket list */}
      {baskets.length === 0 ? (
        <p className="text-sm text-text-dim">No baskets yet. Create one above.</p>
      ) : (
        <div className="space-y-2">
          {baskets.map((basket) => (
            <div
              key={basket.id}
              className="flex items-center justify-between rounded border border-border bg-bg px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full" style={{ backgroundColor: basket.color }} />
                <span className="text-sm text-text">{basket.name}</span>
                <span className="text-text-dim text-xs">{parseFloat(basket.target_allocation).toFixed(0)}%</span>
              </div>
              <button
                type="button"
                onClick={() => handleDelete(basket.id)}
                className="rounded px-2 py-0.5 text-text-dim text-xs transition hover:border hover:border-negative hover:text-negative"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Settings page ──────────────────────────────────────────────────── */

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <h1 className="mb-6 font-semibold text-text text-xl">Settings</h1>

      <div className="space-y-8">
        <section className="rounded border border-border bg-surface p-4">
          <h2 className="mb-4 font-semibold text-sm text-text">Profile</h2>
          <ProfileSettings />
        </section>

        <section className="rounded border border-border bg-surface p-4">
          <h2 className="mb-4 font-semibold text-sm text-text">Baskets</h2>
          <BasketManager />
        </section>
      </div>
    </div>
  )
}
