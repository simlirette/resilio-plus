# S-6 Frontend Tracking Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Tracking Only frontend — `/tracking` (active plan viewer) and `/tracking/import` (file import wizard) — visible only in `tracking_only` mode, with a mode badge in TopNav.

**Architecture:** Extend auth context with `coachingMode` fetched from `GET /athletes/{id}`; add ExternalPlan API types + methods in `api.ts`; conditionally render Tracking nav items in TopNav; two new protected pages using existing shadcn/ui components. S-2 import endpoints are stubbed.

**Tech Stack:** Next.js (App Router), TypeScript, shadcn/ui (Card, Badge, Button, Input), lucide-react, existing `api.ts` + `auth.tsx` patterns.

---

## Task 1: Add ExternalPlan types + methods to api.ts

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add types after the existing `EnergySnapshotSummary` block**

Open `frontend/src/lib/api.ts`. After line 345 (end of `EnergySnapshotSummary`), add:

```ts
// ── ExternalPlan ───────────────────────────────────────────────────────────

export interface AthleteProfile {
  id: string
  name: string
  coaching_mode: 'full' | 'tracking_only'
}

export interface ExternalSessionOut {
  id: string
  plan_id: string
  athlete_id: string
  session_date: string
  sport: string
  title: string
  description: string | null
  duration_min: number | null
  status: string
}

export interface ExternalPlanOut {
  id: string
  athlete_id: string
  title: string
  source: string
  status: string
  start_date: string | null
  end_date: string | null
  created_at: string
  sessions: ExternalSessionOut[]
}

export interface ExternalPlanCreate {
  title: string
  start_date?: string
  end_date?: string
}

export interface ExternalSessionCreate {
  session_date: string
  sport: string
  title: string
  description?: string
  duration_min?: number
}

export interface ExternalSessionUpdate {
  session_date?: string
  sport?: string
  title?: string
  description?: string
  duration_min?: number
  status?: 'planned' | 'completed' | 'skipped'
}

export interface ExternalPlanDraft {
  title: string
  sessions_parsed: number
  sessions: ExternalSessionCreate[]
  parse_warnings: string[]
}
```

- [ ] **Step 2: Add API methods inside the `api` object**

Inside the `api = { ... }` object, after `confirmImportExternalPlan` (at the end, before the closing `}`), add:

