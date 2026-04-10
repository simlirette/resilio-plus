'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type SessionDetailResponse } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const RPE_LABELS: Record<number, string> = {
  1: 'Very Easy', 2: 'Easy', 3: 'Moderate', 4: 'Somewhat Hard',
  5: 'Hard', 6: 'Hard+', 7: 'Very Hard', 8: 'Very Hard+',
  9: 'Max Effort–', 10: 'Max Effort',
}

export default function LogSessionPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const sessionId = params?.id ?? ''

  const [session, setSession] = useState<SessionDetailResponse | null>(null)
  const [skipped, setSkipped] = useState(false)
  const [duration, setDuration] = useState('')
  const [rpe, setRpe] = useState('')
  const [rpeEnabled, setRpeEnabled] = useState(false)
  const [notes, setNotes] = useState('')
  // Sport-specific
  const [paceMin, setPaceMin] = useState('')
  const [paceSec, setPaceSec] = useState('')
  const [distanceKm, setDistanceKm] = useState('')
  const [avgPowerW, setAvgPowerW] = useState('')
  const [distanceM, setDistanceM] = useState('')

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!athleteId || !sessionId) return
    api.getSession(athleteId, sessionId)
      .then(s => {
        setSession(s)
        // Pre-fill from existing log if any
        if (s.log) {
          setSkipped(s.log.skipped)
          if (s.log.actual_duration_min) setDuration(String(s.log.actual_duration_min))
          if (s.log.rpe) { setRpe(String(s.log.rpe)); setRpeEnabled(true) }
          if (s.log.notes) setNotes(s.log.notes)
        } else {
          // Pre-fill duration with planned
          setDuration(String(s.duration_min))
        }
      })
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      })
  }, [athleteId, sessionId, logout])

  function buildActualData(): Record<string, unknown> {
    if (!session) return {}
    if (session.sport === 'running') {
      const pace = paceMin && paceSec ? parseInt(paceMin) * 60 + parseInt(paceSec) : undefined
      const dist = distanceKm ? parseFloat(distanceKm) : undefined
      return { ...(pace ? { avg_pace_s_km: pace } : {}), ...(dist ? { distance_km: dist } : {}) }
    }
    if (session.sport === 'biking') {
      return {
        ...(avgPowerW ? { avg_power_w: parseInt(avgPowerW) } : {}),
        ...(distanceKm ? { distance_km: parseFloat(distanceKm) } : {}),
      }
    }
    if (session.sport === 'swimming') {
      return distanceM ? { distance_m: parseInt(distanceM) } : {}
    }
    return {}
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!athleteId) return
    setError('')
    setLoading(true)
    try {
      await api.logSession(athleteId, sessionId, {
        actual_duration_min: skipped ? undefined : (duration ? parseInt(duration) : undefined),
        skipped,
        rpe: !skipped && rpeEnabled && rpe ? parseInt(rpe) : undefined,
        notes: notes.trim() || undefined,
        actual_data: buildActualData(),
      })
      router.push(`/session/${sessionId}`)
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
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/session/${sessionId}`}>← Session</Link>
          </Button>
        </div>

        <div>
          <h1 className="text-2xl font-bold">Log Session</h1>
          {session && (
            <p className="text-muted-foreground capitalize">
              {session.workout_type.replace(/_/g, ' ')} · {session.duration_min} min planned
            </p>
          )}
        </div>

        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5">

              <div className="flex items-center gap-3">
                <input
                  id="skipped"
                  type="checkbox"
                  checked={skipped}
                  onChange={e => setSkipped(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                />
                <Label htmlFor="skipped" className="cursor-pointer">Skip this session</Label>
              </div>

              {!skipped && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="duration">Actual duration (min)</Label>
                    <Input
                      id="duration"
                      type="number"
                      min={1}
                      value={duration}
                      onChange={e => setDuration(e.target.value)}
                      placeholder="e.g. 45"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <input
                        id="rpe-enabled"
                        type="checkbox"
                        checked={rpeEnabled}
                        onChange={e => { setRpeEnabled(e.target.checked); if (!rpe) setRpe('5') }}
                        className="h-4 w-4 rounded border-input"
                      />
                      <Label htmlFor="rpe-enabled" className="cursor-pointer">
                        Record RPE <span className="text-muted-foreground text-xs">(1–10) {rpeEnabled && rpe ? `— ${RPE_LABELS[parseInt(rpe)] ?? ''}` : ''}</span>
                      </Label>
                    </div>
                    {rpeEnabled && (
                      <>
                        <Input
                          id="rpe"
                          type="range"
                          min={1}
                          max={10}
                          value={rpe || '5'}
                          onChange={e => setRpe(e.target.value)}
                          className="cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>1 · Easy</span><span>10 · Max</span>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Sport-specific fields */}
                  {session?.sport === 'running' && (
                    <div className="space-y-3">
                      <Label>Avg pace (optional)</Label>
                      <div className="flex gap-2 items-center">
                        <Input type="number" min={0} max={30} placeholder="min" value={paceMin} onChange={e => setPaceMin(e.target.value)} className="w-20" />
                        <span className="text-muted-foreground">:</span>
                        <Input type="number" min={0} max={59} placeholder="sec" value={paceSec} onChange={e => setPaceSec(e.target.value)} className="w-20" />
                        <span className="text-sm text-muted-foreground">/km</span>
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="dist_run">Distance (km, optional)</Label>
                        <Input id="dist_run" type="number" step="0.1" value={distanceKm} onChange={e => setDistanceKm(e.target.value)} placeholder="e.g. 10.2" />
                      </div>
                    </div>
                  )}

                  {session?.sport === 'biking' && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <Label htmlFor="power">Avg power (W, optional)</Label>
                        <Input id="power" type="number" value={avgPowerW} onChange={e => setAvgPowerW(e.target.value)} placeholder="e.g. 185" />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="dist_bike">Distance (km, optional)</Label>
                        <Input id="dist_bike" type="number" step="0.1" value={distanceKm} onChange={e => setDistanceKm(e.target.value)} placeholder="e.g. 40" />
                      </div>
                    </div>
                  )}

                  {session?.sport === 'swimming' && (
                    <div className="space-y-1">
                      <Label htmlFor="dist_swim">Distance (m, optional)</Label>
                      <Input id="dist_swim" type="number" value={distanceM} onChange={e => setDistanceM(e.target.value)} placeholder="e.g. 1500" />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="notes">Notes (optional)</Label>
                    <textarea
                      id="notes"
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={notes}
                      onChange={e => setNotes(e.target.value)}
                      placeholder="How did it feel?"
                    />
                  </div>
                </>
              )}

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? 'Saving…' : 'Save log →'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
