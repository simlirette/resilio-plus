import { test, expect } from '@playwright/test'

const ATHLETE_ID = 'dash-athlete-1'

const WEEK_STATUS = {
  week_number: 3,
  completion_pct: 40,
  planned_hours: 7.5,
  actual_hours: 3.0,
  acwr: 1.05,
  plan: {
    id: 'plan-dash',
    athlete_id: ATHLETE_ID,
    phase: 'build',
    start_date: '2026-03-23',
    end_date: '2026-06-15',
    total_weekly_hours: 7.5,
    acwr: 1.05,
    sessions: [
      {
        date: '2026-04-14',
        sport: 'running',
        workout_type: 'Tempo Run',
        duration_min: 50,
        notes: 'Cruise intervals',
        fatigue_score: { local_muscular: 40, cns_load: 30, metabolic_cost: 50, recovery_hours: 24, affected_muscles: [] },
      },
      {
        date: '2026-04-16',
        sport: 'lifting',
        workout_type: 'Upper Body',
        duration_min: 60,
        notes: 'MEV week',
        fatigue_score: { local_muscular: 60, cns_load: 40, metabolic_cost: 20, recovery_hours: 36, affected_muscles: ['chest', 'back'] },
      },
    ],
  },
}

test.describe('Dashboard', () => {
  // Pre-authenticate by injecting localStorage before each test
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ id, tok }) => {
        localStorage.setItem('athlete_id', id)
        localStorage.setItem('token', tok)
      },
      { id: ATHLETE_ID, tok: 'dash_test_token' }
    )
    await page.route(`**/athletes/${ATHLETE_ID}/week-status`, route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(WEEK_STATUS) })
    )
  })

  test('loads and displays week number and completion percentage', async ({ page }) => {
    await page.goto('/dashboard')

    await expect(page.getByText('Week 3')).toBeVisible()
    await expect(page.getByText('40')).toBeVisible()
    await expect(page.getByText('% complete')).toBeVisible()
  })

  test('shows planned hours, actual hours, and ACWR cards', async ({ page }) => {
    await page.goto('/dashboard')

    await expect(page.getByText('7.5')).toBeVisible()  // planned
    await expect(page.getByText('3')).toBeVisible()    // actual
    await expect(page.getByText('1.05')).toBeVisible() // ACWR
  })

  test('shows next upcoming session', async ({ page }) => {
    await page.goto('/dashboard')

    // At least one of the sessions should appear as "Next Session"
    // (which one depends on current date vs session dates)
    await expect(page.getByText('Next Session')).toBeVisible()
  })

  test('"View full plan" link navigates to /plan', async ({ page }) => {
    await page.route(`**/athletes/${ATHLETE_ID}/plan`, route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(WEEK_STATUS.plan),
      })
    )

    await page.goto('/dashboard')
    await page.getByRole('link', { name: /View full plan/i }).click()
    await expect(page).toHaveURL('/plan')
  })

  test('unauthenticated visitor is redirected away from /dashboard', async ({ page }) => {
    // Do NOT inject localStorage for this test
    await page.addInitScript(() => {
      localStorage.removeItem('athlete_id')
      localStorage.removeItem('token')
    })
    await page.goto('/dashboard')

    // ProtectedRoute redirects to /login when no token
    await expect(page).toHaveURL('/login')
  })
})
