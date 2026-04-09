# Phase 5 — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js frontend with onboarding, dashboard, plan view, and weekly review pages that connect to the Phase 4 FastAPI backend.

**Architecture:** Next.js App Router, all pages as Client Components (`"use client"`). Browser calls FastAPI directly at `http://localhost:8000`. JWT in localStorage. `next-themes` for dark/light toggle. The `frontend-design` skill MUST be used by any subagent implementing a page or component to ensure production-grade visual quality.

**Tech Stack:** Next.js (latest), TypeScript, Tailwind CSS, shadcn/ui, next-themes, Vitest, React Testing Library

---

## File Map

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                   # Root layout: AuthProvider + ThemeProvider + TopNav
│   │   ├── page.tsx                     # Redirect: /dashboard if token, else /onboarding
│   │   ├── login/
│   │   │   └── page.tsx                 # Login form
│   │   ├── onboarding/
│   │   │   └── page.tsx                 # 3-step wizard
│   │   ├── dashboard/
│   │   │   └── page.tsx                 # Progress-first week status
│   │   ├── plan/
│   │   │   └── page.tsx                 # Session list
│   │   └── review/
│   │       └── page.tsx                 # Weekly review form
│   ├── components/
│   │   ├── top-nav.tsx                  # Navigation bar + theme toggle
│   │   ├── protected-route.tsx          # Redirect to /login if no token
│   │   └── ui/                          # shadcn/ui primitives (auto-generated)
│   ├── lib/
│   │   ├── api.ts                       # Typed fetch wrapper
│   │   └── auth.tsx                     # AuthContext + AuthProvider + useAuth
│   └── test-setup.ts                    # Vitest globals + next/navigation mock
├── vitest.config.ts
├── package.json
├── tailwind.config.ts
└── next.config.ts
```

---

## Backend API Reference (Phase 4)

Base URL: `http://localhost:8000`

| Method | Path | Auth | Body / Response |
|--------|------|------|-----------------|
| POST | `/auth/login` | No | `{email,password}` → `{access_token,token_type,athlete_id}` |
| POST | `/athletes/onboarding` | No | `OnboardingRequest` → `{athlete,plan,access_token,token_type}` |
| GET | `/athletes/{id}/week-status` | Bearer | → `WeekStatusResponse` |
| GET | `/athletes/{id}/plan` | Bearer | → `TrainingPlanResponse` |
| POST | `/athletes/{id}/review` | Bearer | `WeeklyReviewRequest` → `WeeklyReviewResponse` |

**OnboardingRequest fields (all required unless noted):**
```
email, password (min 8), plan_start_date (ISO date)
name, age (14-100), sex ("M"|"F"|"other"), weight_kg, height_cm
primary_sport ("running"|"lifting"|"swimming"|"biking")
sports: string[]           -- list of sports
goals: string[]            -- list of goal strings
available_days: number[]   -- 0=Mon … 6=Sun
hours_per_week: number
```

**WeekStatusResponse:**
```
week_number, planned_hours, actual_hours, completion_pct, acwr (null if no data)
plan: { id, athlete_id, start_date, end_date, phase, total_weekly_hours, acwr,
        sessions: [{ date, sport, workout_type, duration_min, notes }] }
```

**WeeklyReviewRequest:**
```
week_end_date: string (ISO)
readiness_score?: number (1-10)
hrv_rmssd?: number
sleep_hours_avg?: number
comment?: string
```

**WeeklyReviewResponse:**
```
review_id, week_number, planned_hours, actual_hours, acwr,
adjustment_applied, next_week_suggestion
```

---

## Task 1: Initialize Next.js project

**Files:**
- Delete: `frontend/README.md`
- Create: `frontend/package.json`, `frontend/next.config.ts`, `frontend/tailwind.config.ts`, `frontend/tsconfig.json`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`

- [ ] **Step 1: Remove placeholder README and initialize project**

```bash
cd /c/Users/simon/resilio-plus/frontend
rm README.md
npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*" --no-eslint --use-npm
```

When prompted "Ok to proceed? (y)" → type `y`. All other options are set by the flags above.

- [ ] **Step 2: Verify dev server starts**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm run dev
```

Expected: `✓ Ready in Xs` on `http://localhost:3000`. Stop server with Ctrl+C.

- [ ] **Step 3: Commit scaffold**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/
git commit -m "feat: initialize Next.js app scaffold"
```

---

## Task 2: Configure Vitest testing infrastructure

**Files:**
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test-setup.ts`
- Modify: `frontend/package.json` — add test scripts and devDependencies

- [ ] **Step 1: Install Vitest and React Testing Library**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Create vitest.config.ts**

```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
```

- [ ] **Step 3: Create src/test-setup.ts**

```typescript
// frontend/src/test-setup.ts
import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock Next.js navigation — pages under test don't need a real router
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/',
}))
```

- [ ] **Step 4: Add test scripts to package.json**

Open `frontend/package.json`. In the `"scripts"` section, add:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 5: Write smoke test**

```typescript
// frontend/src/lib/__tests__/smoke.test.ts
import { describe, it, expect } from 'vitest'

describe('test infrastructure', () => {
  it('runs a test', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 6: Run to verify it passes**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test
```

Expected: `1 passed`

