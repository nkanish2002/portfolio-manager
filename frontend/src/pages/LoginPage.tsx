/**
 * Login page — email + password form, links to registration.
 */

import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth, useRequireGuest } from '@/hooks/useAuth'

export default function LoginPage() {
  useRequireGuest()

  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnTo = searchParams.get('returnTo') || '/dashboard'

  const { login, isLoading, error, clearError } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await login({ email, password })
      navigate(decodeURIComponent(returnTo), { replace: true })
    } catch {
      // error set by store
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded border border-border bg-surface p-8">
        <h1 className="mb-2 font-semibold text-text text-xl">Sign in</h1>
        <p className="mb-6 text-sm text-text-dim">Welcome back to Portfolio Manager</p>

        {error && (
          <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-3 py-2 text-negative text-sm">
            {error}
          </div>
        )}

        <label className="mb-4 block">
          <span className="mb-1 block font-medium text-sm text-text-dim">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => {
              clearError()
              setEmail(e.target.value)
            }}
            className="w-full rounded border border-border bg-bg px-3 py-2 text-text outline-none transition focus:border-accent"
            placeholder="you@example.com"
          />
        </label>

        <label className="mb-6 block">
          <span className="mb-1 block font-medium text-sm text-text-dim">Password</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => {
              clearError()
              setPassword(e.target.value)
            }}
            className="w-full rounded border border-border bg-bg px-3 py-2 text-text outline-none transition focus:border-accent"
            placeholder="Min 8 characters"
          />
        </label>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded bg-accent px-4 py-2 font-medium text-bg transition disabled:opacity-50"
        >
          {isLoading ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="mt-6 text-center text-sm text-text-dim">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="font-medium text-accent hover:underline">
            Create one
          </Link>
        </p>
      </form>
    </div>
  )
}
