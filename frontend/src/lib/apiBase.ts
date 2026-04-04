/**
 * API origin helpers. In local dev, default to same-origin paths so Vite's `/api`
 * proxy forwards to the backend; avoids "Network Error" when only :3000 is used
 * or when `VITE_API_URL` pointed at an unreachable host.
 */

function trimSlash(s: string): string {
  return s.replace(/\/+$/, "");
}

/** Base path for REST: `/api/v1` or absolute URL ending in `/api/v1`. */
export function getApiV1Base(): string {
  // Dev server: always same-origin `/api/v1` so Vite proxies to the backend.
  // Do not use VITE_API_URL here — cross-origin calls to :8000 often surface as
  // axios "Network Error" (CORS/preflight, localhost IPv6 vs IPv4, etc.).
  if (import.meta.env.DEV) {
    return "/api/v1";
  }
  const raw = import.meta.env.VITE_API_URL as string | undefined;
  if (raw != null && String(raw).trim() !== "") {
    return `${trimSlash(String(raw))}/api/v1`;
  }
  if (typeof window !== "undefined" && window.location?.origin) {
    return `${window.location.origin}/api/v1`;
  }
  return "/api/v1";
}

/** WebSocket origin (no path): e.g. `ws://localhost:3000` in dev behind Vite proxy. */
export function getWsOrigin(): string {
  const raw = import.meta.env.VITE_WS_URL as string | undefined;
  if (raw != null && String(raw).trim() !== "") {
    return trimSlash(String(raw));
  }
  if (typeof window !== "undefined" && window.location?.host) {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}`;
  }
  return "ws://localhost:8000";
}
