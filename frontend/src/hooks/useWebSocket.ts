/**
 * useWebSocket — Meta Messenger-style real-time hook.
 *
 * Manages the full WebSocket lifecycle: connect, authenticated handshake,
 * message dispatch, exponential-backoff reconnection, and cleanup on unmount.
 * All mutable values consumed inside callbacks are kept in refs to guarantee
 * the callback closures never go stale without needing to be re-created.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuthStore } from "@/stores/auth.store";
import type {
  WsConnectionStatus,
  WsEvent,
  WsFraudAlertEvent,
  WsTransactionEvent,
} from "@/types/api.types";

const RECONNECT_DELAYS = [1_000, 2_000, 4_000, 8_000, 30_000] as const;
const MAX_EVENTS = 100;

const WS_BASE: string =
  (import.meta.env.VITE_WS_URL as string | undefined) ?? "ws://localhost:8000";

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: WsConnectionStatus;
  lastFraudAlert: WsFraudAlertEvent | null;
  lastTransaction: WsTransactionEvent | null;
  events: WsEvent[];
  disconnectedSince: number | null;
}

export function useWebSocket(companyId: number | null): UseWebSocketReturn {
  const { accessToken } = useAuthStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(false);

  // Refs keep callbacks stable while always reading the latest prop values.
  const companyIdRef = useRef(companyId);
  const accessTokenRef = useRef(accessToken);
  companyIdRef.current = companyId;
  accessTokenRef.current = accessToken;

  const [connectionStatus, setConnectionStatus] =
    useState<WsConnectionStatus>("connecting");
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [lastFraudAlert, setLastFraudAlert] = useState<WsFraudAlertEvent | null>(
    null,
  );
  const [lastTransaction, setLastTransaction] =
    useState<WsTransactionEvent | null>(null);
  const [disconnectedSince, setDisconnectedSince] = useState<number | null>(null);

  // Empty deps: intentional — all state read via refs so the function is
  // stable across renders and safe to use in onclose without stale closure.
  const connect = useCallback(() => {
    const cid = companyIdRef.current;
    const token = accessTokenRef.current;
    if (!cid || !token || !mountedRef.current) return;

    const url = `${WS_BASE}/api/v1/ws/company/${cid}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    setConnectionStatus(attemptRef.current === 0 ? "connecting" : "reconnecting");

    ws.onopen = () => {
      // Guard: if component unmounted or a newer connection superseded this one
      if (!mountedRef.current || wsRef.current !== ws) {
        ws.close();
        return;
      }
      attemptRef.current = 0;
      setConnectionStatus("connected");
      setDisconnectedSince(null);
    };

    ws.onmessage = ({ data }: MessageEvent) => {
      if (!mountedRef.current || wsRef.current !== ws) return;
      try {
        const msg = JSON.parse(data as string) as WsEvent;
        if (msg.type === "ping") return; // internal heartbeat — ignore silently

        setEvents((prev) => {
          const next = [msg, ...prev];
          // Bounded at MAX_EVENTS to prevent unbounded memory growth in
          // long-lived sessions (Netflix streaming best practice).
          return next.length > MAX_EVENTS ? next.slice(0, MAX_EVENTS) : next;
        });

        if (msg.type === "fraud_alert") setLastFraudAlert(msg);
        if (msg.type === "transaction") setLastTransaction(msg);
      } catch {
        // Malformed frame: discard silently — never crash the dashboard
      }
    };

    ws.onclose = () => {
      // Bail if this WS was intentionally closed (unmount / superseded).
      if (!mountedRef.current || wsRef.current !== ws) return;

      setConnectionStatus("reconnecting");
      setDisconnectedSince((prev) => prev ?? Date.now());

      const delay =
        RECONNECT_DELAYS[Math.min(attemptRef.current, RECONNECT_DELAYS.length - 1)];
      attemptRef.current += 1;

      reconnectTimerRef.current = setTimeout(connect, delay);
    };

    // onerror always fires before onclose — handled there.
    ws.onerror = () => undefined;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
    if (companyId && accessToken) connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        // Null the handler before close so onclose does not schedule a reconnect.
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [companyId, accessToken, connect]);

  return {
    isConnected: connectionStatus === "connected",
    connectionStatus,
    lastFraudAlert,
    lastTransaction,
    events,
    disconnectedSince,
  };
}