```ts
  getAthleteProfile: (athleteId: string) =>
    request<AthleteProfile>(`/athletes/${athleteId}`),

  getExternalPlan: (athleteId: string) =>
    request<ExternalPlanOut>(`/athletes/${athleteId}/external-plan`),

  createExternalPlan: (athleteId: string, data: ExternalPlanCreate) =>
    request<ExternalPlanOut>(`/athletes/${athleteId}/external-plan`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  addExternalSession: (athleteId: string, data: ExternalSessionCreate) =>
    request<ExternalSessionOut>(`/athletes/${athleteId}/external-plan/sessions`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateExternalSession: (athleteId: string, sessionId: string, data: ExternalSessionUpdate) =>
    request<ExternalSessionOut>(`/athletes/${athleteId}/external-plan/sessions/${sessionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteExternalSession: (athleteId: string, sessionId: string): Promise<void> =>
    request(`/athletes/${athleteId}/external-plan/sessions/${sessionId}`, { method: 'DELETE' }),

  // ── S-2 STUBS ─────────────────────────────────────────────────────────────
  // POST /athletes/{id}/external-plan/import is not yet implemented (S-2 scope).
  // These stubs simulate the API with mock data.

  importExternalPlan: (_athleteId: string, _file: File): Promise<ExternalPlanDraft> => {
    console.log('[STUB] S-2 not implemented: importExternalPlan')
    return new Promise(resolve =>
      setTimeout(() => resolve({
        title: 'Plan importé (démo)',
        sessions_parsed: 3,
        sessions: [
          { session_date: new Date().toISOString().split('T')[0], sport: 'running', title: 'Easy run 45min', duration_min: 45 },
          { session_date: new Date(Date.now() + 2 * 86400000).toISOString().split('T')[0], sport: 'lifting', title: 'Full body strength', duration_min: 60 },
          { session_date: new Date(Date.now() + 4 * 86400000).toISOString().split('T')[0], sport: 'running', title: 'Tempo intervals', duration_min: 55 },
        ],
        parse_warnings: ['[DÉMO] Endpoint S-2 non implémenté — données fictives'],
      }), 800)
    )
  },

  confirmImportExternalPlan: (athleteId: string, _draft: ExternalPlanDraft): Promise<ExternalPlanOut> => {
    console.log('[STUB] S-2 not implemented: confirmImportExternalPlan')
    return new Promise(resolve =>
      setTimeout(() => resolve({
        id: 'stub-plan-id',
        athlete_id: athleteId,
        title: 'Plan importé (démo)',
        source: 'file',
        status: 'active',
        start_date: new Date().toISOString().split('T')[0],
        end_date: null,
        created_at: new Date().toISOString(),
        sessions: [],
      }), 500)
    )
  },
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. If errors, fix types before continuing.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/lib/api.ts
git commit -m "feat(s6): add ExternalPlan types + API methods (import endpoints stubbed)"
```

---

## Task 2: Add coachingMode to auth context

**Files:**
- Modify: `frontend/src/lib/auth.tsx`

- [ ] **Step 1: Replace the entire auth.tsx file**

Replace `frontend/src/lib/auth.tsx` with:

```tsx
// frontend/src/lib/auth.tsx
'use client'
import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { api } from './api'

interface AuthState {
  token: string | null
  athleteId: string | null
  coachingMode: 'full' | 'tracking_only' | null
}

interface AuthContextValue extends AuthState {
  login: (token: string, athleteId: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function fetchCoachingMode(athleteId: string): Promise<'full' | 'tracking_only'> {
  try {
    const profile = await api.getAthleteProfile(athleteId)
    return profile.coaching_mode
  } catch {
    return 'full'
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, athleteId: null, coachingMode: null })

  useEffect(() => {
    const token = localStorage.getItem('token')
    const athleteId = localStorage.getItem('athlete_id')
    const storedMode = localStorage.getItem('coaching_mode') as 'full' | 'tracking_only' | null
    if (token && athleteId) {
      setAuth({ token, athleteId, coachingMode: storedMode })
      fetchCoachingMode(athleteId).then(mode => {
        localStorage.setItem('coaching_mode', mode)
        setAuth(prev => ({ ...prev, coachingMode: mode }))
      })
    }
  }, [])

  const login = useCallback((token: string, athleteId: string) => {
    localStorage.setItem('token', token)
    localStorage.setItem('athlete_id', athleteId)
    setAuth({ token, athleteId, coachingMode: null })
    fetchCoachingMode(athleteId).then(mode => {
      localStorage.setItem('coaching_mode', mode)
      setAuth(prev => ({ ...prev, coachingMode: mode }))
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('athlete_id')
    localStorage.removeItem('coaching_mode')
    setAuth({ token: null, athleteId: null, coachingMode: null })
  }, [])

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

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/lib/auth.tsx
git commit -m "feat(s6): add coachingMode to auth context, fetch from GET /athletes/{id}"
```

---

## Task 3: Add mode badge + Tracking link to TopNav

**Files:**
- Modify: `frontend/src/components/top-nav.tsx`

- [ ] **Step 1: Replace the entire top-nav.tsx file**

Replace `frontend/src/components/top-nav.tsx` with:

```tsx
// frontend/src/components/top-nav.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from 'next-themes'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Moon, Sun } from 'lucide-react'

const BASE_NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/energy', label: 'Energy' },
  { href: '/check-in', label: 'Check-in' },
  { href: '/plan', label: 'Plan' },
  { href: '/review', label: 'Review' },
  { href: '/history', label: 'History' },
  { href: '/analytics', label: 'Analytics' },
  { href: '/settings/connectors', label: 'Settings' },
]

const TRACKING_LINK = { href: '/tracking', label: 'Tracking' }

export function TopNav() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { token, logout, coachingMode } = useAuth()

  const navLinks = coachingMode === 'tracking_only'
    ? [...BASE_NAV_LINKS, TRACKING_LINK]
    : BASE_NAV_LINKS

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-widest text-primary">
          RESILIO+
          {coachingMode === 'tracking_only' && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-semibold tracking-wider border-amber-500 text-amber-500">
              TRACKING
            </Badge>
          )}
        </Link>

        {token && (
          <nav className="hidden gap-6 md:flex">
            {navLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  pathname === href || pathname.startsWith(href + '/')
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

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/components/top-nav.tsx
git commit -m "feat(s6): add TRACKING mode badge + conditional Tracking nav link in TopNav"
```

---

## Task 4: Create tracking/page.tsx — ExternalPlan viewer

**Files:**
- Create: `frontend/src/app/tracking/page.tsx`

- [ ] **Step 1: Create the file with complete implementation**

Create `frontend/src/app/tracking/page.tsx`:

```tsx
// frontend/src/app/tracking/page.tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import {
  api,
  ApiError,
  type ExternalPlanOut,
  type ExternalSessionOut,
  type ExternalPlanCreate,
  type ExternalSessionCreate,
} from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

// ── Helpers ────────────────────────────────────────────────────────────────

const SPORT_LABELS: Record<string, string> = {
  running: 'Course',
  lifting: 'Musculation',
  swimming: 'Natation',
  biking: 'Vélo',
}

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  planned: 'outline',
  completed: 'default',
  skipped: 'secondary',
}

const STATUS_LABELS: Record<string, string> = {
  planned: 'Prévu',
  completed: 'Terminé',
  skipped: 'Sauté',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' })
}

// ── SessionRow ─────────────────────────────────────────────────────────────

function SessionRow({
  session,
  onUpdate,
}: {
  session: ExternalSessionOut
  onUpdate: (updated: ExternalSessionOut) => void
}) {
  const { athleteId } = useAuth()
  const [loading, setLoading] = useState<'complete' | 'skip' | null>(null)

  async function patch(status: 'completed' | 'skipped') {
    if (!athleteId) return
    setLoading(status === 'completed' ? 'complete' : 'skip')
    try {
      const updated = await api.updateExternalSession(athleteId, session.id, { status })
      onUpdate(updated)
    } finally {
      setLoading(null)
    }
  }

  const done = session.status === 'completed' || session.status === 'skipped'

  return (
    <div className="flex items-center gap-3 py-3 border-b last:border-0">
      <div className="w-24 text-xs text-muted-foreground shrink-0">{formatDate(session.session_date)}</div>
      <Badge variant="outline" className="text-xs shrink-0">
        {SPORT_LABELS[session.sport] ?? session.sport}
      </Badge>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{session.title}</p>
        {session.duration_min && (
          <p className="text-xs text-muted-foreground">{session.duration_min} min</p>
        )}
      </div>
      <Badge variant={STATUS_VARIANTS[session.status] ?? 'outline'} className="text-xs shrink-0">
        {STATUS_LABELS[session.status] ?? session.status}
      </Badge>
      {!done && (
        <div className="flex gap-1 shrink-0">
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-2 text-xs"
            disabled={loading !== null}
            onClick={() => patch('completed')}
          >
            {loading === 'complete' ? '…' : '✓'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs text-muted-foreground"
            disabled={loading !== null}
            onClick={() => patch('skipped')}
          >
            {loading === 'skip' ? '…' : '—'}
          </Button>
        </div>
      )}
    </div>
  )
}

// ── AddSessionForm ─────────────────────────────────────────────────────────

function AddSessionForm({ onAdd }: { onAdd: (session: ExternalSessionOut) => void }) {
  const { athleteId } = useAuth()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<ExternalSessionCreate>({
    session_date: new Date().toISOString().split('T')[0],
    sport: 'running',
    title: '',
    duration_min: undefined,
  })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!athleteId || !form.title) return
    setLoading(true)
    try {
      const session = await api.addExternalSession(athleteId, form)
      onAdd(session)
      setOpen(false)
      setForm({ session_date: new Date().toISOString().split('T')[0], sport: 'running', title: '', duration_min: undefined })
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)} className="mt-4">
        + Ajouter une séance
      </Button>
    )
  }

  return (
    <form onSubmit={submit} className="mt-4 p-4 border rounded-lg space-y-3">
      <p className="text-sm font-medium">Nouvelle séance</p>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label htmlFor="s-date" className="text-xs">Date</Label>
          <Input
            id="s-date"
            type="date"
            value={form.session_date}
            onChange={e => setForm(f => ({ ...f, session_date: e.target.value }))}
            required
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="s-sport" className="text-xs">Sport</Label>
          <select
            id="s-sport"
            value={form.sport}
            onChange={e => setForm(f => ({ ...f, sport: e.target.value }))}
            className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="running">Course</option>
            <option value="lifting">Musculation</option>
            <option value="swimming">Natation</option>
            <option value="biking">Vélo</option>
          </select>
        </div>
        <div className="space-y-1 col-span-2">
          <Label htmlFor="s-title" className="text-xs">Titre</Label>
          <Input
            id="s-title"
            placeholder="Ex : Easy run 45 min"
            value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            required
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="s-duration" className="text-xs">Durée (min)</Label>
          <Input
            id="s-duration"
            type="number"
            min={1}
            placeholder="45"
            value={form.duration_min ?? ''}
            onChange={e => setForm(f => ({ ...f, duration_min: e.target.value ? Number(e.target.value) : undefined }))}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={loading}>{loading ? 'Ajout…' : 'Ajouter'}</Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => setOpen(false)}>Annuler</Button>
      </div>
    </form>
  )
}

