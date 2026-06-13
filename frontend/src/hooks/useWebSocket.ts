/**
 * WebSocket hook for real-time market data streaming.
 *
 * Auto-connects on mount, implements exponential backoff reconnection,
 * and dispatches messages via a callback.
 *
 * Usage:
 *   const { connected, messages, subscribe } = useWebSocket(
 *     '/ws/quotes',
 *     (msg) => { /* handle message *\/ }
 *   );
 *
 * Messages from the server:
 *   { type: 'connected', client_id: string }
 *   { type: 'subscribed', symbols: string[] }
 *   { type: 'batch', updates: Array<{symbol, price, prev}> }
 *   { type: 'price', symbol: string, price: number, prev: number }
 *   { type: 'unsubscribed' }
 *   { type: 'error', message: string }
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface PriceUpdate {
  type: 'price';
  symbol: string;
  cusip?: string;
  price: number;
  prev: number;
}

export interface BatchMessage {
  type: 'batch';
  updates: PriceUpdate[];
}

export interface ConnectedMessage {
  type: 'connected';
  client_id: string;
}

export interface SubscribedMessage {
  type: 'subscribed';
  symbols: string[];
}

export type WebSocketMessage =
  | ConnectedMessage
  | SubscribedMessage
  | BatchMessage
  | PriceUpdate
  | { type: 'error'; message: string };

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const RECONNECT_FACTOR = 2;

function useWebSocket(
  url: string,
  onMessage: (msg: WebSocketMessage) => void,
  autoConnect: boolean = true
) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);

  // Clean up reconnect timer on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      reconnectAttemptRef.current = 0; // reset on successful connect
    };

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data);
        onMessage(msg);
      } catch (err) {
        console.error('WebSocket message parse error:', err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;

      // Exponential backoff reconnection
      if (autoConnect) {
        const delay = Math.min(
          RECONNECT_BASE_MS * Math.pow(RECONNECT_FACTOR, reconnectAttemptRef.current),
          RECONNECT_MAX_MS
        );
        reconnectAttemptRef.current += 1;

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };

    ws.onerror = () => {
      // onclose will fire next; don't do anything extra here
    };

    wsRef.current = ws;
  }, [url, onMessage, autoConnect]);

  // Connect on mount (or when autoConnect changes)
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      setConnected(false);
    };
  }, [autoConnect, connect]);

  const subscribe = useCallback((symbols: string[]) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'subscribe', symbols }));
    }
  }, []);

  const unsubscribe = useCallback((symbols: string[]) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'unsubscribe', symbols }));
    }
  }, []);

  return { connected, subscribe, unsubscribe };
}

export default useWebSocket;
