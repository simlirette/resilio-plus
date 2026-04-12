import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('@/lib/api', () => ({
  api: { getPlan: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message) }
  },
}))

import PlanPage from '../page'
import { AuthProvider } from '@/lib/auth'
import * as apiModule from '@/lib/api'

const MOCK_PLAN: apiModule.TrainingPlanResponse = {
  id: 'p1', athlete_id: 'a1', start_date: '2026-04-14', end_date: '2026-04-20',
  phase: 'build', total_weekly_hours: 8.5, acwr: 1.0,
  sessions: [
    { id: 's1', date: '2026-04-14', sport: 'running', workout_type: 'Easy Run', duration_min: 45, fatigue_score: { local_muscular: 20, cns_load: 10, metabolic_cost: 30, recovery_hours: 8, affected_muscles: [] }, notes: 'Zone 2' },
    { id: 's2', date: '2026-04-15', sport: 'lifting', workout_type: 'Squat + Deadlift', duration_min: 60, fatigue_score: { local_muscular: 70, cns_load: 60, metabolic_cost: 20, recovery_hours: 48, affected_muscles: ['quads', 'hamstrings'] }, notes: '5x5' },
  ],
}

function renderPlan() {
  localStorage.setItem('token', 'tok')
  localStorage.setItem('athlete_id', 'ath1')
  return render(<AuthProvider><PlanPage /></AuthProvider>)
}

describe('PlanPage', () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear() })

  it('renders session workout types after load', async () => {
    vi.mocked(apiModule.api.getPlan).mockResolvedValueOnce(MOCK_PLAN)
    renderPlan()
    await waitFor(() => {
      expect(screen.getByText(/Easy Run/)).toBeInTheDocument()
      expect(screen.getByText(/Squat \+ Deadlift/)).toBeInTheDocument()
    })
  })

  it('renders phase and total hours', async () => {
    vi.mocked(apiModule.api.getPlan).mockResolvedValueOnce(MOCK_PLAN)
    renderPlan()
    await waitFor(() => {
      expect(screen.getByText(/build/i)).toBeInTheDocument()
      expect(screen.getByText(/8\.5/)).toBeInTheDocument()
    })
  })

  it('shows "no plan" empty state on 404', async () => {
    const { ApiError } = await import('@/lib/api')
    vi.mocked(apiModule.api.getPlan).mockRejectedValueOnce(new ApiError(404, 'Not found'))
    renderPlan()
    await waitFor(() => {
      expect(screen.getByText(/no plan/i)).toBeInTheDocument()
    })
  })
})