// ── CreatePlanForm ─────────────────────────────────────────────────────────

function CreatePlanForm({ onCreate }: { onCreate: (plan: ExternalPlanOut) => void }) {
  const { athleteId } = useAuth()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<ExternalPlanCreate>({ title: '', start_date: '', end_date: '' })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!athleteId || !form.title) return
    setLoading(true)
    try {
      const data: ExternalPlanCreate = {
        title: form.title,
        ...(form.start_date ? { start_date: form.start_date } : {}),
        ...(form.end_date ? { end_date: form.end_date } : {}),
      }
      const plan = await api.createExternalPlan(athleteId, data)
      onCreate(plan)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 max-w-md">
      <div className="space-y-1">
        <Label htmlFor="p-title" className="text-xs">Nom du plan</Label>
        <Input
          id="p-title"
          placeholder="Ex : Plan marathon printemps 2026"
          value={form.title}
          onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label htmlFor="p-start" className="text-xs">Début (optionnel)</Label>
          <Input
            id="p-start"
            type="date"
            value={form.start_date}
            onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="p-end" className="text-xs">Fin (optionnel)</Label>
          <Input
            id="p-end"
            type="date"
            value={form.end_date}
            onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))}
          />
        </div>
      </div>
      <Button type="submit" disabled={loading}>{loading ? 'Création…' : 'Créer le plan'}</Button>
    </form>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function TrackingPage() {
  const { athleteId, coachingMode } = useAuth()
  const router = useRouter()
  const [plan, setPlan] = useState<ExternalPlanOut | null>(null)
  const [noPlan, setNoPlan] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (coachingMode !== null && coachingMode !== 'tracking_only') {
      router.replace('/dashboard')
    }
  }, [coachingMode, router])

  useEffect(() => {
    if (!athleteId || coachingMode !== 'tracking_only') return
    api.getExternalPlan(athleteId)
      .then(setPlan)
      .catch(err => {
        if (err instanceof ApiError && err.status === 404) setNoPlan(true)
      })
      .finally(() => setLoading(false))
  }, [athleteId, coachingMode])

  function handleSessionUpdate(updated: ExternalSessionOut) {
    setPlan(p => p ? { ...p, sessions: p.sessions.map(s => s.id === updated.id ? updated : s) } : p)
  }

  function handleSessionAdd(session: ExternalSessionOut) {
    setPlan(p => p ? { ...p, sessions: [...p.sessions, session].sort((a, b) => a.session_date.localeCompare(b.session_date)) } : p)
  }

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Plan Externe</h1>
            <p className="text-sm text-muted-foreground mt-1">Mode Tracking Only</p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/tracking/import">Importer un plan</Link>
          </Button>
        </div>

        {loading && <p className="text-muted-foreground animate-pulse">Chargement…</p>}

        {!loading && noPlan && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Aucun plan actif</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Créez un plan manuellement ou importez un fichier PDF/CSV.
              </p>
              <CreatePlanForm onCreate={p => { setPlan(p); setNoPlan(false) }} />
            </CardContent>
          </Card>
        )}

        {!loading && plan && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <CardTitle className="text-lg">{plan.title}</CardTitle>
                  {(plan.start_date || plan.end_date) && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {plan.start_date && formatDate(plan.start_date)}
                      {plan.start_date && plan.end_date && ' → '}
                      {plan.end_date && formatDate(plan.end_date)}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">{plan.source}</Badge>
                  <span className="text-xs text-muted-foreground">{plan.sessions.length} séance{plan.sessions.length !== 1 ? 's' : ''}</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {plan.sessions.length === 0 ? (
                <p className="text-sm text-muted-foreground py-2">Aucune séance — ajoutez-en une ci-dessous.</p>
              ) : (
                <div>
                  {plan.sessions.map(s => (
                    <SessionRow key={s.id} session={s} onUpdate={handleSessionUpdate} />
                  ))}
                </div>
              )}
              <AddSessionForm onAdd={handleSessionAdd} />
            </CardContent>
          </Card>
        )}
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd frontend
git add src/app/tracking/page.tsx
git commit -m "feat(s6): add /tracking page — ExternalPlan viewer + session actions"
```

---

## Task 5: Create tracking/import/page.tsx — File import wizard (S-2 stub)

**Files:**
- Create: `frontend/src/app/tracking/import/page.tsx`

- [ ] **Step 1: Create the file with complete implementation**

Create `frontend/src/app/tracking/import/page.tsx`:

```tsx
// frontend/src/app/tracking/import/page.tsx
'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, type ExternalPlanDraft } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

