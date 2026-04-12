'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid,
} from 'recharts'
import { AllostaticGauge } from '@/components/ui/allostatic-gauge'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type ReadinessResponse, type EnergySnapshotSummary } from '@/lib/api'

// ── Color helpers ──────────────────────────────────────────────────────────

function trafficColor(light: string): string {
  return { green: '#10b981', yellow: '#f59e0b', red: '#ef4444' }[light] ?? '#5b5fef'
}

function allostaticColor(score: number): string {
  if (score <= 40) return '#10b981'
  if (score <= 60) return '#f59e0b'
  if (score <= 80) return '#ef4444'
  return '#dc2626'
}

function eaColor(ea: number): string {
  if (ea >= 45) return '#10b981'
  if (ea >= 30) return '#f59e0b'
  return '#ef4444'
}

// ── Mini stat card ─────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  unit,
  sub,
  color = '#eeeef4',
}: {
  label: string
  value: string | number
  unit?: string
  sub?: string
  color?: string
}) {
  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-1"
      style={{ background: '#14141f', border: '1px solid #22223a' }}
    >
      <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
        {label}
      </p>
      <div className="flex items-end gap-1 mt-1">
        <span
          className="text-3xl font-bold leading-none"
          style={{ fontFamily: "'Space Mono', monospace", color }}
        >
          {value}
        </span>
        {unit && <span className="text-sm mb-0.5" style={{ color: '#5c5c7a' }}>{unit}</span>}
      </div>
      {sub && <p className="text-xs mt-0.5" style={{ color: '#5c5c7a' }}>{sub}</p>}
    </div>
  )
}

// ── EA Bar ────────────────────────────────────────────────────────────────

function EnergyAvailabilityCard({ ea }: { ea: number }) {
  const color = eaColor(ea)
  const label = ea >= 45 ? 'Optimal' : ea >= 30 ? 'Sous-optimal' : 'Critique'
  const pct = Math.min(100, (ea / 60) * 100)

  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-3"
      style={{ background: '#14141f', border: '1px solid #22223a' }}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
          Energy Availability
        </p>
        <span
          className="text-xs font-semibold px-2 py-0.5 rounded-full"
          style={{ background: `${color}18`, color }}
        >
          {label}
        </span>
      </div>

      <div className="flex items-end gap-1">
        <span
          className="text-3xl font-bold leading-none"
          style={{ fontFamily: "'Space Mono', monospace", color }}
        >
          {Math.round(ea)}
        </span>
        <span className="text-sm mb-0.5" style={{ color: '#5c5c7a' }}>kcal/kg FFM</span>
      </div>

      <div className="relative">
        <div className="h-2 rounded-full overflow-hidden" style={{ background: '#22223a' }}>
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
        </div>
        <div className="absolute top-0 bottom-0 w-px" style={{ left: `${(45 / 60) * 100}%`, background: '#10b981', opacity: 0.5 }} />
      </div>

      <div className="flex justify-between text-xs" style={{ color: '#5c5c7a' }}>
        <span>0</span>
        <span style={{ color: '#10b98188' }}>Seuil optimal: 45</span>
        <span>60</span>
      </div>
    </div>
  )
}

// ── Custom Tooltip ────────────────────────────────────────────────────────

function ChartTooltip(props: Record<string, unknown>) {
  const { active, payload, label } = props as {
    active?: boolean
    payload?: ReadonlyArray<{ value: number; color: string; name: string }>
    label?: string
  }
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-lg px-3 py-2 text-sm"
      style={{ background: '#1a1a28', border: '1px solid #22223a', color: '#eeeef4' }}
    >
      <p className="text-xs mb-1" style={{ color: '#5c5c7a' }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          <span className="font-mono font-bold">{p.value}</span>
          <span className="ml-1 text-xs" style={{ color: '#5c5c7a' }}>{p.name}</span>
        </p>
      ))}
    </div>
  )
}

// ── Status banner ─────────────────────────────────────────────────────────

