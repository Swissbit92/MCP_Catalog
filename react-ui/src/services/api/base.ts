// ── Shared API utilities ─────────────────────────────────────────────────────
// Base URL, auth helpers, and fetchWithAuth wrapper used by all domain modules.

export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000'

// ── Auth callback types ──────────────────────────────────────────────────────

type GetTokenFn = () => string | null
type RefreshFn = () => Promise<string | null>
type LogoutFn = () => void

let _getToken: GetTokenFn = () => null
let _refresh: RefreshFn = async () => null
let _logout: LogoutFn = () => {}

// Auth helper — inject Bearer token into fetch headers when available
export function getAuthHeader(token: string | null): HeadersInit {
  return token ? { 'Authorization': 'Bearer ' + token } : {}
}

// ── 401 Auto-Refresh Mechanism ────────────────────────────────────────────────
// AuthContext calls setAuthCallbacks() on mount so api modules can silently
// refresh expired tokens and retry failed requests without importing React hooks.

export function setAuthCallbacks(
  getToken: GetTokenFn,
  refresh: RefreshFn,
  logout: LogoutFn
): void {
  _getToken = getToken
  _refresh = refresh
  _logout = logout
}

/**
 * Authenticated fetch wrapper.
 * - Injects Bearer token automatically
 * - On 401: attempts silent token refresh, retries once
 * - On second 401: calls logout (redirects to /login via AuthContext)
 */
export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = _getToken()
  const authHeaders = getAuthHeader(token)

  const response = await fetch(url, {
    ...options,
    headers: { ...authHeaders, ...options.headers },
  })

  if (response.status !== 401) return response

  // First 401 — attempt silent refresh
  const newToken = await _refresh()
  if (!newToken) {
    _logout()
    return response
  }

  // Retry with new token
  const retried = await fetch(url, {
    ...options,
    headers: { ...getAuthHeader(newToken), ...options.headers },
  })

  if (retried.status === 401) {
    _logout()
  }

  return retried
}
