import { test, expect } from '@playwright/test'

const ATHLETE_ID = 'plan-athlete-1'

const PLAN = {
  id: 'plan-view-1',
  athlete_id: ATHLETE_ID,
  phase: 'base',
  start_date: '2026-04-14',
  end_date: '2026-07-07',
  total_weekly_hours: 9.0,
  acwr: 1.02,
  sessions: [
    {
      date: '2026-04-14',
      sport: 'running',
      workout_type: 'Easy Run',
      duration_min: 45,
      notes: 'Zone 1',
      fatigue_score: { local_muscular: 20, cns_load: 10, metabolic_cost: 30, recovery_hours: 12, affected_muscles: [] },
    },
    {
      date: '2026-04-15',
      sport: 'lifting',
      workout_type: 'Squat Day',
      duration_min: 60,
      notes: '5×5 at MEV',
      fatigue_score: { local_muscular: 70, cns_load: 60, metabolic_cost: 20, recovery_hours: 48, affected_muscles: ['quads', 'glutes'] },
    },
    {
      date: '2026-04-17',
      sport: 'running',
      workout_type: 'Long Run',
      duration_min: 90,
      notes: '20% weekly volume, Z1',
      fatigue_score: { local_muscular: 50, cns_load: 30, metabolic_cost: 60, recovery_hours: 36, affected_muscles: [] },
    },
  ],
}

test.describe('Plan view', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ id, tok }) => {
        localStorage.setItem('athlete_id', id)
        localStorage.setItem('token', tok)
      },
      { id: ATHLETE_ID, tok: 'plan_test_token' }
    )
    await page.route(`**/athletes/${ATHLETE_ID}/plan`, route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PLAN) })
    )
  })

  test('displays plan header with phase, dates, and ACWR', async ({ page }) => {
    await page.goto('/plan')

    await expect(page.getByText('BASE')).toBeVisible()
    await expect(page.getByText('Training Plan')).toBeVisible()
    await expect(page.getByText(/9h total/)).toBeVisible()
    await expect(page.getByText(/ACWR 1.02/)).toBeVisible()
  })

  test('renders all sessions grouped by date', async ({ page }) => {
    await page.goto('/plan')

    await expect(page.getByText('Easy Run')).toBeVisible()
    await expect(page.getByText('Squat Day')).toBeVisible()
    await expect(page.getByText('Long Run')).toBeVisible()
  })

  test('shows sport badges for each session', async ({ page }) => {
    await page.goto('/plan')

    const runningBadges = page.getByText('running')
    const liftingBadge = page.getByText('lifting')
    await expect(runningBadges.first()).toBeVisible()
    await expect(liftingBadge).toBeVisible()
  })

  test('shows session duration and notes', async ({ page }) => {
    await page.goto('/plan')

    await expect(page.getByText(/45 min/)).toBeVisible()
    await expect(page.getByText(/Zone 1/)).toBeVisible()
    await expect(page.getByText(/90 min/)).toBeVisible()
    await expect(page.getByText(/20% weekly volume/)).toBeVisible()
  })

  test('shows no-plan message when 404', async ({ page }) => {
    await page.route(`**/athletes/${ATHLETE_ID}/plan`, route =>
      route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not found' }) })
    )

    await page.goto('/plan')

    await expect(page.getByText('No plan active. Generate one first.')).toBeVisible()
  })

  test('unauthenticated visitor is redirected away from /plan', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.removeItem('athlete_id')
      localStorage.removeItem('token')
    })
    await page.goto('/plan')

    await expect(page).toHaveURL('/login')
  })
})
