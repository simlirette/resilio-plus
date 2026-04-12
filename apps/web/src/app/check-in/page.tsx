'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type CheckInRequest, type ReadinessResponse } from '@/lib/api'

// ── Types ─────────────────────────────────────────────────────────────────

type WorkIntensity = CheckInRequest['work_intensity']
type StressLevel = CheckInRequest['stress_level']
type LegsFeeling = CheckInRequest['legs_feeling']
type EnergyGlobal = CheckInRequest['energy_global']

interface FormState {
  work_intensity: WorkIntensity | null
  stress_level: StressLevel | null
  legs_feeling: LegsFeeling | null
  energy_global: EnergyGlobal | null
  comment: string
}

// ── Option button ─────────────────────────────────────────────────────────

function OptionBtn({
  label,
  sub,
  selected,
  onClick,
}: {
  label: string
  sub?: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-xl px-4 py-3.5 transition-all duration-150"
      style={{
        background: selected ? '#5b5fef18' : '#14141f',
        border: `1px solid ${selected ? '#5b5fef' : '#22223a'}`,
        color: selected ? '#818cf8' : '#eeeef4',
      }}
    >
      <span className="font-medium text-sm">{label}</span>
      {sub && (
        <span className="block text-xs mt-0.5" style={{ color: selected ? '#818cf880' : '#5c5c7a' }}>
          {sub}
        </span>
      )}
    </button>
  )
}

// ── Progress dots ─────────────────────────────────────────────────────────

function ProgressDots({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className="rounded-full transition-all duration-300"
          style={{
            width: i < step ? '24px' : '6px',
            height: '6px',
            background: i < step ? '#5b5fef' : i === step ? '#8888a8' : '#22223a',
          }}
        />
      ))}
    </div>
  )
}

// ── Confirmation screen ───────────────────────────────────────────────────

