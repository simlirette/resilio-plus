'use client'
import Link from 'next/link'

// ── Static cycle phase data ───────────────────────────────────────────────

const CYCLE_PHASES = [
  {
    id: 'menstrual',
    label: 'Menstruelle',
    color: '#ef4444',
    description: 'J1–J5 · Récupération prioritaire',
    days: [1, 2, 3, 4, 5],
  },
  {
    id: 'follicular',
    label: 'Folliculaire',
    color: '#10b981',
    description: 'J6–J13 · Phase de gains',
    days: [6, 7, 8, 9, 10, 11, 12, 13],
  },
  {
    id: 'ovulation',
    label: 'Ovulation',
    color: '#5b5fef',
    description: 'J14–J15 · Pic de performance',
    days: [14, 15],
  },
  {
    id: 'luteal',
    label: 'Lutéale',
    color: '#f59e0b',
    description: 'J16–J28 · Intensité modérée',
    days: Array.from({ length: 13 }, (_, i) => i + 16),
  },
]

const PHASE_DESCRIPTIONS: Record<string, { physio: string; performance: string }> = {
  menstrual: {
    physio: 'Estrogène et progestérone au plus bas. Prostaglandines élevées — crampes et inflammation possibles.',
    performance: 'Force légèrement réduite (–5/–10%). Tolérance à la douleur réduite. Récupération ralentie.',
  },
  follicular: {
    physio: 'Estrogène en hausse. Sensibilité à l\'insuline améliorée. Phase de récupération optimale.',
    performance: 'Phase idéale pour les gains de force et les séances intensives. Récupération la plus rapide.',
  },
  ovulation: {
    physio: 'Pic d\'estrogène + LH. Force maximale absolue du cycle. Laxité ligamentaire augmentée.',
    performance: 'Performance au maximum. Risque accru de blessure ligamentaire — attention à la technique.',
  },
  luteal: {
    physio: 'Progestérone élevée. Température basale +0.3–0.5°C. Catabolisme musculaire accru.',
    performance: 'Force réduite progressivement (–5/–15% fin de phase). Besoin protéines augmenté.',
  },
}

// ── Helpers ───────────────────────────────────────────────────────────────

function getPhase(phaseId: string) {
  return CYCLE_PHASES.find(p => p.id === phaseId) ?? CYCLE_PHASES[3]
}

// ── Calendar grid ─────────────────────────────────────────────────────────

