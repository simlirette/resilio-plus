// frontend/src/components/__tests__/protected-route.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { ProtectedRoute } from '../protected-route'
import { AuthProvider } from '@/lib/auth'

const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => '/',
}))

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear()
    mockReplace.mockClear()
  })

  it('renders children when token is present', async () => {
    localStorage.setItem('token', 'tok')
    localStorage.setItem('athlete_id', 'ath1')
    render(
      <AuthProvider>
        <ProtectedRoute><span>protected content</span></ProtectedRoute>
      </AuthProvider>
    )
    await act(async () => {})
    expect(screen.getByText('protected content')).toBeInTheDocument()
  })

  it('redirects to /login when token is absent', async () => {
    render(
      <AuthProvider>
        <ProtectedRoute><span>protected content</span></ProtectedRoute>
      </AuthProvider>
    )
    await act(async () => {})
    expect(mockReplace).toHaveBeenCalledWith('/login')
  })
})
