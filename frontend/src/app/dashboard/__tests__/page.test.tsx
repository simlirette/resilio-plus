// frontend/src/app/dashboard/__tests__/page.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import DashboardPage from '../page'
import { AuthProvider } from '@/lib/auth'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  api: { getWeekStatus: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message) }
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/dashboard',
}))

const MOCK_STATUS: apiModule.WeekStatusResponse = {
  week_number: 3,
  planned_hours: 8.5,
  actual_hours: 6.2,
  completion_pct: 72.9,
  acwr: 1.12,
  plan: {
    id: 'p1', athlete_id: 'a1', start_date: '2026-04-14', end_date: '2026-04-20',
    phase: 'build', total_weekly_hours: 8.5, acwr: 1.12,
    sessions: [
      { date: '2026-04-17', sport: 'running', workout_type: 'Tempo Run', duration_min: 50, fatigue_score: { local_muscular: 30, cns_load: 20, metabolic_cost: 50, recovery_hours: 12, affected_muscles: [] }, notes: '' },
    ],
  },
}

function renderDashboard() {
  localStorage.setItem('token', 'tok')
  localStorage.setItem('athlete_id', 'ath1')
  return render(<AuthProvider><DashboardPage /></AuthProvider>)
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows completion percentage and hours when data loads', async () => {
    vi.mocked(apiModule.api.getWeekStatus).mockResolvedValueOnce(MOCK_STATUS)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('73')).toBeInTheDocument()  // completion_pct rounded to 73
      expect(screen.getByText('8.5')).toBeInTheDocument()  // planned_hours
      expect(screen.getByText('6.2')).toBeInTheDocument()  // actual_hours
    })
  })

  it('shows ACWR value', async () => {
    vi.mocked(apiModule.api.getWeekStatus).mockResolvedValueOnce(MOCK_STATUS)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/1\.12/)).toBeInTheDocument()
    })
  })

  it('shows "no plan" empty state when 404', async () => {
    const { ApiError } = await import('@/lib/api')
    vi.mocked(apiModule.api.getWeekStatus).mockRejectedValueOnce(new ApiError(404, 'No plan'))
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/no plan/i)).toBeInTheDocument()
    })
  })
})
