// ── Auth API — Google OAuth + JWT refresh/logout ─────────────────────────────

export interface AuthTokenResponse {
  access_token: string
  token_type: string
  user: { sub: string; email: string; name: string; avatar: string }
}

export async function loginWithGoogle(credential: string): Promise<AuthTokenResponse> {
  const res = await fetch('/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ credential }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(err.detail || `Login failed: ${res.status}`)
  }
  return res.json()
}

export async function refreshAccessToken(): Promise<AuthTokenResponse> {
  const res = await fetch('/auth/refresh', {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`Refresh failed: ${res.status}`)
  return res.json()
}

export async function logoutApi(): Promise<void> {
  await fetch('/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
}
