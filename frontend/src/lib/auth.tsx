import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, setAuthToken } from './api'
import type { RoleName } from './rbac'

export interface CurrentUser {
  id: string
  email: string
  full_name: string
  role: RoleName
  department_id: string | null
}

interface AuthContextValue {
  user: CurrentUser | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_STORAGE_KEY = 'arip.token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const hydrate = useCallback(async (token: string) => {
    setAuthToken(token)
    try {
      const me = await api.get<CurrentUser>('/v1/auth/me')
      setUser(me)
    } catch {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      setAuthToken(null)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (!token) {
      setIsLoading(false)
      return
    }
    hydrate(token).finally(() => setIsLoading(false))
  }, [hydrate])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.post<{ access_token: string }>('/v1/auth/login', { email, password })
    localStorage.setItem(TOKEN_STORAGE_KEY, access_token)
    await hydrate(access_token)
  }, [hydrate])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    setAuthToken(null)
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
