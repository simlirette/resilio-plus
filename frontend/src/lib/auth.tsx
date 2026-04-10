// frontend/src/lib/auth.tsx
'use client'
import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'

interface AuthState {
  token: string | null
  athleteId: string | null
}

interface AuthContextValue extends AuthState {
  login: (token: string, athleteId: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, athleteId: null })

  useEffect(() => {
    const token = localStorage.getItem('token')
    const athleteId = localStorage.getItem('athlete_id')
    if (token && athleteId) setAuth({ token, athleteId })
  }, [])

  const login = useCallback((token: string, athleteId: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('athlete_id', athleteId)
    setAuth({ token, athleteId })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('athlete_id')
    setAuth({ token: null, athleteId: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
