"use client";

import { useState, FormEvent } from "react";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────

interface ActualWorkout {
  sport: "running" | "lifting";
  date: string;
  completed: boolean;
  actual_data: Record<string, unknown>;
}

interface Adjustment {
  type: "volume_reduction" | "rest_week" | "intensity_reduction" | "volume_increase";
  reason: string;
  pct?: number;
}

interface WeeklyReport {
  agent: string;
  week_reviewed: number;
  completion_rate: number;
  sessions_completed: number;
  sessions_planned: number;
  trimp_total: number;
  acwr_before: number | null;
  acwr_after: number | null;
  adjustments: Adjustment[];
  next_week_notes: string;
}

// ── Simon demo athlete state (same as calendar page) ─────────────────────

const SIMON_ATHLETE_STATE = {
  athlete_id: "00000000-0000-0000-0000-000000000001",
  updated_at: new Date().toISOString(),
  profile: {
    first_name: "Simon", age: 32, sex: "M", weight_kg: 78.5, height_cm: 178,
    body_fat_percent: 16.5, resting_hr: 58, max_hr_measured: 188,
    active_sports: ["running", "lifting"],
    available_days: {
      monday:    { available: true,  max_hours: 1.5, preferred_time: "morning" },
      tuesday:   { available: true,  max_hours: 1.5, preferred_time: "evening" },
      wednesday: { available: true,  max_hours: 1.0, preferred_time: "morning" },
      thursday:  { available: true,  max_hours: 1.5, preferred_time: "evening" },
      friday:    { available: false, max_hours: 0,   preferred_time: null },
      saturday:  { available: true,  max_hours: 2.5, preferred_time: "morning" },
      sunday:    { available: true,  max_hours: 2.0, preferred_time: "morning" },
    },
    training_history: {
      total_years_training: 5, years_running: 2, years_lifting: 4, years_swimming: 0.5,
      current_weekly_volume_hours: 7, longest_run_ever_km: 15, current_5k_time_min: 28.5,
      current_10k_time_min: null, current_half_marathon_min: null,
      estimated_1rm: { squat: 120, bench_press: 85, deadlift: 140, overhead_press: 55 },
    },
    injuries_history: [],
    lifestyle: {
      work_type: "desk_sedentary", work_hours_per_day: 8, commute_active: false,
      sleep_avg_hours: 7.2, stress_level: "moderate", alcohol_per_week: 2, smoking: false,
    },
    goals: {
      primary: "run_sub_25_5k", secondary: "maintain_muscle_mass",
      tertiary: "improve_swimming_technique", timeline_weeks: 16,
      priority_hierarchy: ["running_5k", "hypertrophy_maintenance", "swimming_technique"],
    },
    equipment: {
      gym_access: true,
      gym_equipment: ["barbell", "dumbbells", "cables", "machines", "pull_up_bar"],
      pool_access: true, pool_type: "25m_indoor", outdoor_running: true, treadmill: false,
      heart_rate_monitor: true, gps_watch: "garmin_forerunner_265", power_meter_bike: false,
    },
  },
  current_phase: { macrocycle: "base_building", mesocycle_week: 3, mesocycle_length: 4 },
  running_profile: {
    vdot: 38.2,
    training_paces: {
      easy_min_per_km: "6:24", easy_max_per_km: "7:06", marathon_pace_per_km: "5:42",
      threshold_pace_per_km: "5:18", interval_pace_per_km: "4:48",
      repetition_pace_per_km: "4:24", long_run_pace_per_km: "6:36",
    },
    weekly_km_current: 22, weekly_km_target: 35, max_long_run_km: 12, cadence_avg: 168, preferred_terrain: "road",
  },
  lifting_profile: {
    training_split: "upper_lower", sessions_per_week: 3,
    current_volume_per_muscle: { quadriceps: 8, hamstrings: 6, chest: 10, back: 12, shoulders: 8, biceps: 6, triceps: 6, calves: 4 },
    volume_landmarks: {
      quadriceps: { mev: 6, mav: 10, mrv_hybrid: 12 }, hamstrings: { mev: 4, mav: 8, mrv_hybrid: 10 },
      chest: { mev: 6, mav: 14, mrv_hybrid: 18 }, back: { mev: 6, mav: 14, mrv_hybrid: 20 },
      shoulders: { mev: 6, mav: 12, mrv_hybrid: 16 }, biceps: { mev: 4, mav: 10, mrv_hybrid: 14 },
      triceps: { mev: 4, mav: 8, mrv_hybrid: 12 }, calves: { mev: 4, mav: 8, mrv_hybrid: 6 },
    },
    progression_model: "double_progression", rir_target_range: [1, 3],
  },
  nutrition_profile: {
    tdee_estimated: 2800, macros_target: { protein_g: 160, carbs_g: 300, fat_g: 80 },
    supplements_current: ["creatine_5g"], dietary_restrictions: [], allergies: [],
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────

function getWeekDates(): { label: string; iso: string }[] {
  const today = new Date();
  const day = today.getDay(); // 0=Sun
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((day + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return {
      label: d.toLocaleDateString("fr-CA", { weekday: "short", day: "numeric" }),
      iso: d.toISOString().slice(0, 10),
    };
  });
}

function completionColour(rate: number): string {
  if (rate >= 0.8) return "bg-emerald-900 text-emerald-200";
  if (rate >= 0.6) return "bg-yellow-900 text-yellow-200";
  return "bg-red-900 text-red-200";
}

const ADJUSTMENT_LABELS: Record<string, string> = {
  volume_reduction: "↓ Réduire le volume",
  rest_week: "🛑 Semaine de repos",
  intensity_reduction: "↓ Réduire l'intensité",
  volume_increase: "↑ Augmenter le volume",
};

// ── Component ─────────────────────────────────────────────────────────────

export default function WeeklyReviewPage() {
  const weekDates = getWeekDates();
  const [workouts, setWorkouts] = useState<ActualWorkout[]>([]);
  const [form, setForm] = useState({
    sport: "running" as "running" | "lifting",
    date: weekDates[0].iso,
    completed: true,
    duration_min: "",
    distance_km: "",
    avg_hr: "",
    run_type: "",
    session_type: "",
  });
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function addWorkout(e: FormEvent) {
    e.preventDefault();
    const actual_data: Record<string, unknown> = {};
    if (form.sport === "running" && form.completed) {
      if (form.duration_min) actual_data["duration_min"] = parseFloat(form.duration_min);
      if (form.distance_km) actual_data["distance_km"] = parseFloat(form.distance_km);
      if (form.avg_hr) actual_data["avg_hr"] = parseInt(form.avg_hr, 10);
      if (form.run_type) actual_data["type"] = form.run_type;
    }
    if (form.sport === "lifting" && form.completed) {
      if (form.session_type) actual_data["session_type"] = form.session_type;
      if (form.duration_min) actual_data["duration_min"] = parseFloat(form.duration_min);
    }
    setWorkouts((prev) => [
      ...prev,
      { sport: form.sport, date: form.date, completed: form.completed, actual_data },
    ]);
  }

  function removeWorkout(i: number) {
    setWorkouts((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function submitReview() {
    setError("");
    setSubmitting(true);
    try {
      const result = await api.post<WeeklyReport>("/workflow/weekly-review", {
        athlete_state: SIMON_ATHLETE_STATE,
        actual_workouts: workouts,
      });
      setReport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du bilan");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass = "px-2 py-1 text-sm rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500";
  const labelClass = "text-xs text-slate-400";

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-100">Bilan hebdomadaire</h2>

      {/* ── Workout Logger ─────────────────────────────────────────── */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
        <h3 className="text-sm font-semibold text-slate-300">Ajouter une séance</h3>

        <form onSubmit={addWorkout} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className={labelClass}>Sport</label>
              <select
                value={form.sport}
                onChange={(e) => setForm((f) => ({ ...f, sport: e.target.value as "running" | "lifting" }))}
                className={inputClass + " w-full"}
              >
                <option value="running">Course</option>
                <option value="lifting">Musculation</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className={labelClass}>Date</label>
              <select
                value={form.date}
                onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
                className={inputClass + " w-full"}
              >
                {weekDates.map((d) => (
                  <option key={d.iso} value={d.iso}>{d.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className={labelClass}>Séance :</label>
            <button
              type="button"
              onClick={() => setForm((f) => ({ ...f, completed: true }))}
              className={`px-3 py-1 text-xs rounded border transition-colors ${form.completed ? "bg-emerald-700 border-emerald-600 text-white" : "bg-slate-800 border-slate-700 text-slate-400"}`}
            >
              Complétée
            </button>
            <button
              type="button"
              onClick={() => setForm((f) => ({ ...f, completed: false }))}
              className={`px-3 py-1 text-xs rounded border transition-colors ${!form.completed ? "bg-red-900 border-red-700 text-red-200" : "bg-slate-800 border-slate-700 text-slate-400"}`}
            >
              Manquée
            </button>
          </div>

          {form.completed && (
            <div className="grid grid-cols-3 gap-3">
              {form.sport === "running" && (
                <>
                  <div className="space-y-1">
                    <label className={labelClass}>Durée (min)*</label>
                    <input type="number" value={form.duration_min} onChange={(e) => setForm((f) => ({ ...f, duration_min: e.target.value }))} className={inputClass + " w-full"} placeholder="45" min="1" />
                  </div>
                  <div className="space-y-1">
                    <label className={labelClass}>Distance (km)</label>
                    <input type="number" step="0.1" value={form.distance_km} onChange={(e) => setForm((f) => ({ ...f, distance_km: e.target.value }))} className={inputClass + " w-full"} placeholder="7.5" />
                  </div>
                  <div className="space-y-1">
                    <label className={labelClass}>FC moy (bpm)</label>
                    <input type="number" value={form.avg_hr} onChange={(e) => setForm((f) => ({ ...f, avg_hr: e.target.value }))} className={inputClass + " w-full"} placeholder="145" />
                  </div>
                  <div className="space-y-1 col-span-3">
                    <label className={labelClass}>Type de séance</label>
                    <select value={form.run_type} onChange={(e) => setForm((f) => ({ ...f, run_type: e.target.value }))} className={inputClass + " w-full"}>
                      <option value="">— Non précisé —</option>
                      <option value="easy">Facile (Z1)</option>
                      <option value="tempo">Tempo (Z2)</option>
                      <option value="interval">Intervalles (Z3)</option>
                    </select>
                  </div>
                </>
              )}
              {form.sport === "lifting" && (
                <>
                  <div className="space-y-1">
                    <label className={labelClass}>Durée (min)</label>
                    <input type="number" value={form.duration_min} onChange={(e) => setForm((f) => ({ ...f, duration_min: e.target.value }))} className={inputClass + " w-full"} placeholder="60" min="1" />
                  </div>
                  <div className="space-y-1 col-span-2">
                    <label className={labelClass}>Type de séance</label>
                    <select value={form.session_type} onChange={(e) => setForm((f) => ({ ...f, session_type: e.target.value }))} className={inputClass + " w-full"}>
                      <option value="">— Non précisé —</option>
                      <option value="hypertrophy">Hypertrophie</option>
                      <option value="strength">Force</option>
                      <option value="power">Puissance</option>
                    </select>
                  </div>
                </>
              )}
            </div>
          )}

          <button type="submit" className="px-4 py-1.5 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors">
            + Ajouter
          </button>
        </form>

        {/* Workout list */}
        {workouts.length > 0 && (
          <div className="space-y-1 pt-2 border-t border-slate-800">
            <p className="text-xs text-slate-500 mb-2">{workouts.length} séance{workouts.length > 1 ? "s" : ""} enregistrée{workouts.length > 1 ? "s" : ""}</p>
            {workouts.map((w, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-slate-800 rounded px-3 py-1.5">
                <span>
                  <span className={`font-medium ${w.sport === "running" ? "text-emerald-400" : "text-blue-400"}`}>
                    {w.sport === "running" ? "Course" : "Muscu"}
                  </span>
                  {" · "}{w.date}
                  {" · "}<span className={w.completed ? "text-emerald-400" : "text-red-400"}>{w.completed ? "✓" : "✗"}</span>
                </span>
                <button onClick={() => removeWorkout(i)} className="text-slate-500 hover:text-red-400 transition-colors">✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Submit ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <button
          onClick={submitReview}
          disabled={submitting}
          className="px-5 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium transition-colors"
        >
          {submitting ? "Analyse en cours..." : "Soumettre le bilan"}
        </button>
        <span className="text-xs text-slate-500">
          {workouts.length === 0 ? "Aucune séance (bilan vide)" : `${workouts.length} séance(s)`}
        </span>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {/* ── Report ────────────────────────────────────────────────── */}
      {report && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-5">
          <h3 className="text-sm font-semibold text-slate-300">Rapport — Semaine {report.week_reviewed}</h3>

          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard
              label="Séances"
              value={`${report.sessions_completed} / ${report.sessions_planned}`}
              badge={`${Math.round(report.completion_rate * 100)}%`}
              badgeClass={completionColour(report.completion_rate)}
            />
            <StatCard label="TRIMP total" value={report.trimp_total.toFixed(0)} badge="pts" badgeClass="bg-slate-800 text-slate-300" />
            <StatCard
              label="ACWR avant"
              value={report.acwr_before?.toFixed(2) ?? "—"}
              badge={acwrZone(report.acwr_before)}
              badgeClass={acwrBadge(report.acwr_before)}
            />
            <StatCard
              label="ACWR après"
              value={report.acwr_after?.toFixed(2) ?? "—"}
              badge={acwrZone(report.acwr_after)}
              badgeClass={acwrBadge(report.acwr_after)}
            />
          </div>

          {/* Adjustments */}
          {report.adjustments.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recommandations</p>
              <div className="flex flex-wrap gap-2">
                {report.adjustments.map((adj, i) => (
                  <span key={i} className="px-3 py-1 text-xs rounded-full bg-slate-800 border border-slate-700 text-slate-200">
                    {ADJUSTMENT_LABELS[adj.type] ?? adj.type}
                    {adj.pct != null ? ` (${adj.pct}%)` : ""}
                  </span>
                ))}
              </div>
            </div>
          )}
          {report.adjustments.length === 0 && (
            <p className="text-sm text-emerald-400">✓ Charge optimale — maintenir le programme actuel.</p>
          )}

          {/* Coaching notes */}
          {report.next_week_notes && (
            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Note du coach</p>
              <p className="text-sm text-slate-300 italic">{report.next_week_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({ label, value, badge, badgeClass }: { label: string; value: string; badge: string; badgeClass: string }) {
  return (
    <div className="bg-slate-800 rounded-lg p-3 space-y-1">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-bold text-slate-100">{value}</p>
      <span className={`inline-block px-2 py-0.5 text-xs rounded ${badgeClass}`}>{badge}</span>
    </div>
  );
}

function acwrZone(val: number | null): string {
  if (val === null) return "—";
  if (val > 1.5) return "Danger";
  if (val > 1.3) return "Caution";
  if (val >= 0.8) return "Safe";
  return "Low";
}

function acwrBadge(val: number | null): string {
  if (val === null) return "bg-slate-700 text-slate-400";
  if (val > 1.5) return "bg-red-900 text-red-200";
  if (val > 1.3) return "bg-yellow-900 text-yellow-200";
  return "bg-emerald-900 text-emerald-200";
}
