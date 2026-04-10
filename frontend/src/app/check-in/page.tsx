'use client'
import { useState } from 'react'
import Link from 'next/link'

// ── Types ─────────────────────────────────────────────────────────────────

type WorkIntensity = 'light' | 'normal' | 'heavy' | 'exhausting'
type StressLevel = 'none' | 'mild' | 'significant'

interface CheckInState {
  work_intensity: WorkIntensity | null
  stress_level: StressLevel | null
  submitted: boolean
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

function ConfirmationScreen({ work, stress }: { work: WorkIntensity; stress: StressLevel }) {
  const scoreEst = {
    none: { light: 28, normal: 36, heavy: 52, exhausting: 72 },
    mild: { light: 35, normal: 45, heavy: 58, exhausting: 76 },
    significant: { light: 48, normal: 58, heavy: 68, exhausting: 85 },
  }[stress][work]

  const zoneColor = scoreEst <= 40 ? '#10b981' : scoreEst <= 60 ? '#f59e0b' : '#ef4444'
  const zoneLabel = scoreEst <= 40 ? 'Charge légère' : scoreEst <= 60 ? 'Charge modérée' : 'Charge élevée'

  return (
    <div className="flex flex-col items-center gap-6 py-8 text-center">
      {/* Checkmark animation */}
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
        <p className="text-sm mt-1" style={{ color: '#5c5c7a' }}>
          L'Energy Coach a mis à jour ton profil.
        </p>
      </div>

      {/* Score preview */}
      <div
        className="w-full rounded-xl p-4"
        style={{ background: '#14141f', border: '1px solid #22223a' }}
      >
        <p className="text-xs tracking-widest uppercase mb-3" style={{ color: '#5c5c7a' }}>
          Estimation Allostatic Score
        </p>
        <div className="flex items-center justify-between">
          <span
            className="text-4xl font-bold"
            style={{ fontFamily: "'Space Mono', monospace", color: zoneColor }}
          >
            ~{scoreEst}
          </span>
          <span
            className="text-xs px-3 py-1 rounded-full font-semibold"
            style={{ background: `${zoneColor}18`, color: zoneColor, border: `1px solid ${zoneColor}40` }}
          >
            {zoneLabel}
          </span>
        </div>

        <div className="mt-3 space-y-1.5 text-left">
          <div className="flex justify-between text-xs">
            <span style={{ color: '#5c5c7a' }}>Journée de travail</span>
            <span style={{ color: '#eeeef4' }}>
              {{ light: 'Légère', normal: 'Normale', heavy: 'Intense', exhausting: 'Épuisante' }[work]}
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span style={{ color: '#5c5c7a' }}>Stress déclaré</span>
            <span style={{ color: '#eeeef4' }}>
              {{ none: 'Aucun', mild: 'Léger', significant: 'Significatif' }[stress]}
            </span>
          </div>
        </div>
      </div>

      {/* Intensity note if high load */}
      {scoreEst > 60 && (
        <div
          className="w-full rounded-xl p-4 flex items-start gap-3 text-left"
          style={{ background: '#f59e0b10', border: '1px solid #f59e0b40' }}
        >
          <span className="text-lg">⚡</span>
          <div>
            <p className="text-sm font-semibold" style={{ color: '#f59e0b' }}>
              Intensité ajustée pour aujourd'hui
            </p>
            <p className="text-xs mt-0.5" style={{ color: '#f59e0b80' }}>
              Cap à 85% de l'intensité normale. Durée réduite de ~10%.
            </p>
          </div>
        </div>
      )}

      <div className="flex gap-3 w-full">
        <Link
          href="/energy"
          className="flex-1 text-center text-sm px-4 py-2.5 rounded-lg font-semibold transition-opacity hover:opacity-80"
          style={{ background: '#5b5fef', color: '#fff' }}
        >
          Voir le dashboard énergie
        </Link>
        <Link
          href="/dashboard"
          className="text-sm px-4 py-2.5 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#1a1a28', border: '1px solid #22223a', color: '#eeeef4' }}
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────

export default function CheckInPage() {
  const [state, setState] = useState<CheckInState>({
    work_intensity: null,
    stress_level: null,
    submitted: false,
  })

  // Which step are we on? 0 = work, 1 = stress, 2 = done
  const step = state.work_intensity === null ? 0 : state.stress_level === null ? 1 : 2
  const canSubmit = step === 2 && !state.submitted

  function submit() {
    setState(s => ({ ...s, submitted: true }))
  }

  if (state.submitted && state.work_intensity && state.stress_level) {
    return (
      <div className="max-w-md mx-auto px-2">
        <ConfirmationScreen work={state.work_intensity} stress={state.stress_level} />
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
              <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
                Check-in Quotidien
              </p>
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: '#5b5fef15', color: '#818cf8', border: '1px solid #5b5fef30' }}
              >
                ~30 secondes
              </span>
            </div>
            <h1 className="text-xl font-bold">Comment vas-tu ?</h1>
          </div>
        </div>

        <ProgressDots step={step === 2 ? 2 : step + 1} total={2} />

        {/* ── Question 1: Work intensity ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-opacity duration-300"
          style={{
            background: '#14141f',
            border: `1px solid ${step >= 0 ? '#22223a' : '#191928'}`,
            opacity: step === 0 || state.work_intensity ? 1 : 0.4,
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-xs font-mono px-1.5 py-0.5 rounded"
              style={{ background: '#22223a', color: '#5c5c7a' }}
            >
              01
            </span>
            <p className="font-semibold text-sm">Comment s'est passée ta journée de travail ?</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {[
              { value: 'light' as WorkIntensity, label: 'Légère', sub: 'Peu de sollicitations' },
              { value: 'normal' as WorkIntensity, label: 'Normale', sub: 'Journée standard' },
              { value: 'heavy' as WorkIntensity, label: 'Intense', sub: 'Beaucoup de réunions / décisions' },
              { value: 'exhausting' as WorkIntensity, label: 'Épuisante', sub: 'Cognitif maximal' },
            ].map(opt => (
              <OptionBtn
                key={opt.value}
                label={opt.label}
                sub={opt.sub}
                selected={state.work_intensity === opt.value}
                onClick={() => setState(s => ({ ...s, work_intensity: opt.value }))}
              />
            ))}
          </div>
        </div>

        {/* ── Question 2: Stress ── */}
        <div
          className="rounded-xl p-5 space-y-3 transition-all duration-300"
          style={{
            background: '#14141f',
            border: `1px solid ${step >= 1 ? '#22223a' : '#191928'}`,
            opacity: state.work_intensity ? 1 : 0.3,
            pointerEvents: state.work_intensity ? 'auto' : 'none',
          }}
        >
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-xs font-mono px-1.5 py-0.5 rounded"
              style={{ background: '#22223a', color: '#5c5c7a' }}
            >
              02
            </span>
            <p className="font-semibold text-sm">Facteurs de stress importants aujourd'hui ?</p>
          </div>

          <div className="space-y-2">
            {[
              { value: 'none' as StressLevel, label: 'Non', sub: 'Journée tranquille' },
              { value: 'mild' as StressLevel, label: 'Oui, léger', sub: 'Quelques tensions gérées' },
              { value: 'significant' as StressLevel, label: 'Oui, significatif', sub: 'Stress notable, difficile à zapper' },
            ].map(opt => (
              <OptionBtn
                key={opt.value}
                label={opt.label}
                sub={opt.sub}
                selected={state.stress_level === opt.value}
                onClick={() => setState(s => ({ ...s, stress_level: opt.value }))}
              />
            ))}
          </div>
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
          {step < 2 ? 'Répondre aux 2 questions pour continuer' : 'Enregistrer le check-in →'}
        </button>

        <p className="text-center text-xs" style={{ color: '#5c5c7a' }}>
          Données utilisées uniquement pour calibrer ton Allostatic Score.
        </p>
      </div>
    </div>
  )
}
