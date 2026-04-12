// frontend/src/lib/auth.tsx
'use client'
import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { api } from './api'

interface AuthState {
  token: string | null
  athleteId: string | null
  coachingMode: 'full' | 'tracking_only' | null
}

interface AuthContextValue extends AuthState {
  login: (token: string, athleteId: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function fetchCoachingMode(athleteId: string): Promise<'full' | 'tracking_only'> {
  try {
    const profile = await api.getAthleteProfile(athleteId)
    return profile.coaching_mode
  } catch {
    return 'full'
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, athleteId: null, coachingMode: null })

  useEffect(() => {
    const token = localStorage.getItem('token')
    const athleteId = localStorage.getItem('athlete_id')
    const storedMode = localStorage.getItem('coaching_mode') as 'full' | 'tracking_only' | null
    if (token && athleteId) {
      setAuth({ token, athleteId, coachingMode: storedMode })
      fetchCoachingMode(athleteId).then(mode => {
        localStorage.setItem('coaching_mode', mode)
        setAuth(prev => ({ ...prev, coachingMode: mode }))
      })
    }
  }, [])

  const login = useCallback((token: string, athleteId: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('athlete_id', athleteId)
    setAuth({ token, athleteId, coachingMode: null })
    fetchCoachingMode(athleteId).then(mode => {
      localStorage.setItem('coaching_mode', mode)
      setAuth(prev => ({ ...prev, coachingMode: mode }))
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('athlete_id')
    localStorage.removeItem('coaching_mode')
    setAuth({ token: null, athleteId: null, coachingMode: null })
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
