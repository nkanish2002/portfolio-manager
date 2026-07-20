/**
 * Auth store — manages user session, JWT lifecycle, and auth state.
 *
 * Persistence: JWT stored in localStorage (survives reload).
 * On mount, `init()` hydrates user from stored token.
 */

import { create } from 'zustand'
import { authApi, type CreateUser, type LoginCredentials, type User, type UserUpdate } from '@/services/api'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null

  /* ── Actions ─────────────────────────────────────────────────────── */
  init: () => Promise<void>
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: CreateUser) => Promise<void>
  logout: () => void
  updateProfile: (patch: UserUpdate) => Promise<void>
  clearError: () => void
}

const TOKEN_KEY = 'jwt_token'

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  error: null,

  /* Hydrate user from stored token */
  init: async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      set({ user: null, token: null })
      return
    }

    set({ isLoading: true, error: null })
    try {
      const user = await authApi.me()
      set({ user, token, isLoading: false })
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      set({ user: null, token: null, isLoading: false })
    }
  },

  login: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      const { access_token } = await authApi.login(credentials)
      localStorage.setItem(TOKEN_KEY, access_token)
      const user = await authApi.me()
      set({ user, token: access_token, isLoading: false })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed'
      set({ error: message, isLoading: false })
      throw err
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null })
    try {
      await authApi.register(data)
      set({ isLoading: false })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Registration failed'
      set({ error: message, isLoading: false })
      throw err
    }
  },

  logout: () => {
    authApi.logout().catch(() => {}) // fire-and-forget backend invalidation
    localStorage.removeItem(TOKEN_KEY)
    set({ user: null, token: null })
    window.location.hash = '#/login'
  },

  updateProfile: async (patch) => {
    try {
      const updated = await authApi.updateMe(patch)
      set({ user: updated })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Profile update failed'
      set({ error: message })
      throw err
    }
  },

  clearError: () => set({ error: null }),
}))
