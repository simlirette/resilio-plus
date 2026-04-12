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
          <p className="mt-1 text-muted-foreground">Log how your week went and get next week&apos;s adjustment.</p>
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