- [ ] **Step 7: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/vitest.config.ts frontend/src/test-setup.ts frontend/src/lib/__tests__/smoke.test.ts frontend/package.json
git commit -m "feat: configure Vitest + React Testing Library"
```

---

## Task 3: Install shadcn/ui + next-themes

**Files:**
- Create: `frontend/components.json` (shadcn config)
- Create: `frontend/src/components/ui/` (auto-generated by shadcn)
- Modify: `frontend/src/app/globals.css` (shadcn CSS variables)
- Modify: `frontend/tailwind.config.ts` (shadcn extends)

- [ ] **Step 1: Initialize shadcn/ui**

```bash
cd /c/Users/simon/resilio-plus/frontend
npx shadcn@latest init -d
```

When asked for the base color, select `Neutral`. Accept all other defaults.

- [ ] **Step 2: Add required components**

```bash
npx shadcn@latest add button card input label badge progress
```

- [ ] **Step 3: Install next-themes**

```bash
npm install next-themes
```

- [ ] **Step 4: Verify build still passes**

```bash
npm run build
```

Expected: `✓ Compiled successfully`

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/
git commit -m "feat: add shadcn/ui components and next-themes"
```

---

## Task 4: API client — src/lib/api.ts

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/__tests__/api.test.ts`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/lib/__tests__/api.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api, ApiError } from '../api'

describe('api.login', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorage.clear()
  })

  it('returns TokenResponse on 200', async () => {
    const payload = { access_token: 'tok123', token_type: 'bearer', athlete_id: 'ath1' }
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } })
    )
    const result = await api.login('a@b.com', 'pass1234')
    expect(result.access_token).toBe('tok123')
    expect(result.athlete_id).toBe('ath1')
  })

  it('throws ApiError(401) on invalid credentials', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 })
    )
    await expect(api.login('a@b.com', 'wrong')).rejects.toBeInstanceOf(ApiError)
    await expect(api.login('a@b.com', 'wrong')).rejects.toMatchObject({ status: 401 })
  })
})

describe('api.getWeekStatus', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()))

  it('adds Authorization header when token is in localStorage', async () => {
    localStorage.setItem('token', 'mytoken')
    const payload = { week_number: 1, plan: {}, planned_hours: 8, actual_hours: 5, completion_pct: 62.5, acwr: 1.1 }
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(payload), { status: 200 })
    )
    await api.getWeekStatus('ath1')
    const [, options] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect((options.headers as Record<string, string>)['Authorization']).toBe('Bearer mytoken')
  })

  it('throws ApiError(401) when server returns 401', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('', { status: 401 }))
    await expect(api.getWeekStatus('ath1')).rejects.toMatchObject({ status: 401 })
  })
})
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/lib/__tests__/api.test.ts
```

Expected: FAIL — `Cannot find module '../api'`

- [ ] **Step 3: Implement api.ts**

```typescript
// frontend/src/lib/api.ts
const API_BASE = 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) throw new ApiError(401, 'Unauthorized')
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, (body as { detail?: string }).detail ?? 'Request failed')
  }
  return res.json() as Promise<T>
}

export type Sport = 'running' | 'lifting' | 'swimming' | 'biking'

export interface FatigueScore {
  local_muscular: number
  cns_load: number
  metabolic_cost: number
  recovery_hours: number
  affected_muscles: string[]
}

export interface WorkoutSlot {
  date: string
  sport: Sport
  workout_type: string
  duration_min: number
  fatigue_score: FatigueScore
  notes: string
}

export interface TrainingPlanResponse {
  id: string
  athlete_id: string
  start_date: string
  end_date: string
  phase: string
  total_weekly_hours: number
  acwr: number
  sessions: WorkoutSlot[]
}

export interface WeekStatusResponse {
  week_number: number
  plan: TrainingPlanResponse
  planned_hours: number
  actual_hours: number
  completion_pct: number
  acwr: number | null
}

export interface WeeklyReviewResponse {
  review_id: string
  week_number: number
  planned_hours: number
  actual_hours: number
  acwr: number
  adjustment_applied: number
  next_week_suggestion: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  athlete_id: string
}

export interface OnboardingResponse {
  athlete: Record<string, unknown>
  plan: TrainingPlanResponse
  access_token: string
  token_type: string
}

export interface OnboardingRequestData {
  email: string
  password: string
  plan_start_date: string
  name: string
  age: number
  sex: 'M' | 'F' | 'other'
  weight_kg: number
  height_cm: number
  primary_sport: Sport
  sports: Sport[]
  goals: string[]
  available_days: number[]
  hours_per_week: number
}

export interface WeeklyReviewRequestData {
  week_end_date: string
  readiness_score?: number
  hrv_rmssd?: number
  sleep_hours_avg?: number
  comment?: string
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  onboarding: (data: OnboardingRequestData) =>
    request<OnboardingResponse>('/athletes/onboarding', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getWeekStatus: (athleteId: string) =>
    request<WeekStatusResponse>(`/athletes/${athleteId}/week-status`),

  getPlan: (athleteId: string) =>
    request<TrainingPlanResponse>(`/athletes/${athleteId}/plan`),

  submitReview: (athleteId: string, data: WeeklyReviewRequestData) =>
    request<WeeklyReviewResponse>(`/athletes/${athleteId}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- src/lib/__tests__/api.test.ts
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/lib/api.ts frontend/src/lib/__tests__/api.test.ts
git commit -m "feat: add typed API client with JWT header injection"
```

---

## Task 5: Auth context — src/lib/auth.tsx

**Files:**
- Create: `frontend/src/lib/auth.tsx`
- Create: `frontend/src/lib/__tests__/auth.test.tsx`

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/lib/__tests__/auth.test.tsx
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../auth'

function Probe() {
  const { token, athleteId, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="token">{token ?? 'none'}</span>
      <span data-testid="athlete">{athleteId ?? 'none'}</span>
      <button onClick={() => login('tok', 'ath1')}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => localStorage.clear())

  it('starts with null token when localStorage is empty', () => {
    render(<AuthProvider><Probe /></AuthProvider>)
    expect(screen.getByTestId('token').textContent).toBe('none')
  })

  it('restores session from localStorage on mount', async () => {
    localStorage.setItem('token', 'saved')
    localStorage.setItem('athlete_id', 'ath99')
    render(<AuthProvider><Probe /></AuthProvider>)
    // useEffect fires after render — wait for it
    await act(async () => {})
    expect(screen.getByTestId('token').textContent).toBe('saved')
    expect(screen.getByTestId('athlete').textContent).toBe('ath99')
  })

  it('stores token in localStorage after login()', () => {
    render(<AuthProvider><Probe /></AuthProvider>)
    act(() => { screen.getByText('login').click() })
    expect(localStorage.getItem('token')).toBe('tok')
    expect(localStorage.getItem('athlete_id')).toBe('ath1')
    expect(screen.getByTestId('token').textContent).toBe('tok')
  })

  it('clears localStorage after logout()', () => {
    localStorage.setItem('token', 'tok')
    localStorage.setItem('athlete_id', 'ath1')
    render(<AuthProvider><Probe /></AuthProvider>)
    act(() => { screen.getByText('logout').click() })
    expect(localStorage.getItem('token')).toBeNull()
    expect(screen.getByTestId('token').textContent).toBe('none')
  })
})
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/lib/__tests__/auth.test.tsx
```

