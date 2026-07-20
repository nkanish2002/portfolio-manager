/**
 * App root — routes with auth guard.
 *
 * Public routes: /login, /register
 * Protected routes: /dashboard (placeholder until 3.3), /settings
 * Root `/` → redirect to /dashboard (auth-guarded)
 */

import type React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useRequireAuth } from '@/hooks/useAuth'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import { useAuthStore } from '@/store/authStore'

/* ── Protected route wrapper ────────────────────────────────────────── */

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useRequireAuth()
  return isAuthenticated ? children : null
}

/* ── Dashboard placeholder (replaced in 3.3) ───────────────────────── */

function DashboardPage() {
  return (
    <div className="p-8 text-text">
      <h1 className="font-semibold text-2xl">Dashboard</h1>
      <p className="mt-2 text-text-dim">Phase 3.3 — Layout + KPI cards incoming</p>
    </div>
  )
}

/* ── App ────────────────────────────────────────────────────────────── */

function App() {
  const { user, isLoading } = useAuthStore()

  return (
    <Routes>
      {/* ── Public routes ──────────────────────────────────────────── */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* ── Protected routes ───────────────────────────────────────── */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            {isLoading ? (
              <div className="flex min-h-screen items-center justify-center text-text-dim">Loading…</div>
            ) : (
              <DashboardPage />
            )}
          </ProtectedRoute>
        }
      />

      {/* ── Root redirect ──────────────────────────────────────────── */}
      <Route
        path="/"
        element={
          isLoading ? (
            <div className="flex min-h-screen items-center justify-center text-text-dim">Loading…</div>
          ) : user ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* ── Catch-all ──────────────────────────────────────────────── */}
      <Route
        path="*"
        element={
          isLoading ? (
            <div className="flex min-h-screen items-center justify-center text-text-dim">Loading…</div>
          ) : user ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  )
}

export default App
