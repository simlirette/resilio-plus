import { test, expect } from '@playwright/test'

const ONBOARDING_RESPONSE = {
  access_token: 'new_tok',
  token_type: 'bearer',
  athlete: { id: 'athlete-2', name: 'New Athlete', email: 'new@example.com' },
  plan: {
    id: 'plan-2',
    athlete_id: 'athlete-2',
    phase: 'base',
    start_date: '2026-04-21',
    end_date: '2026-07-14',
    total_weekly_hours: 8.0,
    acwr: 1.0,
    sessions: [
      {
        date: '2026-04-21',
        sport: 'running',
        workout_type: 'Easy Run',
        duration_min: 45,
        notes: '',
        fatigue_score: { local_muscular: 20, cns_load: 10, metabolic_cost: 30, recovery_hours: 12, affected_muscles: [] },
      },
    ],
  },
}

const WEEK_STATUS = {
  week_number: 1,
  completion_pct: 0,
  planned_hours: 8.0,
  actual_hours: 0,
  acwr: 1.0,
  plan: ONBOARDING_RESPONSE.plan,
}

test.describe('Onboarding wizard', () => {
  test('renders step 1 — Account — with RESILIO+ title', async ({ page }) => {
    await page.goto('/onboarding')

    await expect(page.getByText('RESILIO+')).toBeVisible()
    await expect(page.getByText('Set up your coaching profile')).toBeVisible()
    // Step indicator: step 1 is active
    await expect(page.getByText('Account')).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: /Continue/i })).toBeVisible()
  })

  test('advances from step 1 to step 2 after filling account fields', async ({ page }) => {
    await page.goto('/onboarding')

    await page.getByLabel('Email').fill('new@example.com')
    await page.getByLabel('Password').fill('securepass')
    await page.getByRole('button', { name: /Continue/i }).click()

    // Step 2: Athlete Profile
    await expect(page.getByText('Athlete Profile')).toBeVisible()
    await expect(page.getByLabel('Name')).toBeVisible()
    await expect(page.getByLabel('Age')).toBeVisible()
  })

  test('can navigate back from step 2 to step 1', async ({ page }) => {
    await page.goto('/onboarding')

    // Advance to step 2
    await page.getByLabel('Email').fill('new@example.com')
    await page.getByLabel('Password').fill('securepass')
    await page.getByRole('button', { name: /Continue/i }).click()
    await expect(page.getByText('Athlete Profile')).toBeVisible()

    // Go back
    await page.getByRole('button', { name: /Back/i }).click()
    await expect(page.getByLabel('Email')).toBeVisible()
  })

  test('completes full 3-step wizard and redirects to /dashboard', async ({ page }) => {
    await page.route('**/athletes/onboarding', route =>
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(ONBOARDING_RESPONSE),
      })
    )
    await page.route('**/athletes/athlete-2/week-status', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(WEEK_STATUS) })
    )

    await page.goto('/onboarding')

    // Step 1: Account
    await page.getByLabel('Email').fill('new@example.com')
    await page.getByLabel('Password').fill('securepass')
    await page.getByRole('button', { name: /Continue/i }).click()

    // Step 2: Athlete Profile
    await page.getByLabel('Name').fill('New Athlete')
    await page.getByLabel('Age').fill('28')
    await page.getByLabel('Weight (kg)').fill('75')
    await page.getByLabel('Height (cm)').fill('180')
    await page.getByLabel('Goals').fill('Run a 5K, Build muscle')
    await page.getByLabel('Hours per week').fill('8')
    await page.getByRole('button', { name: /Continue/i }).click()

    // Step 3: Your Plan
    await expect(page.getByText('Your Plan')).toBeVisible()
    await page.getByRole('button', { name: /Generate my plan/i }).click()

    await expect(page).toHaveURL('/dashboard')
  })

  test('shows error when email is already in use (409)', async ({ page }) => {
    await page.route('**/athletes/onboarding', route =>
      route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email already registered' }),
      })
    )

    await page.goto('/onboarding')

    // Step 1
    await page.getByLabel('Email').fill('existing@example.com')
    await page.getByLabel('Password').fill('securepass')
    await page.getByRole('button', { name: /Continue/i }).click()

    // Step 2
    await page.getByLabel('Name').fill('Existing User')
    await page.getByLabel('Age').fill('30')
    await page.getByLabel('Weight (kg)').fill('70')
    await page.getByLabel('Height (cm)').fill('175')
    await page.getByLabel('Goals').fill('Stay fit')
    await page.getByLabel('Hours per week').fill('5')
    await page.getByRole('button', { name: /Continue/i }).click()

    // Step 3: submit
    await page.getByRole('button', { name: /Generate my plan/i }).click()

    await expect(page.getByText('Email already in use. Sign in instead.')).toBeVisible()
  })
})
