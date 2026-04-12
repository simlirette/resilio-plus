// Mock data for Simon — Hybrid Athlete: Running + Lifting + Cycling
// Realistic scenario: Week 8 of 16-week marathon training block, moderate allostatic load

export const SIMON = {
  id: 'simon-001',
  name: 'Simon',
  age: 34,
  sex: 'male',
  weight_kg: 76,
  ffm_kg: 65, // Fat-Free Mass
  sports: ['running', 'lifting', 'cycling'],
  vdot: 52,
  ftp_watts: 280,
  training_week: 8,
  plan_phase: 'build',
}

// ── ENERGY SNAPSHOT (today) ──────────────────────────────────────────────────

export const ENERGY_TODAY = {
  date: '2026-04-10',
  allostatic_score: 58,          // Moderate — one indicator out of zone
  cognitive_load: 65,            // Heavy meeting day
  energy_availability: 42,       // kcal/kg FFM — sub-optimal (threshold: 45)
  sleep_quality: 62,             // 6.8h, fragmented
  sleep_hours: 6.8,
  hrv_rmssd: 68,                 // ms — below Simon's baseline of 75
  hrv_baseline: 75,
  hrv_deviation_pct: -9.3,       // % below baseline
  resting_hr: 52,                // bpm
  recommended_intensity_cap: 0.85, // -15% from normal
  veto_triggered: false,
  veto_reason: null,
  check_in_done: true,
  check_in: {
    work_intensity: 'heavy',     // "Journée intense"
    stress_level: 'mild',        // "Léger stress"
  },
}

// Status derivation helpers
export function allostaticZone(score: number): 'green' | 'yellow' | 'red' | 'critical' {
  if (score <= 40) return 'green'
  if (score <= 60) return 'yellow'
  if (score <= 80) return 'red'
  return 'critical'
}

export function eaStatus(ea: number, sex: 'male' | 'female'): 'optimal' | 'suboptimal' | 'critical' {
  const criticalThreshold = sex === 'female' ? 30 : 25
  if (ea >= 45) return 'optimal'
  if (ea >= criticalThreshold) return 'suboptimal'
  return 'critical'
}

// ── 7-DAY ALLOSTATIC HISTORY ─────────────────────────────────────────────────

export const ALLOSTATIC_HISTORY_7D = [
  { date: '2026-04-04', score: 32, label: 'Fri' },
  { date: '2026-04-05', score: 28, label: 'Sat' },
  { date: '2026-04-06', score: 35, label: 'Sun' },
  { date: '2026-04-07', score: 48, label: 'Mon' },
  { date: '2026-04-08', score: 55, label: 'Tue' },
  { date: '2026-04-09', score: 51, label: 'Wed' },
  { date: '2026-04-10', score: 58, label: 'Thu' },
]

// ── HRV HISTORY ──────────────────────────────────────────────────────────────

export const HRV_HISTORY_7D = [
  { date: '2026-04-04', hrv: 78, label: 'Fri' },
  { date: '2026-04-05', hrv: 80, label: 'Sat' },
  { date: '2026-04-06', hrv: 76, label: 'Sun' },
  { date: '2026-04-07', hrv: 73, label: 'Mon' },
  { date: '2026-04-08', hrv: 71, label: 'Tue' },
  { date: '2026-04-09', hrv: 69, label: 'Wed' },
  { date: '2026-04-10', hrv: 68, label: 'Thu' },
]

// ── CYCLE HORMONAL (pour un profil féminin — données fictives pour démo) ─────

export const HORMONAL_DEMO = {
  enabled: true,
  cycle_length_days: 28,
  current_cycle_day: 18,
  current_phase: 'luteal' as const,
  last_period_start: '2026-03-23',
  tracking_source: 'manual' as const,
}

