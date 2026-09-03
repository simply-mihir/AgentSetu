'use client'

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import api from './api'

// ── Types ───────────────────────────────────────────────────────────────────

export interface AuthUser {
  user_id: string
  email: string
  display_name: string
  role: string
}

interface AuthContextType {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, role: string, displayName?: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

// ── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: async () => {},
  signup: async () => {},
  logout: () => {},
  isAuthenticated: false,
})

export const useAuth = () => useContext(AuthContext)

// ── Storage helpers (never expose token to server components) ────────────────

const TOKEN_KEY = 'agentsetu_token'
const REFRESH_KEY = 'agentsetu_refresh'
const USER_KEY = 'agentsetu_user'

function saveAuth(token: string, user: AuthUser, refreshToken?: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    if (refreshToken) {
      localStorage.setItem(REFRESH_KEY, refreshToken)
    }
  } catch {}
}

function loadAuth(): { token: string | null; user: AuthUser | null; refreshToken: string | null } {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const raw = localStorage.getItem(USER_KEY)
    const user = raw ? JSON.parse(raw) : null
    const refreshToken = localStorage.getItem(REFRESH_KEY)
    return { token, user, refreshToken }
  } catch {
    return { token: null, user: null, refreshToken: null }
  }
}

function clearAuth() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  } catch {}
}

// ── Public routes that don't need auth ──────────────────────────────────────

const PUBLIC_ROUTES = ['/', '/auth', '/merchant']

function isPublicRoute(path: string): boolean {
  // Exact matches for public routes
  if (PUBLIC_ROUTES.includes(path)) return true
  // Merchant detail pages (GET is public)
  if (path.startsWith('/merchant') && !path.includes('/import') && !path.includes('/policy')) return true
  return false
}

// ── Provider ────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  // Attach token to all requests
  useEffect(() => {
    const interceptor = api.interceptors.request.use((config) => {
      const stored = loadAuth()
      if (stored.token) {
        config.headers.Authorization = `Bearer ${stored.token}`
      }
      return config
    })
    return () => api.interceptors.request.eject(interceptor)
  }, [])

  // L8: Handle 401 responses — attempt silent refresh, then redirect on failure
  useEffect(() => {
    let isRefreshing = false
    let failedQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void; config: any }> = []

    const processQueue = (error: unknown, token: string | null = null) => {
      failedQueue.forEach(({ resolve, reject, config }) => {
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
          resolve(api(config))
        } else {
          reject(error)
        }
      })
      failedQueue = []
    }

    const interceptor = api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const origConfig = error.config
        if (error.response?.status !== 401 || origConfig?.url?.includes('/auth/') || origConfig?._retry) {
          return Promise.reject(error)
        }

        // Try silent refresh
        const stored = loadAuth()
        if (!stored.refreshToken) {
          clearAuth(); setUser(null); setToken(null)
          router.push('/auth?expired=1')
          return Promise.reject(error)
        }

        if (isRefreshing) {
          // Queue this request while refresh is in progress
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject, config: origConfig })
          })
        }

        isRefreshing = true
        origConfig._retry = true

        try {
          const resp = await api.post('/auth/refresh', { refresh_token: stored.refreshToken })
          const { access_token, refresh_token: newRefresh, user_id, role, display_name } = resp.data
          const authUser: AuthUser = { user_id, email: stored.user?.email || '', role, display_name }
          saveAuth(access_token, authUser, newRefresh)
          setToken(access_token)
          setUser(authUser)
          origConfig.headers.Authorization = `Bearer ${access_token}`
          processQueue(null, access_token)
          return api(origConfig)
        } catch {
          processQueue(error, null)
          clearAuth(); setUser(null); setToken(null)
          router.push('/auth?expired=1')
          return Promise.reject(error)
        } finally {
          isRefreshing = false
        }
      }
    )
    return () => api.interceptors.response.eject(interceptor)
  }, [router])

  // Load stored auth on mount
  useEffect(() => {
    const stored = loadAuth()
    if (stored.token && stored.user) {
      setToken(stored.token)
      setUser(stored.user)
    }
    setLoading(false)
  }, [])

  // Redirect to login when navigating to protected route without auth
  useEffect(() => {
    if (!loading && !user && !isPublicRoute(pathname)) {
      router.push(`/auth?redirect=${encodeURIComponent(pathname)}`)
    }
  }, [loading, user, pathname, router])

  const login = useCallback(async (email: string, password: string) => {
    const resp = await api.post('/auth/login', { email, password })
    const { access_token, refresh_token: rt, user_id, role, display_name } = resp.data
    const authUser: AuthUser = { user_id, email, role, display_name }
    saveAuth(access_token, authUser, rt)
    setToken(access_token)
    setUser(authUser)
  }, [])

  const signup = useCallback(async (email: string, password: string, role: string, displayName?: string) => {
    const resp = await api.post('/auth/signup', {
      email,
      password,
      role,
      display_name: displayName || email.split('@')[0],
    })
    const { access_token, refresh_token: rt, user_id, role: userRole, display_name } = resp.data
    const authUser: AuthUser = { user_id, email, role: userRole, display_name }
    saveAuth(access_token, authUser, rt)
    setToken(access_token)
    setUser(authUser)
  }, [])

  const logout = useCallback(async () => {
    // N12 FIX: Call backend to revoke JTI before clearing local state
    try {
      await api.post('/auth/logout')
    } catch {
      // Best-effort — clear local state even if backend call fails
    }
    clearAuth()
    setUser(null)
    setToken(null)
    router.push('/')
  }, [router])

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      signup,
      logout,
      isAuthenticated: !!user && !!token,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
