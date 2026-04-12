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
