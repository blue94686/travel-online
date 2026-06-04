import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'scenic-token'
const USER_KEY = 'scenic-user'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch { return null }
  })
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [loading, setLoading] = useState(false)

  const saveAuth = useCallback((tok, usr) => {
    setToken(tok)
    setUser(usr)
    localStorage.setItem(TOKEN_KEY, tok)
    localStorage.setItem(USER_KEY, JSON.stringify(usr))
    // Also set legacy keys for compatibility
    if (usr?.role) localStorage.setItem('scenic-role', usr.role)
    if (usr?.email) localStorage.setItem('scenic-user-email', usr.email)
  }, [])

  const sendCode = useCallback(async (email) => {
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
      const res = await fetch(`${base}/api/auth/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (!data.success) throw new Error(data.message || '发送失败')
      return { success: true, message: data.message }
    } catch (err) {
      return { success: false, error: err.message }
    }
  }, [])

  const login = useCallback(async (email, password) => {
    setLoading(true)
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
      const res = await fetch(`${base}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!data.success) throw new Error(data.message || '登录失败')
      saveAuth(data.data.token, data.data.user)
      return { success: true, user: data.data.user }
    } catch (err) {
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [saveAuth])

  const register = useCallback(async (email, password, code) => {
    setLoading(true)
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
      const res = await fetch(`${base}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, code }),
      })
      const data = await res.json()
      if (!data.success) throw new Error(data.message || '注册失败')
      saveAuth(data.data.token, data.data.user)
      return { success: true, user: data.data.user }
    } catch (err) {
      return { success: false, error: err.message }
    } finally {
      setLoading(false)
    }
  }, [saveAuth])

  const logout = useCallback(() => {
    setToken('')
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem('scenic-role')
    localStorage.removeItem('scenic-user-email')
  }, [])

  // Verify token on mount
  useEffect(() => {
    if (!token) return
    const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
    fetch(`${base}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(data => {
        if (data.success && data.data) {
          setUser(data.data)
          localStorage.setItem(USER_KEY, JSON.stringify(data.data))
        } else {
          logout()
        }
      })
      .catch(() => {})
  }, []) // only on mount

  const isLoggedIn = !!user && !!token
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  return (
    <AuthContext.Provider value={{ user, token, isLoggedIn, isAdmin, loading, login, register, sendCode, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) return { user: null, token: '', isLoggedIn: false, isAdmin: false, loading: false, login: () => {}, register: () => {}, sendCode: () => {}, logout: () => {} }
  return ctx
}
