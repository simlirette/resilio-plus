// frontend/src/app/dashboard/page.tsx
'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type WeekStatusResponse, type WorkoutSlot, type ReadinessResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

function acwrVariant(acwr: number | null): 'default' | 'secondary' | 'destructive' {
  if (acwr === null) return 'secondary'
  if (acwr < 0.8) return 'secondary'
  if (acwr <= 1.3) return 'default'
  return 'destructive'
}

// ── EnergyCard ────────────────────────────────────────────────────────────

function EnergyCard({ readiness }: { readiness: ReadinessResponse | null | 'loading' | 'none' }) {
  if (readiness === 'loading') {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">Énergie</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground animate-pulse">Chargement…</p>
        </CardContent>
      </Card>
    )
  }

  if (readiness === 'none' || readiness === null) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">Énergie</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">Pas de check-in aujourd&apos;hui</p>
          <Button asChild size="sm" variant="outline">
            <Link href="/check-in">Check-in →</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  const lightColor = { green: '#10b981', yellow: '#f59e0b', red: '#ef4444' }[readiness.traffic_light]
  const lightLabel = { green: 'Vert', yellow: 'Orange', red: 'Rouge' }[readiness.traffic_light]
  const score = Math.round(readiness.final_readiness)

  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">Énergie</CardTitle>
        <div className="flex items-center gap-1.5">
          <span
            className="inline-block rounded-full"
            style={{ width: 10, height: 10, background: lightColor, flexShrink: 0 }}
          />
          <span className="text-xs font-medium" style={{ color: lightColor }}>{lightLabel}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-baseline gap-1">
          <span
            className="text-3xl font-bold"
            style={{ fontFamily: "'Space Mono', monospace", color: lightColor }}
          >
            {score}
          </span>
          <span className="text-sm text-muted-foreground">/ 100 readiness</span>
        </div>

        {readiness.insights.length > 0 && (
          <ul className="space-y-1">
            {readiness.insights.slice(0, 2).map((insight, i) => (
              <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                <span style={{ color: lightColor, lineHeight: '1.4' }}>›</span>
                {insight}
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground">
            Cap intensité : {Math.round(readiness.intensity_cap * 100)}%
          </span>
          <Button asChild size="sm" variant="ghost" className="h-6 text-xs px-2">
            <Link href="/energy">Détail →</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────

function nextSession(status: WeekStatusResponse): WorkoutSlot | null {
  const today = new Date().toISOString().split('T')[0]
  return status.plan.sessions.find(s => s.date >= today) ?? null
}

export default function DashboardPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [status, setStatus] = useState<WeekStatusResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')
  const [readiness, setReadiness] = useState<ReadinessResponse | null | 'loading' | 'none'>('loading')

  useEffect(() => {
    if (!athleteId) return
    api.getWeekStatus(athleteId)
      .then(setStatus)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError('Failed to load week status.')
      })
    api.getReadiness(athleteId)
      .then(setReadiness)
      .catch(err => {
        if (err instanceof ApiError && err.status === 404) setReadiness('none')
        else if (err instanceof ApiError && err.status === 401) { /* handled above */ }
        else setReadiness(null)
      })
  }, [athleteId, logout]) // router is stable in Next.js — omit to prevent re-fetch on every render

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
                <Badge variant={acwrVariant(status.acwr)} className="text-base">
                  {status.acwr?.toFixed(2) ?? '—'}
                </Badge>
              </CardContent>
            </Card>
          </div>

          <EnergyCard readiness={readiness} />

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
