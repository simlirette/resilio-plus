// frontend/src/components/protected-route.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (token === null) router.replace('/login')
  }, [token, router])

  if (token === null) return null
  return <>{children}</>
}
