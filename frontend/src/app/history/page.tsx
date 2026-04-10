'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type WeekSummary } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

function phaseLabel(phase: string) {
  return phase.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function HistoryPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [history, setHistory] = useState<WeekSummary[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId) return
    api.getHistory(athleteId)
      .then(setHistory)
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
        else setError('Failed to load history.')
      })
  }, [athleteId, logout])

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Training History</h1>
          <p className="mt-1 text-muted-foreground">Past weeks, newest first.</p>
        </div>

        {error && <p className="text-destructive">{error}</p>}
        {!history && !error && <p className="animate-pulse text-muted-foreground">Loading…</p>}

        {history && history.length === 0 && (
          <p className="text-muted-foreground">No training weeks yet.</p>
        )}

        {history && history.length > 0 && (
          <div className="space-y-3">
            {history.map(week => (
              <Card key={week.plan_id}>
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-muted-foreground">Week {week.week_number}</span>
                        <Badge variant="secondary" className="text-xs">{phaseLabel(week.phase)}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{week.start_date} — {week.end_date}</p>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>{week.sessions_logged}/{week.sessions_total} sessions logged</span>
                          <span>{week.completion_pct}%</span>
                        </div>
                        <Progress value={week.completion_pct} className="h-1.5" />
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-lg font-bold">{week.planned_hours}h</p>
                      <p className="text-xs text-muted-foreground">planned</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ProtectedRoute>
  )
}