Expected: FAIL — `Cannot find module '../auth'`

- [ ] **Step 3: Implement auth.tsx**

```typescript
// frontend/src/lib/auth.tsx
'use client'
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface AuthState {
  token: string | null
  athleteId: string | null
}

interface AuthContextValue extends AuthState {
  login: (token: string, athleteId: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, athleteId: null })

  useEffect(() => {
    const token = localStorage.getItem('token')
    const athleteId = localStorage.getItem('athlete_id')
    if (token && athleteId) setAuth({ token, athleteId })
  }, [])

  function login(token: string, athleteId: string) {
    localStorage.setItem('token', token)
    localStorage.setItem('athlete_id', athleteId)
    setAuth({ token, athleteId })
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('athlete_id')
    setAuth({ token: null, athleteId: null })
  }

  return (
    <AuthContext.Provider value={{ ...auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- src/lib/__tests__/auth.test.tsx
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/lib/auth.tsx frontend/src/lib/__tests__/auth.test.tsx
git commit -m "feat: add AuthContext with localStorage persistence"
```

---

## Task 6: Root layout + TopNav + ProtectedRoute

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/components/top-nav.tsx`
- Create: `frontend/src/components/protected-route.tsx`

> **IMPORTANT:** Use the `frontend-design` skill when implementing TopNav. The component should be polished, professional, and match the dark/light aesthetic from the spec.

- [ ] **Step 1: Write tests for ProtectedRoute**

```typescript
// frontend/src/components/__tests__/protected-route.test.tsx
import { describe, it, expect, vi } from 'vitest'
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/components/__tests__/protected-route.test.tsx
```

Expected: FAIL — `Cannot find module '../protected-route'`

- [ ] **Step 3: Implement ProtectedRoute**

```typescript
// frontend/src/components/protected-route.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (token === null) router.replace('/login')
  }, [token, router])

  if (token === null) return null
  return <>{children}</>
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npm test -- src/components/__tests__/protected-route.test.tsx
```

Expected: 2 passed

- [ ] **Step 5: Implement TopNav**

> Use `frontend-design` skill for this component. Requirements:
> - Top navigation bar with logo `RESILIO+` on the left
> - Nav links: Dashboard (`/dashboard`), Plan (`/plan`), Review (`/review`) — only shown when authenticated
> - Dark/light mode toggle button (using `next-themes` `useTheme`)
> - User display (athlete_id truncated or "Account") + Logout button — only shown when authenticated
> - Active link styling (underline or accent color)
> - Responsive: links collapse to a menu icon on mobile (< 768px)

```typescript
// frontend/src/components/top-nav.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from 'next-themes'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Moon, Sun } from 'lucide-react'

const NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/plan', label: 'Plan' },
  { href: '/review', label: 'Review' },
]

