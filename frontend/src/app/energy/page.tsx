'use client'
import Link from 'next/link'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid,
} from 'recharts'
import { AllostaticGauge } from '@/components/ui/allostatic-gauge'
import {
  ENERGY_TODAY,
  ALLOSTATIC_HISTORY_7D,
  HRV_HISTORY_7D,
  allostaticZone,
  eaStatus,
} from '../../../mock-data/simon'

// ── Color helpers ──────────────────────────────────────────────────────────

function zoneColor(zone: 'green' | 'yellow' | 'red' | 'critical'): string {
  return { green: '#10b981', yellow: '#f59e0b', red: '#ef4444', critical: '#dc2626' }[zone]
}

function eaColor(status: 'optimal' | 'suboptimal' | 'critical'): string {
  return { optimal: '#10b981', suboptimal: '#f59e0b', critical: '#ef4444' }[status]
}

function eaLabel(status: 'optimal' | 'suboptimal' | 'critical'): string {
  return { optimal: 'Optimal', suboptimal: 'Sous-optimal', critical: 'Critique' }[status]
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
      <p
        className="text-xs font-medium tracking-widest uppercase"
        style={{ color: '#5c5c7a' }}
      >
        {label}
      </p>
      <div className="flex items-end gap-1 mt-1">
        <span
          className="text-3xl font-bold leading-none"
          style={{ fontFamily: "'Space Mono', monospace", color }}
        >
          {value}
        </span>
        {unit && (
          <span className="text-sm mb-0.5" style={{ color: '#5c5c7a' }}>
            {unit}
          </span>
        )}
      </div>
      {sub && (
        <p className="text-xs mt-0.5" style={{ color: '#5c5c7a' }}>
          {sub}
        </p>
      )}
    </div>
  )
}

// ── EA Bar ────────────────────────────────────────────────────────────────

