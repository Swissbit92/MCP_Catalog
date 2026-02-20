import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { setAuthCallbacks } from '../services/api'

export interface AuthUser {
  sub: string
  email: string
  name: string
  avatar: string
  onboarding_completed: boolean
}

interface AuthContextValue {
  user: AuthUser | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  onboardingCompleted: boolean
  login: (googleCredential: string) => Promise<void>
  loginLocal: () => Promise<void>
  logout: () => Promise<void>
  refreshToken: () => Promise<boolean>
  completeOnboarding: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

/** Clear all NEPHILIM localStorage keys so a fresh login gets clean state. */
function clearNephilimLocalStorage() {
  const keys = [
    'nephilim_onboarding_complete',
    'nephilim_user_id',
    'nephilim_user_name',
    'nephilim_faction',
    'nephilim_first_persona',
    'nephilim_pending_persona',
  ]
  keys.forEach(k => localStorage.removeItem(k))
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const initialized = useRef(false)
  const migrationDone = useRef(false)
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
      const userData: AuthUser = {
        sub: data.user.sub,
        email: data.user.email,
        name: data.user.name,
        avatar: data.user.avatar,
        onboarding_completed: !!data.user.onboarding_completed,
      }
      setAuth(data.access_token, userData)
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

  // Migration: sync existing localStorage onboarding flag to DB (once per session)
  useEffect(() => {
    if (!user || migrationDone.current) return
    migrationDone.current = true

    const localFlag = localStorage.getItem('nephilim_onboarding_complete')
    if (localFlag === 'true' && !user.onboarding_completed) {
      // Existing user has localStorage flag but not DB flag — sync to server
      fetch('/auth/me/onboarding', {
        method: 'POST',
        headers: accessTokenRef.current
          ? { 'Authorization': `Bearer ${accessTokenRef.current}` }
          : {},
      })
        .then(res => {
          if (res.ok) {
            setUser(prev => prev ? { ...prev, onboarding_completed: true } : prev)
          }
        })
        .catch(() => { /* ignore migration failure, will retry next session */ })
    }
  }, [user])

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
    const userData: AuthUser = {
      sub: data.user.sub,
      email: data.user.email,
      name: data.user.name,
      avatar: data.user.avatar,
      onboarding_completed: !!data.user.onboarding_completed,
    }
    setAuth(data.access_token, userData)
  }, [setAuth])

  // Local bypass login (AUTH_REQUIRED=false)
  const loginLocal = useCallback(async (): Promise<void> => {
    const res = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include',
    })
    if (!res.ok) throw new Error('Local login failed')
    const data = await res.json()
    const userData: AuthUser = {
      sub: data.user.sub,
      email: data.user.email,
      name: data.user.name,
      avatar: data.user.avatar,
      onboarding_completed: !!data.user.onboarding_completed,
    }
    setAuth(data.access_token, userData)
  }, [setAuth])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await fetch('/auth/logout', { method: 'POST', credentials: 'include' })
    } catch {
      // ignore network errors on logout
    }
    clearNephilimLocalStorage()
    clearAuth()
  }, [clearAuth])

  const completeOnboarding = useCallback(async (): Promise<void> => {
    const token = accessTokenRef.current
    const res = await fetch('/auth/me/onboarding', {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Failed to complete onboarding')
    setUser(prev => prev ? { ...prev, onboarding_completed: true } : prev)
    // Keep localStorage in sync for any remaining reads
    localStorage.setItem('nephilim_onboarding_complete', 'true')
  }, [])

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
      onboardingCompleted: !!user?.onboarding_completed,
      login,
      loginLocal,
      logout,
      refreshToken,
      completeOnboarding,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
