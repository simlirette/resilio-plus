import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import ReviewPage from '../page'
import { AuthProvider } from '@/lib/auth'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  api: { submitReview: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message) }
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/review',
}))

const MOCK_REVIEW_RESPONSE: apiModule.WeeklyReviewResponse = {
  review_id: 'r1',
  week_number: 3,
  planned_hours: 8.5,
  actual_hours: 6.2,
  acwr: 1.12,
  adjustment_applied: 1.0,
  next_week_suggestion: 'Load on target. Keep same volume next week.',
}

function renderReview() {
  localStorage.setItem('token', 'tok')
  localStorage.setItem('athlete_id', 'ath1')
  return render(<AuthProvider><ReviewPage /></AuthProvider>)
}

describe('ReviewPage', () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear() })

  it('renders the week_end_date field and submit button', async () => {
    renderReview()
    await act(async () => {})
    expect(screen.getByLabelText(/week end date/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit review/i })).toBeInTheDocument()
  })

  it('submits the form and shows next_week_suggestion on success', async () => {
    vi.mocked(apiModule.api.submitReview).mockResolvedValueOnce(MOCK_REVIEW_RESPONSE)
    renderReview()
    await act(async () => {})
    fireEvent.click(screen.getByRole('button', { name: /submit review/i }))
    await waitFor(() => {
      expect(screen.getByText(/Load on target/i)).toBeInTheDocument()
    })
  })

  it('shows ACWR and adjustment after successful submit', async () => {
    vi.mocked(apiModule.api.submitReview).mockResolvedValueOnce(MOCK_REVIEW_RESPONSE)
    renderReview()
    await act(async () => {})
    fireEvent.click(screen.getByRole('button', { name: /submit review/i }))
    await waitFor(() => {
      expect(screen.getByText(/1\.12/)).toBeInTheDocument()
    })
  })
})
