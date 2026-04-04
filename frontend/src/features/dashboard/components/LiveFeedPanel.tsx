/**
 * LiveFeedPanel — real-time fraud alert stream.
 *
 * Connects to the company's WebSocket channel and renders incoming fraud
 * alerts in a virtualized list (react-window). Degrades gracefully to a
 * 10-second polling fallback if the WS has been disconnected for > 60 s.
 * Browser Notification API toasts are fired for HIGH / CRITICAL alerts the
 * moment they arrive over the live channel.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { FixedSizeList, type ListChildComponentProps } from "react-window";
import { formatDistanceToNow } from "date-fns";
import { useQuery } from "@tanstack/react-query";
import { Wifi, WifiOff, RefreshCw, ShieldAlert } from "lucide-react";

import { useWebSocket } from "@/hooks/useWebSocket";
import { fraudService } from "@/services/fraud.service";
import { formatCurrency } from "@/utils/format";
import type { AlertSeverity, FraudAlert, WsFraudAlertEvent } from "@/types/api.types";

// ─── Constants ───────────────────────────────────────────────────────────────

const OFFLINE_THRESHOLD_MS = 60_000;
const EXPLANATION_MAX_CHARS = 80;
const LIST_HEIGHT = 480;
const ITEM_HEIGHT = 72;
const TIMESTAMP_REFRESH_MS = 10_000;
const POLLING_INTERVAL_MS = 10_000;
const POLLING_PAGE_SIZE = 20;

// ─── Severity styling ────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<
  AlertSeverity,
  { badge: string; dot: string }
> = {
  critical: {
    badge:
      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 ring-1 ring-red-200 dark:ring-red-800",
    dot: "bg-red-500",
  },
  high: {
    badge:
      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 ring-1 ring-red-200 dark:ring-red-800",
    dot: "bg-red-400",
  },
  medium: {
    badge:
      "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 ring-1 ring-orange-200 dark:ring-orange-800",
    dot: "bg-orange-400",
  },
  low: {
    badge:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 ring-1 ring-yellow-200 dark:ring-yellow-800",
    dot: "bg-yellow-400",
  },
};

// ─── Row renderer ─────────────────────────────────────────────────────────────

interface RowData {
  alerts: FraudAlert[];
}

function AlertRow({ index, style, data }: ListChildComponentProps<RowData>) {
  const alert = data.alerts[index];
  if (!alert) return null;

  const cfg = SEVERITY_CONFIG[alert.severity];
  const rawText =
    alert.ml_explanation?.explanation ?? alert.description ?? "";
  const explanation =
    rawText.length > EXPLANATION_MAX_CHARS
      ? `${rawText.slice(0, EXPLANATION_MAX_CHARS)}\u2026`
      : rawText;

  return (
    <div
      style={style}
      className="flex items-start gap-3 px-4 py-3 border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/20 transition-colors"
      role="listitem"
    >
      <div
        className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${cfg.dot}`}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${cfg.badge}`}
            aria-label={`Severity: ${alert.severity}`}
          >
            {alert.severity}
          </span>
          {alert.transaction_amount != null && (
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
              {formatCurrency(Math.abs(alert.transaction_amount))}
            </span>
          )}
          <time
            dateTime={alert.created_at}
            className="ml-auto text-[11px] text-slate-400 flex-shrink-0"
          >
            {formatDistanceToNow(new Date(alert.created_at), {
              addSuffix: true,
            })}
          </time>
        </div>
        {explanation && (
          <p className="text-xs text-slate-500 dark:text-slate-400 truncate leading-4">
            {explanation}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Connection status bar ────────────────────────────────────────────────────

interface StatusBarProps {
  isConnected: boolean;
  isOffline: boolean;
  alertCount: number;
}

function StatusBar({ isConnected, isOffline, alertCount }: StatusBarProps) {
  if (isOffline) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700/60 rounded-lg">
        <WifiOff
          className="h-3.5 w-3.5 text-slate-400 flex-shrink-0"
          aria-hidden="true"
        />
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Offline — switched to auto-refresh mode
        </span>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
        <RefreshCw
          className="h-3.5 w-3.5 text-amber-500 animate-spin flex-shrink-0"
          aria-hidden="true"
        />
        <span className="text-xs text-amber-600 dark:text-amber-400">
          Reconnecting&hellip;
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
      <span
        className="relative flex h-2 w-2 flex-shrink-0"
        aria-hidden="true"
      >
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
      </span>
      <span className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
        Live
      </span>
      <span className="ml-auto text-xs text-slate-400">
        {alertCount} event{alertCount !== 1 ? "s" : ""}
      </span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface LiveFeedPanelProps {
  companyId: number;
}

export function LiveFeedPanel({ companyId }: LiveFeedPanelProps) {
  const { events, isConnected, connectionStatus, lastFraudAlert, disconnectedSince } =
    useWebSocket(companyId);

  // Force timestamp re-render every 10 s without re-fetching data.
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), TIMESTAMP_REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  // Compute offline state reactively from tick (re-evaluated every 10 s).
  const isOffline =
    disconnectedSince !== null &&
    Date.now() - disconnectedSince > OFFLINE_THRESHOLD_MS;

  // ── Browser Notification permission ──────────────────────────────────────
  const notificationPermRef = useRef<NotificationPermission>("default");
  useEffect(() => {
    if (!isConnected) return;
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") {
      void Notification.requestPermission().then((p) => {
        notificationPermRef.current = p;
      });
    } else {
      notificationPermRef.current = Notification.permission;
    }
  }, [isConnected]);

  // ── Toast HIGH / CRITICAL alerts via Notification API ────────────────────
  useEffect(() => {
    if (!lastFraudAlert) return;
    const { severity, transaction_amount, description } = lastFraudAlert.data;
    if (
      (severity === "high" || severity === "critical") &&
      notificationPermRef.current === "granted"
    ) {
      const amountStr =
        transaction_amount != null
          ? ` — ${formatCurrency(Math.abs(transaction_amount))}`
          : "";
      new Notification(`Fraud Alert: ${severity.toUpperCase()}${amountStr}`, {
        body: description ?? "Suspicious activity detected.",
        icon: "/favicon.ico",
        tag: `fraud-${lastFraudAlert.data.id}`,
      });
    }
  }, [lastFraudAlert]);

  // ── Polling fallback (WS offline > 60 s) ─────────────────────────────────
  const { data: polledData } = useQuery({
    queryKey: ["fraud", "live-fallback", companyId],
    queryFn: () => fraudService.getAlerts({ page_size: POLLING_PAGE_SIZE }),
    enabled: isOffline,
    refetchInterval: isOffline ? POLLING_INTERVAL_MS : false,
    staleTime: 5_000,
  });

  // ── Normalise both sources to FraudAlert[] ────────────────────────────────
  const liveAlerts = useMemo<FraudAlert[]>(() => {
    return (events as typeof events)
      .filter((e): e is WsFraudAlertEvent => e.type === "fraud_alert")
      .map((e) => e.data);
  }, [events]);

  const displayAlerts: FraudAlert[] = isOffline
    ? (polledData?.data ?? [])
    : liveAlerts;

  const itemData: RowData = useMemo(
    () => ({ alerts: displayAlerts }),
    [displayAlerts],
  );

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center gap-3 px-4 pt-5 pb-3 border-b border-slate-100 dark:border-slate-700/50">
        <ShieldAlert
          className="h-4 w-4 text-red-500 flex-shrink-0"
          aria-hidden="true"
        />
        <div>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-tight">
            Live Fraud Feed
          </h2>
          <p className="text-[11px] text-slate-400 leading-tight">
            Real-time alerts via WebSocket
            {connectionStatus === "reconnecting" && " · reconnecting"}
          </p>
        </div>
      </div>

      {/* Connection status bar */}
      <div className="px-4 py-2.5">
        <StatusBar
          isConnected={isConnected}
          isOffline={isOffline}
          alertCount={displayAlerts.length}
        />
      </div>

      {/* Virtualized alert list */}
      {displayAlerts.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center h-40 text-slate-400"
          role="status"
          aria-live="polite"
        >
          <ShieldAlert className="h-8 w-8 mb-2 opacity-30" aria-hidden="true" />
          <p className="text-sm">
            {isConnected ? "Waiting for events\u2026" : "No events loaded"}
          </p>
        </div>
      ) : (
        <div role="list" aria-label="Fraud alerts feed">
          <FixedSizeList
            height={LIST_HEIGHT}
            itemCount={displayAlerts.length}
            itemSize={ITEM_HEIGHT}
            itemData={itemData}
            width="100%"
            overscanCount={3}
          >
            {AlertRow}
          </FixedSizeList>
        </div>
      )}
    </div>
  );
}