type Step = 'upload' | 'preview' | 'confirmed'

const SPORT_LABELS: Record<string, string> = {
  running: 'Course',
  lifting: 'Musculation',
  swimming: 'Natation',
  biking: 'Vélo',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' })
}

export default function TrackingImportPage() {
  const { athleteId, coachingMode } = useAuth()
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState<Step>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [draft, setDraft] = useState<ExternalPlanDraft | null>(null)
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (coachingMode !== null && coachingMode !== 'tracking_only') {
      router.replace('/dashboard')
    }
  }, [coachingMode, router])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }, [])

  async function analyse() {
    if (!athleteId || !file) return
    setLoading(true)
    setError('')
    try {
      const result = await api.importExternalPlan(athleteId, file)
      setDraft(result)
      setStep('preview')
    } catch {
      setError('Erreur lors de l\'analyse. Réessayez.')
    } finally {
      setLoading(false)
    }
  }

  async function confirm() {
    if (!athleteId || !draft) return
    setLoading(true)
    setError('')
    try {
      await api.confirmImportExternalPlan(athleteId, draft)
      setStep('confirmed')
    } catch {
      setError('Erreur lors de la confirmation.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-center gap-3">
          <Link href="/tracking" className="text-sm text-muted-foreground hover:text-foreground">
            ← Plan externe
          </Link>
          <span className="text-muted-foreground">/</span>
          <span className="text-sm font-medium">Importer</span>
        </div>

        <div>
          <h1 className="text-2xl font-bold">Importer un plan</h1>
          <p className="text-sm text-muted-foreground mt-1">PDF, TXT, CSV ou ICS</p>
        </div>

        {/* Stub notice */}
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3">
          <p className="text-xs text-amber-600 dark:text-amber-400">
            <span className="font-semibold">Fonctionnalité en cours (S-2)</span> — L&apos;analyse IA utilise des données de démonstration. L&apos;endpoint backend sera disponible dans une prochaine session.
          </p>
        </div>

        {step === 'upload' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Étape 1 — Choisir un fichier</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
                  dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/50'
                }`}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.txt,.csv,.ics"
                  className="hidden"
                  onChange={e => setFile(e.target.files?.[0] ?? null)}
                />
                {file ? (
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-muted-foreground">Glissez un fichier ici ou cliquez pour sélectionner</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF · TXT · CSV · ICS</p>
                  </div>
                )}
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button onClick={analyse} disabled={!file || loading}>
                {loading ? 'Analyse en cours…' : 'Analyser avec IA'}
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 'preview' && draft && (
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">Étape 2 — Vérifier le plan détecté</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    {draft.sessions_parsed} séance{draft.sessions_parsed !== 1 ? 's' : ''} détectée{draft.sessions_parsed !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {draft.parse_warnings.length > 0 && (
                <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-3 py-2 space-y-1">
                  {draft.parse_warnings.map((w, i) => (
                    <p key={i} className="text-xs text-yellow-600 dark:text-yellow-400">{w}</p>
                  ))}
                </div>
              )}

              <div className="divide-y">
                {draft.sessions.map((s, i) => (
                  <div key={i} className="flex items-center gap-3 py-3">
                    <div className="w-24 text-xs text-muted-foreground shrink-0">{formatDate(s.session_date)}</div>
                    <Badge variant="outline" className="text-xs shrink-0">
                      {SPORT_LABELS[s.sport] ?? s.sport}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{s.title}</p>
                      {s.duration_min && (
                        <p className="text-xs text-muted-foreground">{s.duration_min} min</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <div className="flex gap-2 pt-2">
                <Button onClick={confirm} disabled={loading}>
                  {loading ? 'Confirmation…' : 'Confirmer l\'import'}
                </Button>
                <Button variant="ghost" onClick={() => { setStep('upload'); setDraft(null); setFile(null) }}>
                  ← Retour
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 'confirmed' && (
          <Card>
            <CardContent className="py-10 text-center space-y-4">
              <p className="text-4xl">✓</p>
              <p className="text-lg font-semibold">Plan importé !</p>
              <p className="text-sm text-muted-foreground">Vos séances ont été ajoutées à votre plan externe.</p>
              <Button asChild>
                <Link href="/tracking">Voir mon plan →</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </ProtectedRoute>
  )
}
```

- [ ] **Step 2: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run build check**

```bash
cd frontend && npm run build
```

Expected: clean build, no TypeScript/build errors.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/app/tracking/import/page.tsx
git commit -m "feat(s6): add /tracking/import page — file upload wizard (S-2 stubs)"
```

---

## Task 6: Branch setup + SESSION_REPORT.md

**Files:**
- Modify: `SESSION_REPORT.md`

- [ ] **Step 1: Checkout correct branch (if not already on it)**

```bash
git checkout main && git pull && git checkout -b session/s6-frontend-tracking
```

If the branch already exists:
```bash
git checkout session/s6-frontend-tracking
```

- [ ] **Step 2: Add S-6 section to SESSION_REPORT.md**

Prepend (insert after the first `---` separator at the top) the following section to `SESSION_REPORT.md`:

```markdown
# SESSION S-6 — Frontend Tracking Page

**Date :** 2026-04-12
**Branche :** session/s6-frontend-tracking
**Commits :** 5 (feat × 4 + docs × 1)

## Ce qui a été fait

### 1. api.ts — Types + méthodes ExternalPlan
- `AthleteProfile`, `ExternalPlanOut`, `ExternalSessionOut`
- `ExternalPlanCreate`, `ExternalSessionCreate`, `ExternalSessionUpdate`
- `ExternalPlanDraft` (type stub S-2)
- `api.getAthleteProfile()`, `api.getExternalPlan()`, `api.createExternalPlan()`
- `api.addExternalSession()`, `api.updateExternalSession()`, `api.deleteExternalSession()`
- **STUBS** : `api.importExternalPlan()`, `api.confirmImportExternalPlan()` → mock data

### 2. auth.tsx — coachingMode dans le contexte
- `coachingMode: 'full' | 'tracking_only' | null` ajouté à `AuthState`
- Fetch `GET /athletes/{id}` au chargement et au login
- localStorage key `coaching_mode` pour bootstrap rapide

### 3. top-nav.tsx — Badge mode + lien conditionnel
- Badge `TRACKING` (amber) affiché si `coaching_mode === "tracking_only"`
- Lien "Tracking" → `/tracking` visible uniquement en mode tracking_only

### 4. tracking/page.tsx — Visualisation plan externe
- `ProtectedRoute` + redirect `/dashboard` si `coachingMode !== 'tracking_only'`
- GET `/athletes/{id}/external-plan` → affiche plan + sessions
- Marquage séance : PATCH status=completed / skipped
- Formulaire ajout séance (inline)
- Formulaire création plan si 404

### 5. tracking/import/page.tsx — Wizard import fichier
- Drag & drop / sélection fichier (PDF/TXT/CSV/ICS)
- Étape 1 : upload → `api.importExternalPlan()` (STUB)
- Étape 2 : preview draft (sessions + warnings)
- Étape 3 : confirmation → `api.confirmImportExternalPlan()` (STUB)
- Notice de démo visible dans l'UI

## Invariants
- `npx tsc --noEmit` → ✅ aucune erreur
- `npm run build` → ✅ clean

## Stubs S-2 documentés

| Méthode | Endpoint réel | Comportement stub |
|---|---|---|
| `api.importExternalPlan()` | `POST /athletes/{id}/external-plan/import` | Mock draft 3 séances après 800ms |
| `api.confirmImportExternalPlan()` | `POST /athletes/{id}/external-plan/import/confirm` | Mock ExternalPlanOut après 500ms |

Ces stubs seront remplacés quand S-2 sera mergé sur main.

---
```

- [ ] **Step 3: Commit SESSION_REPORT**

```bash
git add SESSION_REPORT.md docs/superpowers/specs/2026-04-12-s6-frontend-tracking-design.md docs/superpowers/plans/2026-04-12-s6-frontend-tracking.md
git commit -m "docs(s6): add SESSION_REPORT S-6 + spec + plan"
```

- [ ] **Step 4: Push branch**

```bash
git push -u origin session/s6-frontend-tracking
```

Expected: branch pushed to remote successfully.

---

## Self-Review Checklist

- [x] `tracking/page.tsx` — protected, mode-gated, shows plan + sessions, mark complete/skip, add session, create plan ✓
- [x] `tracking/import/page.tsx` — protected, mode-gated, upload → preview → confirm, stub notice ✓  
- [x] `top-nav.tsx` — TRACKING badge + conditional nav link ✓
- [x] `auth.tsx` — `coachingMode` in context, fetched on load/login, stored in localStorage ✓
- [x] `api.ts` — all types defined, all methods added, stubs clearly documented ✓
- [x] No new npm packages ✓
- [x] TypeScript check + build check in Task 5 ✓
- [x] SESSION_REPORT.md documents stubs ✓
- [x] Branch pushed ✓