function VetoStatus({ readiness }: { readiness: ReadinessResponse }) {
  const cap = readiness.intensity_cap
  const light = readiness.traffic_light

  if (light === 'red') {
    return (
      <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: '#ef444415', border: '1px solid #ef444440' }}>
        <span className="text-xl mt-0.5">🔴</span>
        <div>
          <p className="font-semibold text-sm" style={{ color: '#ef4444' }}>Séance déconseillée</p>
          <p className="text-xs mt-0.5" style={{ color: '#ef444490' }}>
            Charge allostatique critique. Cap à {Math.round(cap * 100)}%.
          </p>
        </div>
      </div>
    )
  }

  if (light === 'yellow') {
    return (
      <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: '#f59e0b12', border: '1px solid #f59e0b40' }}>
        <span className="text-xl mt-0.5">🟡</span>
        <div>
          <p className="font-semibold text-sm" style={{ color: '#f59e0b' }}>
            Intensité réduite · cap {Math.round(cap * 100)}%
          </p>
          <p className="text-xs mt-0.5" style={{ color: '#f59e0b90' }}>
            Charge allostatique modérée.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: '#10b98112', border: '1px solid #10b98140' }}>
      <span className="text-xl mt-0.5">🟢</span>
      <div>
        <p className="font-semibold text-sm" style={{ color: '#10b981' }}>Plan nominal</p>
        <p className="text-xs mt-0.5" style={{ color: '#10b98190' }}>Tous les indicateurs dans la zone.</p>
      </div>
    </div>
  )
}

// ── History charts ────────────────────────────────────────────────────────