export function TopNav() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { token, logout } = useAuth()

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-6 px-4">
        <Link href="/" className="font-bold tracking-widest text-primary">
          RESILIO+
        </Link>

        {token && (
          <nav className="hidden gap-6 md:flex">
            {NAV_LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  pathname === href
                    ? 'text-foreground border-b-2 border-primary pb-0.5'
                    : 'text-muted-foreground'
                }`}
              >
                {label}
              </Link>
            ))}
          </nav>
        )}

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
          {token && (
            <Button variant="ghost" size="sm" onClick={logout}>
              Logout
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
```

- [ ] **Step 6: Install lucide-react (icons)**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm install lucide-react
```

- [ ] **Step 7: Update root layout**

```typescript
// frontend/src/app/layout.tsx
import type { Metadata } from 'next'
import { GeistSans } from 'geist/font/sans'
import { ThemeProvider } from 'next-themes'
import { AuthProvider } from '@/lib/auth'
import { TopNav } from '@/components/top-nav'
import './globals.css'

export const metadata: Metadata = {
  title: 'Resilio+',
  description: 'AI-powered hybrid athlete coaching',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={GeistSans.className}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <AuthProvider>
            <TopNav />
            <main className="mx-auto max-w-screen-xl px-4 py-8">
              {children}
            </main>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 8: Install geist font**

```bash
npm install geist
```

- [ ] **Step 9: Run all tests**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test
```

Expected: all tests pass

- [ ] **Step 10: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/
git commit -m "feat: add TopNav, ProtectedRoute, and root layout"
```

---

## Task 7: Root redirect + Login page

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/login/__tests__/page.test.tsx`

> **IMPORTANT:** Use the `frontend-design` skill when implementing LoginPage.

- [ ] **Step 1: Write failing tests for LoginPage**

```typescript
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/login/__tests__/page.test.tsx
```

Expected: FAIL — `Cannot find module '../page'`

- [ ] **Step 3: Implement LoginPage**

> Use `frontend-design` skill. Requirements: centered card layout, dark background, RESILIO+ heading, email + password fields with labels, "Sign in" button, link to `/onboarding`, error message area.

```typescript
// frontend/src/app/login/page.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function LoginPage() {
  const router = useRouter()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.login(email, password)
      login(res.access_token, res.athlete_id)
      router.replace('/dashboard')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Invalid credentials. Check your email and password.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl font-bold tracking-widest text-primary">RESILIO+</CardTitle>
          <CardDescription>Sign in to your coaching dashboard</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              No account?{' '}
              <Link href="/onboarding" className="text-primary hover:underline">
                Get started
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Implement root redirect page**

```typescript
// frontend/src/app/page.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'

export default function RootPage() {
  const router = useRouter()
  const { token } = useAuth()

  useEffect(() => {
    router.replace(token ? '/dashboard' : '/onboarding')
  }, [token, router])

  return null
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/login/__tests__/page.test.tsx
```

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/app/page.tsx frontend/src/app/login/
git commit -m "feat: add login page and root redirect"
```

---

## Task 8: Onboarding wizard

**Files:**
- Create: `frontend/src/app/onboarding/page.tsx`
- Create: `frontend/src/app/onboarding/__tests__/page.test.tsx`

> **IMPORTANT:** Use the `frontend-design` skill when implementing OnboardingPage. The wizard should feel premium — progress indicator, clear step labels, smooth transitions between steps.

- [ ] **Step 1: Write failing tests**

```typescript
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
    fireEvent.change(screen.getByLabelText(/hours per week/i), { target: { value: '8' } })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 3 — submit
    fireEvent.click(screen.getByRole('button', { name: /generate my plan/i }))

    await waitFor(() => expect(screen.getByText(/email already in use/i)).toBeInTheDocument())
  })

  it('stores token and redirects to /dashboard on success', async () => {
    vi.mocked(apiModule.api.onboarding).mockResolvedValueOnce({
      athlete: {},
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
    fireEvent.change(screen.getByLabelText(/hours per week/i), { target: { value: '8' } })
    fireEvent.click(screen.getByRole('button', { name: /continue/i }))

    // Step 3
    fireEvent.click(screen.getByRole('button', { name: /generate my plan/i }))

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/dashboard')
      expect(localStorage.getItem('token')).toBe('tok123')
    })
  })
})
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/onboarding/__tests__/page.test.tsx
```

Expected: FAIL — `Cannot find module '../page'`

- [ ] **Step 3: Implement OnboardingPage**

> Use `frontend-design` skill. Requirements:
> - 3-step progress indicator at top (numbered circles + connecting lines, active step highlighted)
> - Step 1: Email + Password (min 8 chars validation)
> - Step 2: Name, Age (number), Sex (select: M/F/other), Weight kg, Height cm, Primary sport (select), Sports (checkboxes), Goals (text, comma-separated hint), Available days (Mon–Sun checkboxes), Hours/week
> - Step 3: Plan start date (date input, default = next Monday), "Generate my plan" button
> - "Back" button on steps 2 and 3
> - Error banner below form on submission failure

```typescript
// frontend/src/app/onboarding/page.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type Sport } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const SPORTS: { value: Sport; label: string }[] = [
  { value: 'running', label: 'Running' },
  { value: 'lifting', label: 'Lifting' },
  { value: 'swimming', label: 'Swimming' },
  { value: 'biking', label: 'Biking' },
]

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function nextMonday(): string {
  const d = new Date()
  const day = d.getDay()
  const daysUntilMonday = day === 0 ? 1 : 8 - day
  d.setDate(d.getDate() + daysUntilMonday)
  return d.toISOString().split('T')[0]
}

interface FormData {
  // Step 1
  email: string
  password: string
  // Step 2
  name: string
  age: string
  sex: 'M' | 'F' | 'other'
  weight_kg: string
  height_cm: string
  primary_sport: Sport
  sports: Sport[]
  goals: string
  available_days: number[]
  hours_per_week: string
  // Step 3
  plan_start_date: string
}

