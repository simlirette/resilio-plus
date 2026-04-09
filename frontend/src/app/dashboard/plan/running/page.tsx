"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

// Simon demo athlete state
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

interface RunSession {
  day?: string;
  type?: string;
  zone?: string;
  distance_km?: number;
  duration_min?: number;
  pace_per_km?: string;
  description?: string;
  [key: string]: unknown;
}

interface RunPlan {
  sessions?: RunSession[];
  coaching_notes?: string[];
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

const TYPE_BADGE: Record<string, string> = {
  easy: "bg-emerald-900 text-emerald-200",
  tempo: "bg-amber-900 text-amber-200",
  interval: "bg-red-900 text-red-200",
  long: "bg-violet-900 text-violet-200",
  long_run: "bg-violet-900 text-violet-200",
  repetition: "bg-orange-900 text-orange-200",
};

const TYPE_LABELS: Record<string, string> = {
  easy: "Facile (Z1)",
  tempo: "Tempo (Z2)",
  interval: "Intervalles (Z3)",
  long: "Longue sortie",
  long_run: "Longue sortie",
  repetition: "Répétitions",
};

const DAY_FR: Record<string, string> = {
  monday: "Lundi", tuesday: "Mardi", wednesday: "Mercredi",
  thursday: "Jeudi", friday: "Vendredi", saturday: "Samedi", sunday: "Dimanche",
};

export default function RunningPlanPage() {
  const [plan, setPlan] = useState<RunPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .post<RunPlan>("/plan/running", { athlete_state: SIMON_ATHLETE_STATE })
      .then(setPlan)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 text-sm">Génération du plan en cours...</div>
      </div>
    );
  }
  if (error) return <p className="text-red-400 text-sm">{error}</p>;
  if (!plan) return null;

  const sessions = plan.sessions ?? [];
  const totalKm = sessions.reduce((sum, s) => sum + (s.distance_km ?? 0), 0);
  const metadata = plan.metadata ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-100">Plan course — Détail</h2>
        <Link href="/dashboard/calendar" className="text-sm text-slate-400 hover:text-violet-400 transition-colors">
          ← Retour au calendrier
        </Link>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500">Séances</p>
          <p className="text-2xl font-bold text-slate-100">{sessions.length}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500">Volume total</p>
          <p className="text-2xl font-bold text-slate-100">{totalKm.toFixed(1)} km</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500">Phase</p>
          <p className="text-sm font-bold text-slate-100 mt-1 capitalize">
            {String(metadata["macrocycle"] ?? "Base building")}
          </p>
        </div>
      </div>

      {/* Session cards */}
      <div className="space-y-3">
        {sessions.map((s, i) => {
          const typeKey = String(s.type ?? "").toLowerCase();
          const badgeClass = TYPE_BADGE[typeKey] ?? "bg-slate-800 text-slate-300";
          const typeLabel = TYPE_LABELS[typeKey] ?? (s.type ? String(s.type) : "Séance");
          const dayFr = DAY_FR[String(s.day ?? "").toLowerCase()] ?? String(s.day ?? `Séance ${i + 1}`);
          return (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-200">{dayFr}</span>
                  <span className={`px-2 py-0.5 text-xs rounded ${badgeClass}`}>{typeLabel}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  {s.distance_km != null && <span>{s.distance_km} km</span>}
                  {s.duration_min != null && <span>{s.duration_min} min</span>}
                  {s.pace_per_km && <span>{s.pace_per_km}/km</span>}
                </div>
              </div>

              {s.description && (
                <p className="text-sm text-slate-400 leading-relaxed">{String(s.description)}</p>
              )}

              {/* Extra fields */}
              <div className="flex flex-wrap gap-2">
                {Object.entries(s)
                  .filter(([k]) => !["day", "type", "zone", "distance_km", "duration_min", "pace_per_km", "description", "sport"].includes(k))
                  .map(([k, v]) => (
                    <span key={k} className="text-xs text-slate-500 bg-slate-800 rounded px-2 py-0.5">
                      {k}: {typeof v === "object" ? JSON.stringify(v) : String(v)}
                    </span>
                  ))}
              </div>
            </div>
          );
        })}
        {sessions.length === 0 && (
          <p className="text-sm text-slate-500">Aucune séance retournée par l&apos;API.</p>
        )}
      </div>

      {/* Coaching notes */}
      {(plan.coaching_notes ?? []).length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Notes du coach</h3>
          <ul className="space-y-1">
            {(plan.coaching_notes ?? []).map((note, i) => (
              <li key={i} className="text-sm text-slate-300 italic">• {note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