function ConfirmationScreen({ readiness }: { readiness: ReadinessResponse }) {
  const lightColor = { green: '#10b981', yellow: '#f59e0b', red: '#ef4444' }[readiness.traffic_light]
  const lightLabel = { green: 'Feu vert', yellow: 'Feu orange', red: 'Feu rouge' }[readiness.traffic_light]
  const score = Math.round(readiness.final_readiness)

  return (
    <div className="flex flex-col items-center gap-6 py-8 text-center">
      {/* Checkmark */}
      <div
        className="flex items-center justify-center rounded-full"
        style={{ width: 72, height: 72, background: '#10b98118', border: '2px solid #10b981' }}
      >
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <path d="M5 13l4 4L19 7" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <div>
        <h2 className="text-xl font-bold">Check-in enregistré</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--muted-foreground)' }}>
          L&apos;Energy Coach a mis à jour ton profil.
        </p>
      </div>

      {/* Readiness card */}
      <div
        className="w-full rounded-xl p-4"
        style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
      >
        <p className="text-xs tracking-widest uppercase mb-3" style={{ color: 'var(--muted-foreground)' }}>
          Readiness aujourd&apos;hui
        </p>
        <div className="flex items-center justify-between mb-3">
          <span
            className="text-4xl font-bold"
            style={{ fontFamily: "'Space Mono', monospace", color: lightColor }}
          >
            {score}
          </span>
          <span
            className="text-xs px-3 py-1 rounded-full font-semibold flex items-center gap-1.5"
            style={{ background: `${lightColor}18`, color: lightColor, border: `1px solid ${lightColor}40` }}
          >
            <span
              className="inline-block rounded-full"
              style={{ width: 8, height: 8, background: lightColor }}
            />
            {lightLabel}
          </span>
        </div>

        {readiness.insights.length > 0 && (
          <ul className="text-left space-y-1 mt-2">
            {readiness.insights.map((insight, i) => (
              <li key={i} className="text-xs flex items-start gap-2" style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: lightColor, marginTop: 1 }}>›</span>
                {insight}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-3 pt-3 flex justify-between text-xs" style={{ borderTop: '1px solid #22223a' }}>
          <span style={{ color: 'var(--muted-foreground)' }}>Cap intensité</span>
          <span style={{ color: 'var(--foreground)' }}>{Math.round(readiness.intensity_cap * 100)}%</span>
        </div>
      </div>

      {readiness.traffic_light !== 'green' && (
        <div
          className="w-full rounded-xl p-4 flex items-start gap-3 text-left"
          style={{ background: `${lightColor}10`, border: `1px solid ${lightColor}40` }}
        >
          <span className="text-lg">{readiness.traffic_light === 'red' ? '🔴' : '🟡'}</span>
          <div>
            <p className="text-sm font-semibold" style={{ color: lightColor }}>
              Intensité ajustée pour aujourd&apos;hui
            </p>
            <p className="text-xs mt-0.5" style={{ color: `${lightColor}90` }}>
              Cap à {Math.round(readiness.intensity_cap * 100)}% de l&apos;intensité normale.
            </p>
          </div>
        </div>
      )}

      <div className="flex gap-3 w-full">
        <Link
          href="/energy"
          className="flex-1 text-center text-sm px-4 py-2.5 rounded-lg font-semibold transition-opacity hover:opacity-80"
          style={{ background: 'var(--primary)', color: '#fff' }}
        >
          Voir le dashboard énergie
        </Link>
        <Link
          href="/dashboard"
          className="text-sm px-4 py-2.5 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: 'var(--input)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────

export default function CheckInPage() {
  const { athleteId } = useAuth()
  const router = useRouter()

  const [form, setForm] = useState<FormState>({
    work_intensity: null,
    stress_level: null,
    legs_feeling: null,
    energy_global: null,
    comment: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)

  // Step: number of completed questions
  const step =
    form.work_intensity === null ? 0
    : form.stress_level === null ? 1
    : form.legs_feeling === null ? 2
    : form.energy_global === null ? 3
    : 4

  const canSubmit = step === 4 && !submitting

  async function submit() {
    if (!athleteId) { router.replace('/login'); return }
    if (!form.work_intensity || !form.stress_level || !form.legs_feeling || !form.energy_global) return
    setSubmitting(true)
    setError('')
    try {
      const payload: CheckInRequest = {
        work_intensity: form.work_intensity,
        stress_level: form.stress_level,
        legs_feeling: form.legs_feeling,
        energy_global: form.energy_global,
        comment: form.comment.trim() || null,
      }
      const res = await api.submitCheckin(athleteId, payload)
      setReadiness(res)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace('/login')
      } else {
        setError('Erreur lors du check-in. Réessaie.')
        setSubmitting(false)
      }
    }
  }

  if (readiness) {
    return (
      <div className="max-w-md mx-auto px-2">
        <ConfirmationScreen readiness={readiness} />
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto px-2">
      <div className="space-y-6">

        {/* ── Header ── */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <p className="text-xs font-medium tracking-widest uppercase" style={{ color: 'var(--muted-foreground)' }}>
                Check-in Quotidien
              </p>
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: '#5b5fef15', color: '#818cf8', border: '1px solid #5b5fef30' }}
              >
                ~60 secondes
              </span>
            </div>
            <h1 className="text-xl font-bold">Comment vas-tu ?</h1>
          </div>
        </div>

        <ProgressDots step={Math.min(step, 4)} total={4} />

        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {/* ── Q1: Work intensity ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-opacity duration-300"
          style={{
            background: 'var(--card)',
            border: `1px solid ${step >= 0 ? '#22223a' : '#191928'}`,
            opacity: step === 0 || form.work_intensity ? 1 : 0.4,
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'var(--border)', color: 'var(--muted-foreground)' }}>01</span>
            <p className="font-semibold text-sm">Comment s&apos;est passée ta journée de travail ?</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {([
              { value: 'light' as WorkIntensity, label: 'Légère', sub: 'Peu de sollicitations' },
              { value: 'normal' as WorkIntensity, label: 'Normale', sub: 'Journée standard' },
              { value: 'heavy' as WorkIntensity, label: 'Intense', sub: 'Beaucoup de réunions / décisions' },
              { value: 'exhausting' as WorkIntensity, label: 'Épuisante', sub: 'Cognitif maximal' },
            ] as const).map(opt => (
              <OptionBtn
                key={opt.value}
                label={opt.label}
                sub={opt.sub}
                selected={form.work_intensity === opt.value}
                onClick={() => setForm(s => ({ ...s, work_intensity: opt.value }))}
              />
            ))}
          </div>
        </div>

        {/* ── Q2: Stress ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-all duration-300"
          style={{
            background: 'var(--card)',
            border: `1px solid ${step >= 1 ? '#22223a' : '#191928'}`,
            opacity: form.work_intensity ? 1 : 0.3,
            pointerEvents: form.work_intensity ? 'auto' : 'none',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'var(--border)', color: 'var(--muted-foreground)' }}>02</span>
            <p className="font-semibold text-sm">Facteurs de stress importants aujourd&apos;hui ?</p>
          </div>
          <div className="space-y-2">
            {([
              { value: 'none' as StressLevel, label: 'Non', sub: 'Journée tranquille' },
              { value: 'mild' as StressLevel, label: 'Oui, léger', sub: 'Quelques tensions gérées' },
              { value: 'significant' as StressLevel, label: 'Oui, significatif', sub: 'Stress notable, difficile à zapper' },
            ] as const).map(opt => (
              <OptionBtn
                key={opt.value}
                label={opt.label}
                sub={opt.sub}
                selected={form.stress_level === opt.value}
                onClick={() => setForm(s => ({ ...s, stress_level: opt.value }))}
              />
            ))}
          </div>
        </div>

        {/* ── Q3: Legs feeling ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-all duration-300"
          style={{
            background: 'var(--card)',
            border: `1px solid ${step >= 2 ? '#22223a' : '#191928'}`,
            opacity: form.stress_level ? 1 : 0.3,
            pointerEvents: form.stress_level ? 'auto' : 'none',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'var(--border)', color: 'var(--muted-foreground)' }}>03</span>
            <p className="font-semibold text-sm">Comment se sentent tes jambes ?</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {([
              { value: 'fresh' as LegsFeeling, label: 'Fraîches', sub: 'Prêt à tout' },
              { value: 'normal' as LegsFeeling, label: 'Normales', sub: 'État standard' },
              { value: 'heavy' as LegsFeeling, label: 'Lourdes', sub: 'Fatigue ressentie' },
              { value: 'dead' as LegsFeeling, label: 'Mortes', sub: 'Vraiment épuisées' },
            ] as const).map(opt => (
              <OptionBtn
                key={opt.value}
                label={opt.label}
                sub={opt.sub}
                selected={form.legs_feeling === opt.value}
                onClick={() => setForm(s => ({ ...s, legs_feeling: opt.value }))}
              />
            ))}
          </div>
        </div>

        {/* ── Q4: Energy global ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-all duration-300"
          style={{
            background: 'var(--card)',
            border: `1px solid ${step >= 3 ? '#22223a' : '#191928'}`,
            opacity: form.legs_feeling ? 1 : 0.3,
            pointerEvents: form.legs_feeling ? 'auto' : 'none',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'var(--border)', color: 'var(--muted-foreground)' }}>04</span>
            <p className="font-semibold text-sm">Niveau d&apos;énergie global aujourd&apos;hui ?</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {([
              { value: 'great' as EnergyGlobal, label: 'Super', sub: 'Plein d\'énergie' },
              { value: 'ok' as EnergyGlobal, label: 'Correct', sub: 'Dans la norme' },
              { value: 'low' as EnergyGlobal, label: 'Faible', sub: 'Moins d\'élan que d\'habitude' },
              { value: 'exhausted' as EnergyGlobal, label: 'Épuisé', sub: 'Vraiment à plat' },
            ] as const).map(opt => (
              <OptionBtn
                key={opt.value}
                label={opt.label}
                sub={opt.sub}
                selected={form.energy_global === opt.value}
                onClick={() => setForm(s => ({ ...s, energy_global: opt.value }))}
              />
            ))}
          </div>
        </div>

        {/* ── Q5: Optional comment ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-all duration-300"
          style={{
            background: 'var(--card)',
            border: `1px solid ${step >= 4 ? '#22223a' : '#191928'}`,
            opacity: form.energy_global ? 1 : 0.3,
            pointerEvents: form.energy_global ? 'auto' : 'none',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: 'var(--border)', color: 'var(--muted-foreground)' }}>05</span>
            <p className="font-semibold text-sm">
              Note rapide{' '}
              <span className="font-normal" style={{ color: 'var(--muted-foreground)' }}>(optionnel)</span>
            </p>
          </div>
          <textarea
            value={form.comment}
            onChange={e => setForm(s => ({ ...s, comment: e.target.value.slice(0, 140) }))}
            placeholder="Ex : nuit agitée, courbatures post-sortie longue…"
            rows={2}
            className="w-full rounded-lg px-3 py-2.5 text-sm resize-none outline-none"
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--border)',
              color: 'var(--foreground)',
            }}
          />
          {form.comment.length > 0 && (
            <p className="text-right text-xs" style={{ color: 'var(--muted-foreground)' }}>
              {form.comment.length}/140
            </p>
          )}
        </div>

        {/* ── Submit ── */}
        <button
          disabled={!canSubmit}
          onClick={submit}
          className="w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200"
          style={{
            background: canSubmit ? '#5b5fef' : '#22223a',
            color: canSubmit ? '#fff' : '#5c5c7a',
            cursor: canSubmit ? 'pointer' : 'not-allowed',
          }}
        >
          {submitting
            ? 'Enregistrement…'
            : step < 4
            ? `Répondre aux ${4 - step} question${4 - step > 1 ? 's' : ''} restante${4 - step > 1 ? 's' : ''}`
            : 'Enregistrer le check-in →'}
        </button>

        <p className="text-center text-xs" style={{ color: 'var(--muted-foreground)' }}>
          Données utilisées uniquement pour calibrer ton Allostatic Score.
        </p>
      </div>
    </div>
  )
}
