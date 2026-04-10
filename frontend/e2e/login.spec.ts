import { test, expect } from '@playwright/test'

// Minimal week-status payload so the dashboard renders after redirect
const WEEK_STATUS = {
  week_number: 1,
  completion_pct: 0,
  planned_hours: 6.5,
  actual_hours: 0,
  acwr: 1.0,
  plan: {
    id: 'plan-1',
    athlete_id: 'athlete-1',
    phase: 'base',
    start_date: '2026-04-14',
    end_date: '2026-07-07',
    total_weekly_hours: 6.5,
    acwr: 1.0,
    sessions: [
      {
        date: '2026-04-14',
        sport: 'running',
        workout_type: 'Easy Run',
        duration_min: 45,
        notes: 'Zone 1 easy',
        fatigue_score: { local_muscular: 20, cns_load: 10, metabolic_cost: 30, recovery_hours: 12, affected_muscles: [] },
      },
    ],
  },
}

test.describe('Login flow', () => {
  test('renders login page with RESILIO+ title and form fields', async ({ page }) => {
    await page.goto('/login')

    await expect(page.getByText('RESILIO+')).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
    await expect(page.getByText('Get started')).toBeVisible()
  })

  test('shows error message on invalid credentials (401)', async ({ page }) => {
    await page.route('**/auth/login', route =>
      route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Invalid credentials' }) })
    )

    await page.goto('/login')
    await page.getByLabel('Email').fill('wrong@example.com')
    await page.getByLabel('Password').fill('badpassword')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Invalid credentials. Check your email and password.')).toBeVisible()
  })

  test('shows generic error on server error (500)', async ({ page }) => {
    await page.route('**/auth/login', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal error' }) })
    )

    await page.goto('/login')
    await page.getByLabel('Email').fill('athlete@example.com')
    await page.getByLabel('Password').fill('password123')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Something went wrong. Please try again.')).toBeVisible()
  })

  test('redirects to /dashboard on successful login', async ({ page }) => {
    await page.route('**/auth/login', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'test_tok', token_type: 'bearer', athlete_id: 'athlete-1' }),
      })
    )
    await page.route('**/athletes/athlete-1/week-status', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(WEEK_STATUS) })
    )

    await page.goto('/login')
    await page.getByLabel('Email').fill('athlete@example.com')
    await page.getByLabel('Password').fill('password123')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page).toHaveURL('/dashboard')
  })

  test('"Get started" link navigates to /onboarding', async ({ page }) => {
    await page.goto('/login')
    await page.getByText('Get started').click()
    await expect(page).toHaveURL('/onboarding')
  })
})