function HistoryCharts({ history }: { history: EnergySnapshotSummary[] }) {
  if (history.length === 0) return null

  const chartData = history.slice(-7).map(s => ({
    label: s.date.slice(5), // MM-DD
    score: Math.round(s.allostatic_score),
    light: s.traffic_light,
  }))

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: '#14141f', border: '1px solid #22223a' }}
    >
      <p className="text-xs font-medium tracking-widest uppercase mb-4" style={{ color: '#5c5c7a' }}>
        Historique {Math.min(history.length, 7)} jours
      </p>
      <p className="text-xs mb-3" style={{ color: '#8888a8' }}>Allostatic Score</p>
      <ResponsiveContainer width="100%" height={100}>
        <LineChart data={chartData} margin={{ left: -20, right: 10, top: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#22223a" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#5c5c7a', fontFamily: 'Space Grotesk' }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#5c5c7a', fontFamily: 'Space Mono' }} axisLine={false} tickLine={false} />
          <ReferenceLine y={40} stroke="#10b98140" strokeDasharray="4 4" />
          <ReferenceLine y={60} stroke="#f59e0b40" strokeDasharray="4 4" />
          <Tooltip content={(props) => <ChartTooltip {...props} />} />
          <Line
            type="monotone"
            dataKey="score"
            name="score"
            stroke="#5b5fef"
            strokeWidth={2}
            dot={{ r: 3, fill: '#5b5fef', stroke: '#08080e', strokeWidth: 2 }}
            activeDot={{ r: 4, fill: '#5b5fef' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Insights panel ─────────────────────────────────────────────────────────

function InsightsPanel({ insights }: { insights: string[] }) {
  if (insights.length === 0) return null
  return (
    <div
      className="rounded-xl p-4"
      style={{ background: '#14141f', border: '1px solid #22223a' }}
    >
      <p className="text-xs font-medium tracking-widest uppercase mb-3" style={{ color: '#5c5c7a' }}>
        Insights
      </p>
      <ul className="space-y-1.5">
        {insights.map((insight, i) => (
          <li key={i} className="text-xs flex items-start gap-2" style={{ color: '#8888a8' }}>
            <span style={{ color: '#5b5fef', marginTop: 1 }}>›</span>
            {insight}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────

export default function EnergyPage() {
  const { athleteId } = useAuth()
  const router = useRouter()
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)
  const [history, setHistory] = useState<EnergySnapshotSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [noCheckin, setNoCheckin] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!athleteId) return

    Promise.allSettled([
      api.getReadiness(athleteId),
      api.getEnergyHistory(athleteId, 7),
    ]).then(([rRes, hRes]) => {
      if (rRes.status === 'fulfilled') {
        setReadiness(rRes.value)
      } else if (rRes.reason instanceof ApiError) {
        if (rRes.reason.status === 401) { router.replace('/login'); return }
        if (rRes.reason.status === 404) setNoCheckin(true)
        else setError('Impossible de charger le readiness.')
      }
      if (hRes.status === 'fulfilled') setHistory(hRes.value)
      setLoading(false)
    })
  }, [athleteId, router])

  const today = new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
  const todayCapitalized = today.charAt(0).toUpperCase() + today.slice(1)

  return (
    <div className="space-y-6 pb-12">

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
            Tableau de Bord Énergie
          </p>
          <h1 className="text-2xl font-bold mt-0.5" style={{ letterSpacing: '-0.02em' }}>
            {todayCapitalized}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {readiness ? (
            <span
              className="text-xs px-2.5 py-1 rounded-full font-medium"
              style={{ background: '#10b98115', color: '#10b981', border: '1px solid #10b98130' }}
            >
              ✓ Check-in fait
            </span>
          ) : (
            <Link
              href="/check-in"
              className="text-xs px-3 py-1.5 rounded-full font-semibold transition-opacity hover:opacity-80"
              style={{ background: '#5b5fef', color: '#fff' }}
            >
              Check-in →
            </Link>
          )}
        </div>
      </div>

      {/* ── Loading state ── */}
      {loading && (
        <p className="text-sm text-muted-foreground animate-pulse">Chargement…</p>
      )}

      {/* ── Error ── */}
      {error && <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>}

      {/* ── No check-in yet ── */}
      {!loading && noCheckin && !readiness && (
        <div
          className="rounded-xl p-6 flex flex-col items-center gap-4 text-center"
          style={{ background: '#14141f', border: '1px solid #22223a' }}
        >
          <p className="text-sm" style={{ color: '#5c5c7a' }}>
            Pas encore de check-in aujourd&apos;hui.
          </p>
          <Link
            href="/check-in"
            className="text-sm px-6 py-2.5 rounded-xl font-semibold transition-opacity hover:opacity-80"
            style={{ background: '#5b5fef', color: '#fff' }}
          >
            Faire le check-in →
          </Link>
        </div>
      )}

      {/* ── Main content (when readiness loaded) ── */}
      {readiness && (
        <>
          {/* Status banner */}
          <VetoStatus readiness={readiness} />

          {/* Main grid: Gauge + EA */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

            {/* Gauge card */}
            <div
              className="rounded-xl p-5 flex flex-col items-center gap-2"
              style={{ background: '#14141f', border: '1px solid #22223a' }}
            >
              <AllostaticGauge score={Math.round(readiness.allostatic_score)} size={200} />

              {/* Divergence info */}
              {readiness.divergence_flag !== 'none' && (
                <div
                  className="w-full rounded-lg px-3 py-2 text-xs"
                  style={{
                    background: readiness.divergence_flag === 'high' ? '#ef444415' : '#f59e0b15',
                    border: `1px solid ${readiness.divergence_flag === 'high' ? '#ef444430' : '#f59e0b30'}`,
                    color: readiness.divergence_flag === 'high' ? '#ef4444' : '#f59e0b',
                  }}
                >
                  Divergence objectif/subjectif : {Math.round(readiness.divergence)} pts
                </div>
              )}
            </div>

            {/* Right column: stats */}
            <div className="flex flex-col gap-4">
              <EnergyAvailabilityCard ea={readiness.energy_availability} />

              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  label="Readiness"
                  value={Math.round(readiness.final_readiness)}
                  unit="/100"
                  sub={`Obj ${Math.round(readiness.objective_score)} / Subj ${Math.round(readiness.subjective_score)}`}
                  color={trafficColor(readiness.traffic_light)}
                />
                <StatCard
                  label="Cap intensité"
                  value={Math.round(readiness.intensity_cap * 100)}
                  unit="%"
                  sub="Limite recommandée"
                  color={allostaticColor(readiness.allostatic_score)}
                />
              </div>
            </div>
          </div>

          {/* Insights */}
          <InsightsPanel insights={readiness.insights} />
        </>
      )}

      {/* ── History chart (when available) ── */}
      {history.length > 0 && <HistoryCharts history={history} />}

      {/* ── Quick links ── */}
      <div className="flex gap-3 flex-wrap">
        <Link
          href="/check-in"
          className="text-sm px-4 py-2 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#5b5fef', color: '#fff' }}
        >
          {readiness ? 'Modifier le check-in' : 'Check-in →'}
        </Link>
        <Link
          href="/dashboard"
          className="text-sm px-4 py-2 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#1a1a28', border: '1px solid #22223a', color: '#eeeef4' }}
        >
          Dashboard
        </Link>
      </div>
    </div>
  )
}