function EnergyAvailabilityCard() {
  const ea = ENERGY_TODAY.energy_availability
  const status = eaStatus(ea, 'male')
  const color = eaColor(status)
  const pct = Math.min(100, (ea / 60) * 100) // max display at 60 kcal

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
          {eaLabel(status)}
        </span>
      </div>

      <div className="flex items-end gap-1">
        <span
          className="text-3xl font-bold leading-none"
          style={{ fontFamily: "'Space Mono', monospace", color }}
        >
          {ea}
        </span>
        <span className="text-sm mb-0.5" style={{ color: '#5c5c7a' }}>kcal/kg FFM</span>
      </div>

      {/* Progress bar with threshold markers */}
      <div className="relative">
        <div className="h-2 rounded-full overflow-hidden" style={{ background: '#22223a' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
        {/* Threshold line at 45 */}
        <div
          className="absolute top-0 bottom-0 w-px"
          style={{ left: `${(45 / 60) * 100}%`, background: '#10b981', opacity: 0.5 }}
        />
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

function ChartTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { value: number; color: string; name: string }[]
  label?: string
}) {
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

// ── Veto status banner ────────────────────────────────────────────────────

function VetoStatus() {
  const zone = allostaticZone(ENERGY_TODAY.allostatic_score)
  const cap = ENERGY_TODAY.recommended_intensity_cap

  if (ENERGY_TODAY.veto_triggered) {
    return (
      <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: '#ef444415', border: '1px solid #ef444440' }}>
        <span className="text-xl mt-0.5">🔴</span>
        <div>
          <p className="font-semibold text-sm" style={{ color: '#ef4444' }}>Séance bloquée</p>
          <p className="text-xs mt-0.5" style={{ color: '#ef444490' }}>{ENERGY_TODAY.veto_reason}</p>
        </div>
      </div>
    )
  }

  if (zone === 'yellow' || zone === 'red') {
    return (
      <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: '#f59e0b12', border: '1px solid #f59e0b40' }}>
        <span className="text-xl mt-0.5">🟡</span>
        <div>
          <p className="font-semibold text-sm" style={{ color: '#f59e0b' }}>
            Intensité réduite · cap {Math.round(cap * 100)}%
          </p>
          <p className="text-xs mt-0.5" style={{ color: '#f59e0b90' }}>
            Charge allostatique modérée — un indicateur hors zone.
            {' '}Journée de travail lourde (cognitif +65).
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

// ── Main Page ─────────────────────────────────────────────────────────────

export default function EnergyPage() {
  const zone = allostaticZone(ENERGY_TODAY.allostatic_score)
  const zColor = zoneColor(zone)
  const hrvDelta = ENERGY_TODAY.hrv_rmssd - ENERGY_TODAY.hrv_baseline
  const hrvDeltaStr = (hrvDelta > 0 ? '+' : '') + hrvDelta.toFixed(0)

  return (
    <div className="space-y-6 pb-12">

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
            Tableau de Bord Énergie
          </p>
          <h1 className="text-2xl font-bold mt-0.5" style={{ letterSpacing: '-0.02em' }}>
            Jeudi 10 Avril
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {ENERGY_TODAY.check_in_done ? (
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

      {/* ── Status banner ── */}
      <VetoStatus />

      {/* ── Main grid: Gauge + EA ── */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">

        {/* Gauge card */}
        <div
          className="rounded-xl p-5 flex flex-col items-center gap-2"
          style={{ background: '#14141f', border: '1px solid #22223a' }}
        >
          <AllostaticGauge score={ENERGY_TODAY.allostatic_score} size={200} />

          {/* Component breakdown */}
          <div className="w-full mt-2 space-y-1.5">
            {[
              { label: 'HRV / Autonomique', value: 30, fill: '#ef4444', pct: 30 },
              { label: 'Sommeil', value: 62, fill: '#f59e0b', pct: 62 * 0.25 },
              { label: 'Charge cognitive', value: 65, fill: '#ef4444', pct: 65 * 0.20 },
              { label: 'Stress déclaré', value: 30, fill: '#10b981', pct: 30 * 0.15 },
            ].map(row => (
              <div key={row.label} className="flex items-center gap-2 text-xs">
                <span className="w-32 shrink-0" style={{ color: '#5c5c7a' }}>{row.label}</span>
                <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#22223a' }}>
                  <div className="h-full rounded-full" style={{ width: `${Math.min(100, row.value)}%`, background: row.fill }} />
                </div>
                <span className="w-8 text-right font-mono" style={{ color: '#8888a8' }}>{row.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right column: EA + HRV + Sleep */}
        <div className="flex flex-col gap-4">
          <EnergyAvailabilityCard />

          <div className="grid grid-cols-2 gap-3">
            <StatCard
              label="HRV (RMSSD)"
              value={ENERGY_TODAY.hrv_rmssd}
              unit="ms"
              sub={`${hrvDeltaStr}ms vs baseline`}
              color={ENERGY_TODAY.hrv_rmssd < ENERGY_TODAY.hrv_baseline ? '#f59e0b' : '#10b981'}
            />
            <StatCard
              label="Sommeil"
              value={ENERGY_TODAY.sleep_hours}
              unit="h"
              sub={`Qualité ${ENERGY_TODAY.sleep_quality}/100`}
              color={ENERGY_TODAY.sleep_hours >= 7 ? '#10b981' : '#f59e0b'}
            />
          </div>

          <StatCard
            label="FC Repos"
            value={ENERGY_TODAY.resting_hr}
            unit="bpm"
            sub="Dans la norme"
            color="#eeeef4"
          />
        </div>
      </div>

      {/* ── 7-Day History charts ── */}
      <div
        className="rounded-xl p-5"
        style={{ background: '#14141f', border: '1px solid #22223a' }}
      >
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-medium tracking-widest uppercase" style={{ color: '#5c5c7a' }}>
            Historique 7 Jours
          </p>
        </div>

        <div className="space-y-6">
          {/* Allostatic score chart */}
          <div>
            <p className="text-xs mb-3" style={{ color: '#8888a8' }}>Allostatic Score</p>
            <ResponsiveContainer width="100%" height={100}>
              <LineChart data={ALLOSTATIC_HISTORY_7D} margin={{ left: -20, right: 10, top: 4, bottom: 0 }}>
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

          {/* HRV chart */}
          <div>
            <p className="text-xs mb-3" style={{ color: '#8888a8' }}>HRV RMSSD (ms)</p>
            <ResponsiveContainer width="100%" height={100}>
              <LineChart data={HRV_HISTORY_7D} margin={{ left: -20, right: 10, top: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#22223a" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#5c5c7a', fontFamily: 'Space Grotesk' }} axisLine={false} tickLine={false} />
                <YAxis domain={[55, 90]} tick={{ fontSize: 10, fill: '#5c5c7a', fontFamily: 'Space Mono' }} axisLine={false} tickLine={false} />
                <ReferenceLine y={ENERGY_TODAY.hrv_baseline} stroke="#10b98150" strokeDasharray="4 4" label={{ value: 'baseline', position: 'right', fill: '#10b98170', fontSize: 10 }} />
                <Tooltip content={(props) => <ChartTooltip {...props} />} />
                <Line
                  type="monotone"
                  dataKey="hrv"
                  name="ms"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#10b981', stroke: '#08080e', strokeWidth: 2 }}
                  activeDot={{ r: 4, fill: '#10b981' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Quick links ── */}
      <div className="flex gap-3 flex-wrap">
        <Link
          href="/check-in"
          className="text-sm px-4 py-2 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#5b5fef', color: '#fff' }}
        >
          Modifier le check-in
        </Link>
        <Link
          href="/energy/cycle"
          className="text-sm px-4 py-2 rounded-lg font-medium transition-opacity hover:opacity-80"
          style={{ background: '#1a1a28', border: '1px solid #22223a', color: '#eeeef4' }}
        >
          Vue cycle →
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
