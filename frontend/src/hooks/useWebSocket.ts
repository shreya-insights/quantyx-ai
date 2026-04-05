/**
 * useWebSocket — Meta Messenger-style real-time hook.
 *
 * Manages the full WebSocket lifecycle: connect, authenticated handshake,
 * message dispatch, exponential-backoff reconnection, and cleanup on unmount.
 * All mutable values consumed inside callbacks are kept in refs so connect()
 * stays a stable callback without stale closures.
 */
/* eslint-disable react-hooks/immutability -- reconnect uses setTimeout(connect); connect is a stable useCallback */

import { useCallback, useEffect, useRef, useState } from "react";

import { getWsOrigin } from "@/lib/apiBase";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/stores/auth.store";
import { isAccessTokenExpiredOrNear } from "@/utils/jwtExpiry";
import type {
  WsConnectionStatus,
  WsEvent,
  WsFraudAlertEvent,
  WsTransactionEvent,
} from "@/types/api.types";

const RECONNECT_DELAYS = [1_000, 2_000, 4_000, 8_000, 30_000] as const;
const MAX_EVENTS = 100;

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: WsConnectionStatus;
  lastFraudAlert: WsFraudAlertEvent | null;
  lastTransaction: WsTransactionEvent | null;
  events: WsEvent[];
  disconnectedSince: number | null;
}

export function useWebSocket(companyId: number | null): UseWebSocketReturn {
  const { accessToken, refreshToken } = useAuthStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(false);

  const companyIdRef = useRef(companyId);
  const accessTokenRef = useRef(accessToken);
  const refreshTokenRef = useRef(refreshToken);
  companyIdRef.current = companyId;
  accessTokenRef.current = accessToken;
  refreshTokenRef.current = refreshToken;

  const [connectionStatus, setConnectionStatus] =
    useState<WsConnectionStatus>("connecting");
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [lastFraudAlert, setLastFraudAlert] = useState<WsFraudAlertEvent | null>(
    null,
  );
  const [lastTransaction, setLastTransaction] =
    useState<WsTransactionEvent | null>(null);
  const [disconnectedSince, setDisconnectedSince] = useState<number | null>(null);

  const connect = useCallback(() => {
    const run = async () => {
      const cid = companyIdRef.current;
      let token = accessTokenRef.current;
      const rt = refreshTokenRef.current;
      if (!cid || !token || !mountedRef.current) return;

      if (isAccessTokenExpiredOrNear(token) && rt) {
        try {
          const refreshed = await authService.refresh(rt);
          useAuthStore.getState().setTokens(refreshed);
          token = refreshed.access_token;
          accessTokenRef.current = token;
          refreshTokenRef.current = refreshed.refresh_token;
        } catch {
          /* Fall through: handshake will fail; user may need to log in again */
        }
      }

      if (!mountedRef.current || !token) return;

      const url = `${getWsOrigin()}/api/v1/ws/company/${cid}?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      setConnectionStatus(attemptRef.current === 0 ? "connecting" : "reconnecting");

      ws.onopen = () => {
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
          if (msg.type === "ping") return;

          setEvents((prev) => {
            const next = [msg, ...prev];
            return next.length > MAX_EVENTS ? next.slice(0, MAX_EVENTS) : next;
          });

          if (msg.type === "fraud_alert") setLastFraudAlert(msg);
          if (msg.type === "transaction") setLastTransaction(msg);
        } catch {
          // Malformed frame: discard silently
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current || wsRef.current !== ws) return;

        setConnectionStatus("reconnecting");
        setDisconnectedSince((prev) => prev ?? Date.now());

        const delay =
          RECONNECT_DELAYS[Math.min(attemptRef.current, RECONNECT_DELAYS.length - 1)];
        attemptRef.current += 1;

        reconnectTimerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => undefined;
    };

    void run();
  }, []);

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
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [companyId, accessToken, refreshToken, connect]);

  return {
    isConnected: connectionStatus === "connected",
    connectionStatus,
    lastFraudAlert,
    lastTransaction,
    events,
    disconnectedSince,
  };
}