const INITIAL: FormData = {
  email: '', password: '', name: '', age: '', sex: 'M',
  weight_kg: '', height_cm: '', primary_sport: 'running', sports: ['running'],
  goals: '', available_days: [0, 1, 2, 3, 4], hours_per_week: '',
  plan_start_date: nextMonday(),
}

export default function OnboardingPage() {
  const router = useRouter()
  const { login } = useAuth()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormData>(INITIAL)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(key: keyof FormData, value: unknown) {
    setForm(f => ({ ...f, [key]: value }))
  }

  function toggleSport(sport: Sport) {
    set('sports', form.sports.includes(sport)
      ? form.sports.filter(s => s !== sport)
      : [...form.sports, sport])
  }

  function toggleDay(day: number) {
    set('available_days', form.available_days.includes(day)
      ? form.available_days.filter(d => d !== day)
      : [...form.available_days, day].sort())
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.onboarding({
        email: form.email,
        password: form.password,
        plan_start_date: form.plan_start_date,
        name: form.name,
        age: parseInt(form.age),
        sex: form.sex,
        weight_kg: parseFloat(form.weight_kg),
        height_cm: parseFloat(form.height_cm),
        primary_sport: form.primary_sport,
        sports: form.sports.length > 0 ? form.sports : [form.primary_sport],
        goals: form.goals.split(',').map(g => g.trim()).filter(Boolean),
        available_days: form.available_days,
        hours_per_week: parseFloat(form.hours_per_week),
      })
      login(res.access_token, res.athlete.id as string)
      router.replace('/dashboard')
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('Email already in use. Sign in instead.')
      } else if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const stepTitles = ['Account', 'Athlete Profile', 'Your Plan']

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl font-bold tracking-widest text-primary">RESILIO+</CardTitle>
          <CardDescription>Set up your coaching profile</CardDescription>
          {/* Step indicator */}
          <div className="flex items-center gap-2 pt-2">
            {[1, 2, 3].map(n => (
              <div key={n} className="flex items-center gap-2">
                <div className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                  step === n ? 'bg-primary text-primary-foreground' : step > n ? 'bg-primary/40 text-primary-foreground' : 'bg-muted text-muted-foreground'
                }`}>{n}</div>
                <span className={`text-xs ${step === n ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                  {stepTitles[n - 1]}
                </span>
                {n < 3 && <div className="h-px w-8 bg-border" />}
              </div>
            ))}
          </div>
        </CardHeader>

        <CardContent>
          {step === 1 && (
            <form onSubmit={e => { e.preventDefault(); setStep(2) }} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={form.email} onChange={e => set('email', e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={form.password} onChange={e => set('password', e.target.value)} required minLength={8} />
                <p className="text-xs text-muted-foreground">Minimum 8 characters</p>
              </div>
              <Button type="submit" className="w-full">Continue →</Button>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={e => { e.preventDefault(); setStep(3) }} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" value={form.name} onChange={e => set('name', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="age">Age</Label>
                  <Input id="age" type="number" min={14} max={100} value={form.age} onChange={e => set('age', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight">Weight (kg)</Label>
                  <Input id="weight" type="number" step="0.1" value={form.weight_kg} onChange={e => set('weight_kg', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="height">Height (cm)</Label>
                  <Input id="height" type="number" value={form.height_cm} onChange={e => set('height_cm', e.target.value)} required />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="sex">Sex</Label>
                <select id="sex" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm" value={form.sex} onChange={e => set('sex', e.target.value as 'M' | 'F' | 'other')}>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="primary_sport">Primary sport</Label>
                <select id="primary_sport" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm" value={form.primary_sport} onChange={e => { const s = e.target.value as Sport; set('primary_sport', s); if (!form.sports.includes(s)) set('sports', [...form.sports, s]) }}>
                  {SPORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>

              <div className="space-y-2">
                <Label>Sports you train</Label>
                <div className="flex gap-3 flex-wrap">
                  {SPORTS.map(s => (
                    <label key={s.value} className="flex items-center gap-1.5 text-sm">
                      <input type="checkbox" checked={form.sports.includes(s.value)} onChange={() => toggleSport(s.value)} />
                      {s.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="goals">Goals <span className="text-muted-foreground text-xs">(comma-separated)</span></Label>
                <Input id="goals" placeholder="e.g. Run a 5K, Build muscle" value={form.goals} onChange={e => set('goals', e.target.value)} required />
              </div>

              <div className="space-y-2">
                <Label>Available days</Label>
                <div className="flex gap-2">
                  {DAYS.map((d, i) => (
                    <label key={i} className="flex flex-col items-center gap-1 text-xs">
                      <input type="checkbox" checked={form.available_days.includes(i)} onChange={() => toggleDay(i)} />
                      {d}
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="hours_per_week">Hours per week</Label>
                <Input id="hours_per_week" type="number" min={1} step="0.5" value={form.hours_per_week} onChange={e => set('hours_per_week', e.target.value)} required />
              </div>

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setStep(1)}>← Back</Button>
                <Button type="submit" className="flex-1">Continue →</Button>
              </div>
            </form>
          )}

          {step === 3 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="plan_start_date">Plan start date</Label>
                <Input id="plan_start_date" type="date" value={form.plan_start_date} onChange={e => set('plan_start_date', e.target.value)} required />
                <p className="text-xs text-muted-foreground">Your first week starts on this date.</p>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setStep(2)}>← Back</Button>
                <Button type="submit" className="flex-1" disabled={loading}>
                  {loading ? 'Generating…' : 'Generate my plan →'}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/onboarding/__tests__/page.test.tsx
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/app/onboarding/
git commit -m "feat: add 3-step onboarding wizard"
```

---

## Task 9: Dashboard page

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/dashboard/__tests__/page.test.tsx`

> **IMPORTANT:** Use the `frontend-design` skill when implementing DashboardPage. Progress-first layout: big completion %, progress bar as hero, ACWR badge with color coding (green < 0.8, amber 0.8–1.3, red > 1.3), next session card.

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/src/app/dashboard/__tests__/page.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
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
    await act(async () => {})
    expect(screen.getByText(/72/)).toBeInTheDocument()  // completion_pct
    expect(screen.getByText(/8\.5/)).toBeInTheDocument()  // planned_hours
    expect(screen.getByText(/6\.2/)).toBeInTheDocument()  // actual_hours
  })

  it('shows ACWR value', async () => {
    vi.mocked(apiModule.api.getWeekStatus).mockResolvedValueOnce(MOCK_STATUS)
    renderDashboard()
    await act(async () => {})
    expect(screen.getByText(/1\.12/)).toBeInTheDocument()
  })

  it('shows "no plan" empty state when 404', async () => {
    const { ApiError } = await import('@/lib/api')
    vi.mocked(apiModule.api.getWeekStatus).mockRejectedValueOnce(new ApiError(404, 'No plan'))
    renderDashboard()
    await act(async () => {})
    expect(screen.getByText(/no plan/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/dashboard/__tests__/page.test.tsx
```

Expected: FAIL — `Cannot find module '../page'`

- [ ] **Step 3: Implement DashboardPage**

> Use `frontend-design` skill. Layout:
> - Header: `Week N of M · PHASE` (use `plan.phase`, estimate total weeks from `plan.end_date - plan.start_date`)
> - Hero: large `completion_pct%` + progress bar
> - Metric cards: Planned Xh / Actual Xh / ACWR (colored badge)
> - Next session card (first session with date ≥ today, or "Week complete 🎉")
> - Link to `/plan` and `/review`

```typescript
// frontend/src/app/dashboard/page.tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type WeekStatusResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

function acwrColor(acwr: number | null): string {
  if (acwr === null) return 'secondary'
  if (acwr < 0.8) return 'secondary'
  if (acwr <= 1.3) return 'default'
  return 'destructive'
}

function nextSession(status: WeekStatusResponse) {
  const today = new Date().toISOString().split('T')[0]
  return status.plan.sessions.find(s => s.date >= today) ?? null
}

export default function DashboardPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [status, setStatus] = useState<WeekStatusResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId) return
    api.getWeekStatus(athleteId)
      .then(setStatus)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError('Failed to load week status.')
      })
  }, [athleteId, logout, router])

  return (
    <ProtectedRoute>
      {notFound && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-muted-foreground">No plan active yet.</p>
          <Button asChild><Link href="/plan">Generate a plan</Link></Button>
        </div>
      )}

      {error && <p className="text-destructive">{error}</p>}

      {!status && !notFound && !error && (
        <p className="text-muted-foreground animate-pulse">Loading…</p>
      )}

      {status && (
        <div className="space-y-6">
          <div>
            <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
              Week {status.week_number} · {status.plan.phase.toUpperCase()}
            </p>
            <div className="mt-2 flex items-end gap-3">
              <span className="text-6xl font-bold tabular-nums">
                {Math.round(status.completion_pct)}
              </span>
              <span className="mb-2 text-2xl text-muted-foreground">%</span>
              <span className="mb-2 text-muted-foreground">complete</span>
            </div>
            <Progress value={status.completion_pct} className="mt-3 h-2" />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">Planned</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{status.planned_hours}<span className="text-sm text-muted-foreground">h</span></p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">Actual</CardTitle></CardHeader>
              <CardContent><p className="text-2xl font-bold">{status.actual_hours}<span className="text-sm text-muted-foreground">h</span></p></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">ACWR</CardTitle></CardHeader>
              <CardContent>
                <Badge variant={acwrColor(status.acwr) as 'default' | 'secondary' | 'destructive'} className="text-base">
                  {status.acwr?.toFixed(2) ?? '—'}
                </Badge>
              </CardContent>
            </Card>
          </div>

          {(() => {
            const next = nextSession(status)
            return (
              <Card>
                <CardHeader><CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Next Session</CardTitle></CardHeader>
                <CardContent>
                  {next ? (
                    <div>
                      <p className="text-lg font-semibold">{next.workout_type}</p>
                      <p className="text-sm text-muted-foreground">{next.date} · {next.duration_min} min · {next.sport}</p>
                    </div>
                  ) : (
                    <p className="text-muted-foreground">Week complete 🎉</p>
                  )}
                </CardContent>
              </Card>
            )
          })()}

          <div className="flex gap-3">
            <Button asChild variant="outline"><Link href="/plan">View full plan</Link></Button>
            <Button asChild><Link href="/review">Weekly review →</Link></Button>
          </div>
        </div>
      )}
    </ProtectedRoute>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/dashboard/__tests__/page.test.tsx
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/app/dashboard/
git commit -m "feat: add progress-first dashboard page"
```

---

## Task 10: Plan page

**Files:**
- Create: `frontend/src/app/plan/page.tsx`
- Create: `frontend/src/app/plan/__tests__/page.test.tsx`

> **IMPORTANT:** Use the `frontend-design` skill when implementing PlanPage. Sessions grouped by day, each session card shows sport icon/badge, workout type, duration, intensity notes.

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/src/app/plan/__tests__/page.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import PlanPage from '../page'
import { AuthProvider } from '@/lib/auth'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  api: { getPlan: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message) }
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/plan',
}))

const MOCK_PLAN: apiModule.TrainingPlanResponse = {
  id: 'p1', athlete_id: 'a1', start_date: '2026-04-14', end_date: '2026-04-20',
  phase: 'build', total_weekly_hours: 8.5, acwr: 1.0,
  sessions: [
    { date: '2026-04-14', sport: 'running', workout_type: 'Easy Run', duration_min: 45, fatigue_score: { local_muscular: 20, cns_load: 10, metabolic_cost: 30, recovery_hours: 8, affected_muscles: [] }, notes: 'Zone 2' },
    { date: '2026-04-15', sport: 'lifting', workout_type: 'Squat + Deadlift', duration_min: 60, fatigue_score: { local_muscular: 70, cns_load: 60, metabolic_cost: 20, recovery_hours: 48, affected_muscles: ['quads', 'hamstrings'] }, notes: '5x5' },
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
    await act(async () => {})
    expect(screen.getByText(/Easy Run/)).toBeInTheDocument()
    expect(screen.getByText(/Squat \+ Deadlift/)).toBeInTheDocument()
  })

  it('renders phase and total hours', async () => {
    vi.mocked(apiModule.api.getPlan).mockResolvedValueOnce(MOCK_PLAN)
    renderPlan()
    await act(async () => {})
    expect(screen.getByText(/build/i)).toBeInTheDocument()
    expect(screen.getByText(/8\.5/)).toBeInTheDocument()
  })

  it('shows "no plan" empty state on 404', async () => {
    const { ApiError } = await import('@/lib/api')
    vi.mocked(apiModule.api.getPlan).mockRejectedValueOnce(new ApiError(404, 'Not found'))
    renderPlan()
    await act(async () => {})
    expect(screen.getByText(/no plan/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/plan/__tests__/page.test.tsx
```

Expected: FAIL — `Cannot find module '../page'`

- [ ] **Step 3: Implement PlanPage**

> Use `frontend-design` skill. Layout: header with phase + total hours, sessions as cards grouped by date (show full date label e.g. "Monday Apr 14"). Each card: sport badge, workout type title, duration + notes.

```typescript
// frontend/src/app/plan/page.tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type TrainingPlanResponse, type WorkoutSlot } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const SPORT_COLORS: Record<string, string> = {
  running: 'bg-emerald-500/20 text-emerald-400',
  lifting: 'bg-purple-500/20 text-purple-400',
  swimming: 'bg-blue-500/20 text-blue-400',
  biking: 'bg-orange-500/20 text-orange-400',
}

function formatDate(iso: string): string {
  return new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
}

function groupByDate(sessions: WorkoutSlot[]): [string, WorkoutSlot[]][] {
  const map = new Map<string, WorkoutSlot[]>()
  for (const s of sessions) {
    const arr = map.get(s.date) ?? []
    arr.push(s)
    map.set(s.date, arr)
  }
  return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
}

export default function PlanPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [plan, setPlan] = useState<TrainingPlanResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId) return
    api.getPlan(athleteId)
      .then(setPlan)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError('Failed to load plan.')
      })
  }, [athleteId, logout, router])

  return (
    <ProtectedRoute>
      {notFound && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-muted-foreground">No plan active. Generate one first.</p>
          <Button asChild><Link href="/dashboard">Go to dashboard</Link></Button>
        </div>
      )}
      {error && <p className="text-destructive">{error}</p>}
      {!plan && !notFound && !error && <p className="animate-pulse text-muted-foreground">Loading…</p>}
      {plan && (
        <div className="space-y-6">
          <div>
            <p className="text-sm uppercase tracking-widest text-muted-foreground">
              {plan.phase.toUpperCase()} · {plan.start_date} — {plan.end_date}
            </p>
            <h1 className="text-3xl font-bold">Training Plan</h1>
            <p className="mt-1 text-muted-foreground">{plan.total_weekly_hours}h total · ACWR {plan.acwr.toFixed(2)}</p>
          </div>

          <div className="space-y-6">
            {groupByDate(plan.sessions).map(([date, sessions]) => (
              <div key={date}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">{formatDate(date)}</h2>
                <div className="space-y-2">
                  {sessions.map((s, i) => (
                    <Card key={i}>
                      <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SPORT_COLORS[s.sport] ?? ''}`}>{s.sport}</span>
                          <CardTitle className="text-base">{s.workout_type}</CardTitle>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-muted-foreground">{s.duration_min} min{s.notes ? ` · ${s.notes}` : ''}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </ProtectedRoute>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/plan/__tests__/page.test.tsx
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/app/plan/
git commit -m "feat: add training plan page with sessions grouped by day"
```

---

## Task 11: Review page

**Files:**
- Create: `frontend/src/app/review/page.tsx`
- Create: `frontend/src/app/review/__tests__/page.test.tsx`

> **IMPORTANT:** Use the `frontend-design` skill when implementing ReviewPage. Inputs: readiness slider (1–10), HRV (optional), sleep hours (optional), comment textarea. After submit: show ACWR, adjustment, and `next_week_suggestion` in a styled result card.

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/src/app/review/__tests__/page.test.tsx
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
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/review/__tests__/page.test.tsx
```

Expected: FAIL — `Cannot find module '../page'`

- [ ] **Step 3: Implement ReviewPage**

> Use `frontend-design` skill. Layout: form on top, result card below (shown after submit). The result card highlights `next_week_suggestion` prominently. ACWR value colored: green if ≤ 1.0, amber 1.0–1.3, red > 1.3.

```typescript
// frontend/src/app/review/page.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type WeeklyReviewResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

function lastSunday(): string {
  const d = new Date()
  const day = d.getDay()
  d.setDate(d.getDate() - (day === 0 ? 0 : day))
  return d.toISOString().split('T')[0]
}

export default function ReviewPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [weekEndDate, setWeekEndDate] = useState(lastSunday())
  const [readiness, setReadiness] = useState<string>('')
  const [hrv, setHrv] = useState<string>('')
  const [sleep, setSleep] = useState<string>('')
  const [comment, setComment] = useState('')
  const [result, setResult] = useState<WeeklyReviewResponse | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!athleteId) return
    setError('')
    setLoading(true)
    try {
      const res = await api.submitReview(athleteId, {
        week_end_date: weekEndDate,
        readiness_score: readiness ? parseFloat(readiness) : undefined,
        hrv_rmssd: hrv ? parseFloat(hrv) : undefined,
        sleep_hours_avg: sleep ? parseFloat(sleep) : undefined,
        comment,
      })
      setResult(res)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      else if (err instanceof ApiError) setError(err.message)
      else setError('Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="mx-auto max-w-lg space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Weekly Review</h1>
          <p className="mt-1 text-muted-foreground">Log how your week went and get next week's adjustment.</p>
        </div>

        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="week_end_date">Week end date</Label>
                <Input id="week_end_date" type="date" value={weekEndDate} onChange={e => setWeekEndDate(e.target.value)} required />
              </div>

              <div className="space-y-2">
                <Label htmlFor="readiness">Readiness score <span className="text-muted-foreground text-xs">(1–10, optional)</span></Label>
                <Input id="readiness" type="number" min={1} max={10} step="0.5" value={readiness} onChange={e => setReadiness(e.target.value)} placeholder="e.g. 7.5" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="hrv">HRV rMSSD <span className="text-muted-foreground text-xs">(optional)</span></Label>
                  <Input id="hrv" type="number" step="0.1" value={hrv} onChange={e => setHrv(e.target.value)} placeholder="ms" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sleep">Sleep avg <span className="text-muted-foreground text-xs">(optional)</span></Label>
                  <Input id="sleep" type="number" step="0.5" value={sleep} onChange={e => setSleep(e.target.value)} placeholder="hours" />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="comment">Comment <span className="text-muted-foreground text-xs">(optional)</span></Label>
                <textarea
                  id="comment"
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                  placeholder="How did the week feel?"
                />
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Submitting…' : 'Submit review →'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {result && (
          <Card className="border-primary/30 bg-primary/5">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-wider text-muted-foreground">Week {result.week_number} Summary</CardTitle>
              <CardDescription className="text-base font-medium text-foreground mt-1">
                {result.next_week_suggestion}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Planned</p>
                  <p className="text-xl font-bold">{result.planned_hours}h</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">Actual</p>
                  <p className="text-xl font-bold">{result.actual_hours}h</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-muted-foreground">ACWR</p>
                  <p className={`text-xl font-bold ${result.acwr > 1.3 ? 'text-destructive' : result.acwr >= 0.8 ? 'text-amber-500' : 'text-emerald-500'}`}>
                    {result.acwr.toFixed(2)}
                  </p>
                </div>
              </div>
              {result.adjustment_applied !== 1.0 && (
                <p className="mt-3 text-sm text-muted-foreground text-center">
                  Next week volume: {result.adjustment_applied < 1 ? '↓' : '↑'} {Math.round(Math.abs(1 - result.adjustment_applied) * 100)}%
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test -- src/app/review/__tests__/page.test.tsx
```

Expected: 3 passed

- [ ] **Step 5: Run full test suite**

```bash
cd /c/Users/simon/resilio-plus/frontend
npm test
```

Expected: all tests pass (≥ 20 tests)

- [ ] **Step 6: Commit**

```bash
cd /c/Users/simon/resilio-plus
git add frontend/src/app/review/
git commit -m "feat: add weekly review page with ACWR adjustment display"
```

---

## Final Verification

- [ ] **Run full backend test suite to confirm nothing regressed**

```bash
cd /c/Users/simon/resilio-plus
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe" tests/backend/ -q --tb=no
```

Expected: 286 passed, 1 pre-existing failure

- [ ] **Start backend and verify frontend connects**

```bash
# Terminal 1 — start backend
cd /c/Users/simon/resilio-plus
"/c/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/uvicorn.exe" backend.app.main:app --reload

# Terminal 2 — start frontend
cd /c/Users/simon/resilio-plus/frontend
npm run dev
```

Open `http://localhost:3000` — should redirect to `/onboarding`.

- [ ] **Final commit if any cleanup needed**

```bash
cd /c/Users/simon/resilio-plus
git add -p
git commit -m "chore: Phase 5 final cleanup"
```
