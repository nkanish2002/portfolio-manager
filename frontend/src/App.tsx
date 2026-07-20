/**
 * App root — routes with auth guard + Layout shell.
 *
 * Public routes (no Layout): /login, /register
 * Protected routes (Layout wrapper): /dashboard, /positions, /settings
 */

import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from '@/components/Layout'
import { useRequireAuth } from '@/hooks/useAuth'
import DashboardPage from '@/pages/DashboardPage'
import LoginPage from '@/pages/LoginPage'
import PositionsPage from '@/pages/PositionsPage'
import RegisterPage from '@/pages/RegisterPage'
import SettingsPage from '@/pages/SettingsPage'
import { useAuthStore } from '@/store/authStore'
import { useBasketStore } from '@/store/basketStore'
import { usePortfolioStore } from '@/store/portfolioStore'

/* ── Init stores on mount ───────────────────────────────────────────── */

function InitStores() {
  const portfolioInit = usePortfolioStore((s) => s.init)
  const basketInit = useBasketStore((s) => s.init)

  React.useEffect(() => {
    portfolioInit()
  }, [portfolioInit])
  React.useEffect(() => {
    basketInit()
  }, [basketInit])

  return null
}

/* ── Protected route wrapper ────────────────────────────────────────── */

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useRequireAuth()
  return isAuthenticated ? children : null
}

/* ── Loading screen ─────────────────────────────────────────────────── */

function Loading() {
  return <div className="flex min-h-screen items-center justify-center text-text-dim">Loading…</div>
}

/* ── App ────────────────────────────────────────────────────────────── */

function App() {
  const { user, isLoading } = useAuthStore()

  return (
    <>
      <Routes>
        {/* ── Public routes (no Layout) ────────────────────────────── */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* ── Protected routes (with Layout) ───────────────────────── */}
        <Route
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/positions" element={<PositionsPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />

        {/* ── Root redirect ────────────────────────────────────────── */}
        <Route
          path="/"
          element={
            isLoading ? <Loading /> : user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
          }
        />

        {/* ── Catch-all ────────────────────────────────────────────── */}
        <Route
          path="*"
          element={
            isLoading ? <Loading /> : user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
          }
        />
      </Routes>

      {/* ── Init data stores (hydrates portfolios + baskets) ────────── */}
      {user && <InitStores />}
    </>
  )
}

export default App
