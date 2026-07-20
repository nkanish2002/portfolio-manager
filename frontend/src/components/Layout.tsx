/**
 * Layout — main app shell: nav bar, portfolio selector, user menu.
 *
 * Wrapped around all protected routes. Public routes (login/register)
 * render without this layout.
 */

import type React from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAuthStore } from '@/store/authStore'
import { usePortfolioStore } from '@/store/portfolioStore'

/* ── Nav link (active state) ────────────────────────────────────────── */

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <li>
      <NavLink
        to={to}
        end
        className={({ isActive }) =>
          `border-b-2 pb-1 transition ${
            isActive ? 'border-accent text-accent' : 'border-transparent text-text-dim hover:text-text'
          }`
        }
      >
        {children}
      </NavLink>
    </li>
  )
}

/* ── Portfolio selector dropdown ────────────────────────────────────── */

function PortfolioSelector() {
  const { portfolios, selectedId, select, isLoading } = usePortfolioStore()

  if (isLoading) return <span className="text-text-dim text-xs">Loading…</span>
  if (portfolios.length === 0) return <span className="text-text-dim text-xs">No portfolios</span>

  const selected = portfolios.find((p) => p.id === selectedId)
  void selected // used for potential future display

  return (
    <select
      value={selectedId ?? ''}
      onChange={(e) => select(e.target.value || null)}
      className="rounded border border-border bg-bg px-2 py-1 text-sm text-text outline-none focus:border-accent"
    >
      {portfolios.map((p) => (
        <option key={p.id} value={p.id}>
          {p.name}
        </option>
      ))}
    </select>
  )
}

/* ── User menu ──────────────────────────────────────────────────────── */

function UserMenu() {
  const { user, logout } = useAuthStore()
  const { status } = useWebSocket()

  const statusConfig = {
    idle: { color: 'bg-text-dim', label: 'Offline', pulse: false },
    connecting: { color: 'bg-warning', label: 'Connecting…', pulse: true },
    connected: { color: 'bg-positive', label: 'Live', pulse: true },
    error: { color: 'bg-negative', label: 'Disconnected', pulse: false },
  }
  const { color, label, pulse } = statusConfig[status]

  return (
    <div className="flex items-center gap-3">
      {/* Live connection indicator */}
      <span className="flex items-center gap-1.5 text-xs">
        <span className={`h-2 w-2 rounded-full ${color} ${pulse ? 'live-indicator' : ''}`} />
        <span className="hidden text-text-dim sm:inline">{label}</span>
      </span>

      <span className="text-sm text-text-dim">{user?.display_name || user?.email || 'User'}</span>
      <button
        type="button"
        onClick={logout}
        className="rounded border border-border px-2 py-1 text-text-dim text-xs transition hover:border-negative hover:text-negative"
      >
        Logout
      </button>
    </div>
  )
}

/* ── Layout shell ───────────────────────────────────────────────────── */

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const isDashboard = location.pathname === '/dashboard'

  return (
    <div className="flex min-h-screen flex-col">
      {/* ── Nav bar ────────────────────────────────────────────────── */}
      <nav className="border-border border-b bg-surface px-4 py-2">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="font-semibold text-base text-text">
              Portfolio Manager
            </Link>

            {isDashboard && (
              <ul className="flex gap-4 text-sm">
                <NavItem to="/dashboard">Overview</NavItem>
                <NavItem to="/positions">Positions</NavItem>
              </ul>
            )}
          </div>

          <div className="flex items-center gap-4">
            <PortfolioSelector />
            <Link to="/settings" className="text-text-dim transition hover:text-text" title="Settings">
              ⚙
            </Link>
            <UserMenu />
          </div>
        </div>
      </nav>

      {/* ── Page content ───────────────────────────────────────────── */}
      <main className="flex-1 bg-bg">{children}</main>
    </div>
  )
}
