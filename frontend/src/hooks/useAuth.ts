/**
 * Auth guard hook — checks auth state on mount and redirects.
 *
 * - `useAuth()` — returns auth state, auto-hydrates on mount.
 * - `useRequireAuth()` — redirects to /login if unauthenticated.
 * - `useRequireGuest()` — redirects to /dashboard if already authenticated.
 */

import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

/**
 * Primary auth hook — hydrates user on mount, exposes state + actions.
 */
export function useAuth() {
  const navigate = useNavigate()
  const { user, isLoading, error, init, login, register, logout, updateProfile, clearError } = useAuthStore()

  useEffect(() => {
    init()
  }, [init])

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    error,
    login,
    register,
    logout,
    updateProfile,
    clearError,
    navigate,
  }
}

/**
 * Require authenticated user. Redirects to /login if unauthenticated.
 *
 * Safe to call from any protected page component.
 */
export function useRequireAuth() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && !user) {
      // Preserve return URL for post-login redirect
      const returnTo = location.pathname.replace(/^\/#/, '') || '/dashboard'
      navigate(`/login?returnTo=${encodeURIComponent(returnTo)}`, { replace: true })
    }
  }, [user, isLoading, navigate, location.pathname])

  return !!user && !isLoading
}

/**
 * Require guest (not logged in). Redirects to /dashboard if authenticated.
 *
 * Use on login/register pages to skip them when already logged in.
 */
export function useRequireGuest() {
  const navigate = useNavigate()
  const { user, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && user) {
      navigate('/dashboard', { replace: true })
    }
  }, [user, isLoading, navigate])
}