export const CYCLE_PHASES = [
  {
    id: 'menstrual',
    label: 'Menstruelle',
    days: [1, 2, 3, 4, 5],
    color: '#ef4444',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/50',
    textColor: 'text-red-400',
    dot: 'bg-red-500',
    description: 'Jours 1–5 · Estrogène et progestérone bas',
  },
  {
    id: 'follicular',
    label: 'Folliculaire',
    days: [6, 7, 8, 9, 10, 11, 12, 13],
    color: '#22c55e',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/50',
    textColor: 'text-green-400',
    dot: 'bg-green-500',
    description: 'Jours 6–13 · Phase optimale — gains de force',
  },
  {
    id: 'ovulation',
    label: 'Ovulation',
    days: [14, 15],
    color: '#f59e0b',
    bgColor: 'bg-amber-500/20',
    borderColor: 'border-amber-500/50',
    textColor: 'text-amber-400',
    dot: 'bg-amber-500',
    description: 'Jours 14–15 · Force max, attention ligaments',
  },
  {
    id: 'luteal',
    label: 'Lutéale',
    days: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28],
    color: '#6366f1',
    bgColor: 'bg-indigo-500/20',
    borderColor: 'border-indigo-500/50',
    textColor: 'text-indigo-400',
    dot: 'bg-indigo-500',
    description: 'Jours 16–28 · Progestérone élevée, récup. vigilance',
  },
]

export const CYCLE_ADJUSTMENTS_TODAY: Record<string, {
  agent: string
  adjustment: string
  severity: 'info' | 'caution' | 'warning'
}[]> = {
  luteal: [
    { agent: 'Lifting', adjustment: 'RPE cible réduit de 1 point — pas de 1RM', severity: 'caution' },
    { agent: 'Running', adjustment: 'Hydratation augmentée — éviter chaleur', severity: 'info' },
    { agent: 'Nutrition', adjustment: 'Protéines +0.2g/kg/jour · +200 kcal', severity: 'info' },
    { agent: 'Recovery', adjustment: 'Vigilance accrue sur signes de surentraînement', severity: 'caution' },
  ],
  menstrual: [
    { agent: 'Lifting', adjustment: 'RPE cible -1 · Aucun attempt 1RM', severity: 'warning' },
    { agent: 'Running', adjustment: 'Remplacer fractionnés par Z2 si douleurs', severity: 'caution' },
    { agent: 'Nutrition', adjustment: 'Augmenter fer, magnésium, oméga-3', severity: 'info' },
    { agent: 'Recovery', adjustment: 'Seuil veto abaissé à 40%', severity: 'warning' },
  ],
  follicular: [
    { agent: 'Lifting', adjustment: 'Semaine idéale pour PR attempts et sessions lourdes', severity: 'info' },
    { agent: 'Running', adjustment: 'Fractionnés haute intensité — timing optimal', severity: 'info' },
    { agent: 'Recovery', adjustment: 'Seuils normaux ou légèrement assouplis', severity: 'info' },
    { agent: 'Nutrition', adjustment: 'Glucides modérés OK — sensibilité insuline optimale', severity: 'info' },
  ],
  ovulation: [
    { agent: 'Lifting', adjustment: 'Performance maximale — insister sur technique', severity: 'info' },
    { agent: 'Running', adjustment: 'Éviter changements de direction brusques', severity: 'caution' },
    { agent: 'Recovery', adjustment: 'Note de risque ligamentaire ajoutée', severity: 'caution' },
    { agent: 'Nutrition', adjustment: 'Hydratation optimale — rétention d\'eau possible', severity: 'info' },
  ],
}

// ── TODAY'S TRAINING SESSION ──────────────────────────────────────────────────

export const SESSION_TODAY = {
  type: 'Tempo Run',
  sport: 'running',
  planned_duration_min: 65,
  planned_tss: 78,
  intensity_cap_applied: 0.85, // Allostatic score >40 → -15%
  adjusted_duration_min: 55,
  zone: 'Z2',
  note: 'Intensité réduite — charge allostatique modérée (58/100)',
}
