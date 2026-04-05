/** Client-side JWT exp check (no signature verify — hint only for proactive refresh). */

const _JWT_EXPIRY_SKEW_SECONDS = 120;

function _base64UrlToJson(segment: string): unknown {
  const b64 = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "=");
  const json = atob(padded);
  return JSON.parse(json) as unknown;
}

function _payloadExp(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const payload = _base64UrlToJson(parts[1]);
    if (typeof payload !== "object" || payload === null) return null;
    const exp = (payload as { exp?: unknown }).exp;
    return typeof exp === "number" ? exp : null;
  } catch {
    return null;
  }
}

export function isAccessTokenExpiredOrNear(
  token: string | null | undefined,
  skewSeconds = _JWT_EXPIRY_SKEW_SECONDS,
): boolean {
  if (!token) return true;
  const exp = _payloadExp(token);
  if (exp === null) return false;
  return exp * 1000 < Date.now() + skewSeconds * 1000;
}
