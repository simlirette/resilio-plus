// frontend/src/app/login/__tests__/page.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LoginPage from '../page'
import { AuthProvider } from '@/lib/auth'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  api: { login: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message) }
  },
}))

const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => '/login',
}))

function renderLogin() {
  return render(<AuthProvider><LoginPage /></AuthProvider>)
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders email and password fields and a submit button', () => {
    renderLogin()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('calls api.login with form values and redirects to /dashboard on success', async () => {
    vi.mocked(apiModule.api.login).mockResolvedValueOnce({
      access_token: 'tok123', token_type: 'bearer', athlete_id: 'ath1',
    })
    renderLogin()
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(apiModule.api.login).toHaveBeenCalledWith('a@b.com', 'pass1234')
      expect(mockReplace).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('shows error message when api.login throws ApiError(401)', async () => {
    const { ApiError } = await import('@/lib/api')
    vi.mocked(apiModule.api.login).mockRejectedValueOnce(new ApiError(401, 'Invalid credentials'))
    renderLogin()
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument())
  })
})
