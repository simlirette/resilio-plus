'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
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
  }, [athleteId, logout]) // router is stable in Next.js — omit to prevent re-fetch on every render

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
