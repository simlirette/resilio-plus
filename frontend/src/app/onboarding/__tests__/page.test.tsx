// frontend/src/app/onboarding/__tests__/page.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import OnboardingPage from '../page'
import { AuthProvider } from '@/lib/auth'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  api: { onboarding: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message) }
  },
}))

const mockReplace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  usePathname: () => '/onboarding',
}))

function renderOnboarding() {
  return render(<AuthProvider><OnboardingPage /></AuthProvider>)
}

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders Step 1 with email and password fields', () => {
    renderOnboarding()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue/i })).toBeInTheDocument()
  })

  it('advances to Step 2 when Step 1 Continue is clicked', () => {
    renderOnboarding()
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
  })

  it('shows error when duplicate email (409)', async () => {
    const { ApiError } = await import('@/lib/api')
    vi.mocked(apiModule.api.onboarding).mockRejectedValueOnce(new ApiError(409, 'Email already in use'))
    renderOnboarding()

    // Step 1
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'dup@b.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 2 — fill required fields
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Simon' } })
    fireEvent.change(screen.getByLabelText(/age/i), { target: { value: '30' } })
    fireEvent.change(screen.getByLabelText(/weight/i), { target: { value: '75' } })
    fireEvent.change(screen.getByLabelText(/height/i), { target: { value: '180' } })
    fireEvent.change(screen.getByLabelText(/goals/i), { target: { value: 'Get fit' } })
    fireEvent.change(screen.getByLabelText(/hours per week/i), { target: { value: '8' } })
    const continueButtons = screen.getAllByRole('button', { name: /continue/i })
    fireEvent.click(continueButtons[continueButtons.length - 1])

    // Step 3 — submit
    fireEvent.click(screen.getByRole('button', { name: /generate my plan/i }))

    await waitFor(() => expect(screen.getByText(/email already in use/i)).toBeInTheDocument())
  })

  it('stores token and redirects to /dashboard on success', async () => {
    vi.mocked(apiModule.api.onboarding).mockResolvedValueOnce({
      athlete: { id: 'a1' },
      plan: { id: 'p1', athlete_id: 'a1', start_date: '2026-04-14', end_date: '2026-04-20', phase: 'build', total_weekly_hours: 8, acwr: 1.0, sessions: [] },
      access_token: 'tok123',
      token_type: 'bearer',
    })
    renderOnboarding()

    // Step 1
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'new@b.com' } })
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 2
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Simon' } })
    fireEvent.change(screen.getByLabelText(/age/i), { target: { value: '30' } })
    fireEvent.change(screen.getByLabelText(/weight/i), { target: { value: '75' } })
    fireEvent.change(screen.getByLabelText(/height/i), { target: { value: '180' } })
    fireEvent.change(screen.getByLabelText(/goals/i), { target: { value: 'Get fit' } })
    fireEvent.change(screen.getByLabelText(/hours per week/i), { target: { value: '8' } })
    const continueButtons = screen.getAllByRole('button', { name: /continue/i })
    fireEvent.click(continueButtons[continueButtons.length - 1])

    // Step 3
    fireEvent.click(screen.getByRole('button', { name: /generate my plan/i }))

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/dashboard')
      expect(localStorage.getItem('token')).toBe('tok123')
    })
  })
})
