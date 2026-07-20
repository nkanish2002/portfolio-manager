/**
 * WebSocket hook — manages live price connection with JWT auth.
 *
 * Connects to `/ws/quotes?token=<jwt>` via the Vite proxy.
 * Supports subscribe/unsubscribe, ping/pong, and auto-reconnect with
 * exponential backoff.
 *
 * Dispatches `ws-message` custom events on `window` so any store/component
 * can listen for price updates.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/store/authStore'

/* ── Types ──────────────────────────────────────────────────────────── */

export type WSStatus = 'idle' | 'connecting' | 'connected' | 'error'

export interface WSPriceUpdate {
  symbol: string
  price: number
  prev: number | null
  change: number
  change_pct: number
}

/* ── Constants ──────────────────────────────────────────────────────── */

const RECONNECT_MIN_MS = 1000
const RECONNECT_MAX_MS = 30000
const PING_INTERVAL_MS = 20000

/* ── Hook ───────────────────────────────────────────────────────────── */

export function useWebSocket() {
  const token = useAuthStore((s) => s.token)
  const [status, setStatus] = useState<WSStatus>('idle')

  // Refs for mutable state inside timers / handlers
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectDelayRef = useRef(RECONNECT_MIN_MS)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const statusRef = useRef<WSStatus>('idle')
  // Messages sent before the socket is OPEN are buffered and flushed on open,
  // so a `subscribe` fired during the connecting phase isn't silently dropped.
  const pendingRef = useRef<Record<string, unknown>[]>([])

  // Mirror status into ref so timer callbacks see latest
  useEffect(() => {
    statusRef.current = status
  }, [status])

  /* ── Internal helpers ────────────────────────────────────────────── */

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    } else {
      pendingRef.current.push(data)
    }
  }, [])

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current)
      pingTimerRef.current = null
    }
  }, [])

  const teardown = useCallback(() => {
    clearTimers()
    pendingRef.current = []
    wsRef.current?.close(1000, 'client cleanup')
    wsRef.current = null
    setStatus('idle')
    statusRef.current = 'idle'
  }, [clearTimers])

  const connect = useCallback(() => {
    if (!token) return
    if (statusRef.current === 'connecting' || statusRef.current === 'connected') return

    setStatus('connecting')
    const ws = new WebSocket(`/ws/quotes?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      statusRef.current = 'connected'
      reconnectDelayRef.current = RECONNECT_MIN_MS

      // Flush anything sent while we were still connecting (e.g. subscribes).
      for (const msg of pendingRef.current) {
        ws.send(JSON.stringify(msg))
      }
      pendingRef.current = []

      // Start ping/pong keepalive
      pingTimerRef.current = setInterval(() => send({ type: 'ping' }), PING_INTERVAL_MS)
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data)
        window.dispatchEvent(new CustomEvent('ws-message', { detail: message }))
      } catch {
        // ignore non-JSON
      }
    }

    ws.onclose = () => {
      wsRef.current = null
      clearTimers()
      setStatus('error')
      statusRef.current = 'error'

      // Auto-reconnect with exponential backoff (only if user is still logged in)
      if (!token) return
      const delay = Math.min(reconnectDelayRef.current, RECONNECT_MAX_MS)
      reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, RECONNECT_MAX_MS)
      reconnectTimerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      // onerror fires before onclose — teardown handled in onclose
    }
  }, [token, send, clearTimers])

  /* ── Public API ──────────────────────────────────────────────────── */

  const subscribe = useCallback(
    (symbols: string[]) => {
      send({ type: 'subscribe', symbols })
    },
    [send],
  )

  const unsubscribe = useCallback(
    (symbols: string[]) => {
      send({ type: 'unsubscribe', symbols })
    },
    [send],
  )

  const reconnect = useCallback(() => {
    teardown()
    reconnectDelayRef.current = RECONNECT_MIN_MS
    // Small delay so the old socket fully closes first
    setTimeout(connect, 200)
  }, [teardown, connect])

  /* ── Lifecycle ───────────────────────────────────────────────────── */

  // Connect on login, teardown on logout
  useEffect(() => {
    if (token) {
      connect()
    } else {
      teardown()
    }
    return teardown
  }, [token, connect, teardown])

  return { status, subscribe, unsubscribe, reconnect }
}