function CycleCalendar({ cycleDay, cycleLength }: { cycleDay: number; cycleLength: number }) {
  const days = Array.from({ length: cycleLength }, (_, i) => i + 1)

  function phaseForDay(day: number) {
    return CYCLE_PHASES.find(p => p.days.includes(day))
  }

  return (
    <div>
      <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(7, 1fr)' }}>
        {['L', 'M', 'M', 'J', 'V', 'S', 'D'].map((d, i) => (
          <div key={i} className="text-center text-xs py-1" style={{ color: '#5c5c7a' }}>
            {d}
          </div>
        ))}
        {days.map(day => {
          const phase = phaseForDay(day)
          const isToday = day === cycleDay
          const isCurrent = day <= cycleDay
          return (
            <div
              key={day}
              className="relative flex items-center justify-center rounded-lg text-xs font-medium"
              style={{
                aspectRatio: '1',
                background: isToday
                  ? phase?.color ?? '#5b5fef'
                  : isCurrent
                  ? `${phase?.color ?? '#5b5fef'}22`
                  : '#14141f',
                color: isToday ? '#fff' : isCurrent ? phase?.color : '#5c5c7a',
                border: isToday ? `2px solid ${phase?.color ?? '#5b5fef'}` : '1px solid #22223a',
                fontFamily: "'Space Mono', monospace",
              }}
            >
              {day}
              {isToday && (
                <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full" style={{ background: '#fff' }} />
              )}
            </div>
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 mt-4">
        {CYCLE_PHASES.map(phase => (
          <div key={phase.id} className="flex items-center gap-1.5 text-xs">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: phase.color }} />
            <span style={{ color: '#8888a8' }}>{phase.label}</span>
            <span style={{ color: '#5c5c7a' }}>J{phase.days[0]}–{phase.days[phase.days.length - 1]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Phase detail card ─────────────────────────────────────────────────────

function PhaseCard({ phaseId, cycleDay }: { phaseId: string; cycleDay: number }) {
  const phase = getPhase(phaseId)
  const desc = PHASE_DESCRIPTIONS[phaseId] ?? PHASE_DESCRIPTIONS.luteal

  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: `${phase.color}0e`, border: `1px solid ${phase.color}35` }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium tracking-widest uppercase" style={{ color: `${phase.color}90` }}>
            Phase active
          </p>
          <h3 className="text-xl font-bold mt-0.5" style={{ color: phase.color }}>{phase.label}</h3>
          <p className="text-xs mt-0.5" style={{ color: `${phase.color}80` }}>{phase.description}</p>
        </div>
        <div
          className="text-right text-xs font-mono px-3 py-1.5 rounded-lg"
          style={{ background: `${phase.color}18`, color: phase.color }}
        >
          J{cycleDay}
        </div>
      </div>
      <div className="space-y-2">
        <div>
          <p className="text-xs font-semibold mb-1" style={{ color: '#8888a8' }}>Physiologie</p>
          <p className="text-xs" style={{ color: '#8888a8' }}>{desc.physio}</p>
        </div>
        <div>
          <p className="text-xs font-semibold mb-1" style={{ color: '#8888a8' }}>Performance</p>
          <p className="text-xs" style={{ color: '#8888a8' }}>{desc.performance}</p>
        </div>
      </div>
    </div>
  )
}

// ── Demo notice ───────────────────────────────────────────────────────────

function DemoNotice() {
  return (
    <div
      className="rounded-xl p-4 flex items-start gap-3"
      style={{ background: '#5b5fef10', border: '1px solid #5b5fef30' }}
    >
      <span style={{ color: '#818cf8' }}>ℹ</span>
      <div className="text-xs" style={{ color: '#8888a8' }}>
        <p>Cette vue utilise des données de démonstration (J18 — phase lutéale).</p>
        <p className="mt-0.5">
          Configure ton profil hormonal via le check-in quotidien ou les réglages.
        </p>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────

const DEMO_CYCLE_DAY = 18
const DEMO_CYCLE_LENGTH = 28
const DEMO_PHASE = 'luteal'

export default function CyclePage() {
  const phase = getPhase(DEMO_PHASE)

  return (
    <div className="space-y-6 pb-12 max-w-lg mx-auto">

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
            Cycle Hormonal
          </p>
          <h1 className="text-2xl font-bold mt-0.5" style={{ letterSpacing: '-0.02em' }}>
            <span style={{ color: phase.color }}>{phase.label}</span>
            {' '}
            <span className="font-mono text-lg" style={{ color: '#5c5c7a' }}>J{DEMO_CYCLE_DAY}</span>
          </h1>
        </div>
        <Link
          href="/energy"
          className="text-xs px-3 py-1.5 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#1a1a28', border: '1px solid #22223a', color: '#8888a8' }}
        >
          ← Énergie
        </Link>
      </div>

      <DemoNotice />

      {/* ── Phase detail ── */}
      <PhaseCard phaseId={DEMO_PHASE} cycleDay={DEMO_CYCLE_DAY} />

      {/* ── Cycle calendar ── */}
      <div
        className="rounded-xl p-5"
        style={{ background: '#14141f', border: '1px solid #22223a' }}
      >
        <p className="text-xs font-medium tracking-widest uppercase mb-4" style={{ color: '#5c5c7a' }}>
          Cycle {DEMO_CYCLE_LENGTH} jours · Démo
        </p>
        <CycleCalendar cycleDay={DEMO_CYCLE_DAY} cycleLength={DEMO_CYCLE_LENGTH} />
      </div>

      {/* ── Info note ── */}
      <div
        className="rounded-xl p-4 flex items-start gap-3"
        style={{ background: '#14141f', border: '1px solid #22223a' }}
      >
        <span style={{ color: '#5c5c7a' }}>ℹ</span>
        <div className="text-xs" style={{ color: '#5c5c7a' }}>
          <p>Données saisies manuellement via le check-in quotidien.</p>
          <p className="mt-0.5">Connecte Apple Health pour un suivi automatique du cycle.</p>
        </div>
      </div>

      {/* ── Quick actions ── */}
      <div className="flex gap-3">
        <Link
          href="/check-in"
          className="flex-1 text-center text-sm px-4 py-2.5 rounded-lg font-semibold transition-opacity hover:opacity-80"
          style={{ background: '#5b5fef', color: '#fff' }}
        >
          Check-in du jour
        </Link>
        <Link
          href="/energy"
          className="text-sm px-4 py-2.5 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#1a1a28', border: '1px solid #22223a', color: '#eeeef4' }}
        >
          Dashboard énergie
        </Link>
      </div>
    </div>
  )
}
