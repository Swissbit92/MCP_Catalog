import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { setAuthCallbacks } from '../services/api'

export interface AuthUser {
  sub: string
  email: string
  name: string
  avatar: string
}

interface AuthContextValue {
  user: AuthUser | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (googleCredential: string) => Promise<void>
  loginLocal: () => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const initialized = useRef(false)
  // Ref so auth callbacks always see the latest token without stale closures
  const accessTokenRef = useRef<string | null>(null)

  const setAuth = useCallback((token: string, userData: AuthUser) => {
    accessTokenRef.current = token
    setAccessToken(token)
    setUser(userData)
  }, [])

  const clearAuth = useCallback(() => {
    accessTokenRef.current = null
    setAccessToken(null)
    setUser(null)
  }, [])

  // Silent refresh on mount — recovers session from HttpOnly cookie
  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch('/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      })
      if (!res.ok) {
        clearAuth()
        return false
      }
      const data = await res.json()
      setAuth(data.access_token, data.user as AuthUser)
      return true
    } catch {
      clearAuth()
      return false
    }
  }, [clearAuth, setAuth])

  // Initialize auth state on first mount
  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    refreshToken().finally(() => setIsLoading(false))
  }, [refreshToken])

  const login = useCallback(async (googleCredential: string): Promise<void> => {
    const res = await fetch('/auth/google', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ credential: googleCredential }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    setAuth(data.access_token, data.user as AuthUser)
  }, [setAuth])

  // Local bypass login (AUTH_REQUIRED=false)
  const loginLocal = useCallback(async (): Promise<void> => {
    const res = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    })
    if (!res.ok) throw new Error('Local login failed')
    const data = await res.json()
    setAuth(data.access_token, data.user as AuthUser)
  }, [setAuth])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    } catch {
      // ignore network errors on logout
    }
    clearAuth()
  }, [clearAuth])

  // Register auth callbacks so fetchWithAuth in api.ts can auto-refresh on 401
  // Uses accessTokenRef so callbacks always see the latest token, not stale closures
  useEffect(() => {
    setAuthCallbacks(
      () => accessTokenRef.current,
      async () => {
        const ok = await refreshToken()
        return ok ? accessTokenRef.current : null
      },
      () => { logout().catch(() => {}) }
    )
  }, [refreshToken, logout])

  return (
    <AuthContext.Provider value={{
      user,
      accessToken,
      isAuthenticated: !!user,
      isLoading,
      login,
      loginLocal,
      logout,
      refreshToken,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
