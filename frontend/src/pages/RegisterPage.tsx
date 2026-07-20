/**
 * Register page — email + password + display name form, links to login.
 */

import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, useRequireGuest } from '@/hooks/useAuth'

export default function RegisterPage() {
  useRequireGuest()

  const navigate = useNavigate()
  const { register, isLoading, error, clearError } = useAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [mismatchError, setMismatchError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setMismatchError('')

    if (password !== confirmPassword) {
      setMismatchError('Passwords do not match')
      return
    }

    try {
      await register({ email, password, display_name: name || null })
      navigate('/login', { replace: true, state: { registered: true } })
    } catch {
      // error set by store
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded border border-border bg-surface p-8">
        <h1 className="mb-2 font-semibold text-text text-xl">Create account</h1>
        <p className="mb-6 text-sm text-text-dim">Set up your Portfolio Manager account</p>

        {error && (
          <div className="mb-4 rounded border border-negative/30 bg-negative/10 px-3 py-2 text-negative text-sm">
            {error}
          </div>
        )}

        <label className="mb-4 block">
          <span className="mb-1 block font-medium text-sm text-text-dim">
            Display name <span className="text-text-dim">(optional)</span>
          </span>
          <input
            type="text"
            value={name}
            onChange={(e) => {
              clearError()
              setName(e.target.value)
            }}
            className="w-full rounded border border-border bg-bg px-3 py-2 text-text outline-none transition focus:border-accent"
            placeholder="Niko"
          />
        </label>

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

        <label className="mb-4 block">
          <span className="mb-1 block font-medium text-sm text-text-dim">Password</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={password}
            onChange={(e) => {
              clearError()
              setMismatchError('')
              setPassword(e.target.value)
            }}
            className="w-full rounded border border-border bg-bg px-3 py-2 text-text outline-none transition focus:border-accent"
            placeholder="Min 8 characters"
          />
        </label>

        <label className="mb-6 block">
          <span className="mb-1 block font-medium text-sm text-text-dim">Confirm password</span>
          <input
            type="password"
            required
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => {
              clearError()
              setMismatchError('')
              setConfirmPassword(e.target.value)
            }}
            className={`w-full rounded border bg-bg px-3 py-2 text-text outline-none transition focus:border-accent ${
              mismatchError ? 'border-negative' : 'border-border'
            }`}
            placeholder="Re-enter password"
          />
          {mismatchError && <p className="mt-1 text-negative text-xs">{mismatchError}</p>}
        </label>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded bg-accent px-4 py-2 font-medium text-bg transition disabled:opacity-50"
        >
          {isLoading ? 'Creating account…' : 'Create account'}
        </button>

        <p className="mt-6 text-center text-sm text-text-dim">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-accent hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  )
}
