// frontend/src/app/page.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'

export default function RootPage() {
  const router = useRouter()
  const { token } = useAuth()

  useEffect(() => {
    router.replace(token ? '/dashboard' : '/onboarding')
  }, [token, router])

  return null
}
