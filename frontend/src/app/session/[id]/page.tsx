'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type SessionDetailResponse } from '@/lib/api'
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

function FatigueBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{value.toFixed(0)}/100</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div className="h-1.5 rounded-full bg-primary" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

export default function SessionDetailPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const sessionId = params?.id ?? ''

  const [session, setSession] = useState<SessionDetailResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId || !sessionId) return
    api.getSession(athleteId, sessionId)
      .then(setSession)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError('Failed to load session.')
      })
  }, [athleteId, sessionId, logout])

  return (
    <ProtectedRoute>
      <div className="mx-auto max-w-lg space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/plan">← Plan</Link>
          </Button>
        </div>

        {notFound && <p className="text-muted-foreground">Session not found.</p>}
        {error && <p className="text-destructive">{error}</p>}
        {!session && !notFound && !error && <p className="animate-pulse text-muted-foreground">Loading…</p>}

        {session && (
          <>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SPORT_COLORS[session.sport] ?? ''}`}>
                  {session.sport}
                </span>
                {session.log && (
                  <Badge variant="outline" className="text-emerald-400 border-emerald-400/30">✓ Logged</Badge>
                )}
              </div>
              <h1 className="text-2xl font-bold capitalize">{session.workout_type.replace(/_/g, ' ')}</h1>
              <p className="text-muted-foreground">{session.date} · {session.duration_min} min planned</p>
            </div>

            {session.notes && (
              <Card>
                <CardHeader><CardTitle className="text-sm">Coach Notes</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-line">{session.notes}</p>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader><CardTitle className="text-sm">Fatigue Impact</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <FatigueBar label="Local muscular" value={session.fatigue_score.local_muscular} />
                <FatigueBar label="CNS load" value={session.fatigue_score.cns_load} />
                <FatigueBar label="Metabolic cost" value={session.fatigue_score.metabolic_cost} />
                <p className="text-xs text-muted-foreground mt-2">
                  Recovery: ~{session.fatigue_score.recovery_hours}h
                  {session.fatigue_score.affected_muscles.length > 0 && ` · ${session.fatigue_score.affected_muscles.join(', ')}`}
                </p>
              </CardContent>
            </Card>

            {session.log ? (
              <Card className="border-emerald-500/20 bg-emerald-500/5">
                <CardHeader>
                  <CardTitle className="text-sm text-emerald-400">Session Logged</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  {session.log.skipped ? (
                    <p className="text-muted-foreground">Session skipped.</p>
                  ) : (
                    <>
                      {session.log.actual_duration_min != null && (
                        <p>Duration: <span className="font-medium">{session.log.actual_duration_min} min</span></p>
                      )}
                      {session.log.rpe != null && (
                        <p>RPE: <span className="font-medium">{session.log.rpe}/10</span></p>
                      )}
                      {session.log.notes && (
                        <p className="text-muted-foreground">{session.log.notes}</p>
                      )}
                    </>
                  )}
                  <Button variant="outline" size="sm" asChild className="mt-3">
                    <Link href={`/session/${sessionId}/log`}>Edit log</Link>
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Button className="w-full" asChild>
                <Link href={`/session/${sessionId}/log`}>Log this session →</Link>
              </Button>
            )}
          </>
        )}
      </div>
    </ProtectedRoute>
  )
}
