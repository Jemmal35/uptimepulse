import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import api, { tokens, type User } from './api'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!tokens.access())

  useEffect(() => {
    if (!tokens.access()) return
    api.get<User>('/auth/me/')
      .then((r) => setUser(r.data))
      .catch(() => tokens.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/token/', { email, password })
    tokens.set(data.access, data.refresh)
    setUser((await api.get<User>('/auth/me/')).data)
  }

  const register = async (email: string, username: string, password: string) => {
    await api.post('/auth/register/', { email, username, password })
    await login(email, password)
  }

  const logout = () => {
    tokens.clear()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, register, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
