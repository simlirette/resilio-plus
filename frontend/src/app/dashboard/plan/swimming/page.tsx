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

interface SwimSet {
  distance_m: number;
  description: string;
  rest_s: number;
  [key: string]: unknown;
}

interface SwimSession {
  session_number: number;
  session_type: string;
  total_distance_m: number;
  css_target_sec_per_100m?: number;
  sets?: SwimSet[];
  coaching_cues?: string[];
  [key: string]: unknown;
}

interface SwimPlan {
  agent?: string;
  technique_level?: string;
  css_sec_per_100m?: number;
  weekly_volume_km?: number;
  sessions?: SwimSession[];
  coaching_notes?: string[];
  notes?: string;
  [key: string]: unknown;
}

const SESSION_TYPE_BADGE: Record<string, string> = {
  technique: "bg-blue-900 text-blue-200",
  aerobic_endurance: "bg-emerald-900 text-emerald-200",
  threshold: "bg-amber-900 text-amber-200",
};

const SESSION_TYPE_LABELS: Record<string, string> = {
  technique: "Technique",
  aerobic_endurance: "Endurance aérobie",
  threshold: "Seuil",
};

const TECHNIQUE_LEVEL_BADGE: Record<string, string> = {
  beginner: "bg-blue-900 text-blue-200",
  intermediate: "bg-amber-900 text-amber-200",
  advanced: "bg-emerald-900 text-emerald-200",
};

const TECHNIQUE_LEVEL_LABELS: Record<string, string> = {
  beginner: "Débutant",
  intermediate: "Intermédiaire",
  advanced: "Avancé",
};

function formatCss(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;
}

export default function SwimmingPlanPage() {
  const [plan, setPlan] = useState<SwimPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .post<SwimPlan>("/plan/swimming", { athlete_state: SIMON_ATHLETE_STATE })
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
  const totalDistanceM = sessions.reduce((sum, s) => sum + (s.total_distance_m ?? 0), 0);
  const techniqueLevel = plan.technique_level ?? "";
  const css = plan.css_sec_per_100m;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-100">Plan natation — Détail</h2>
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
          <p className="text-2xl font-bold text-slate-100">{totalDistanceM.toLocaleString()} m</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500">CSS (ss/100m)</p>
          <p className="text-2xl font-bold text-slate-100">
            {css != null ? formatCss(css) : "—"}
          </p>
        </div>
      </div>

      {/* Technique level badge */}
      {techniqueLevel && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Niveau technique :</span>
          <span className={`px-2 py-0.5 text-xs rounded ${TECHNIQUE_LEVEL_BADGE[techniqueLevel] ?? "bg-slate-800 text-slate-300"}`}>
            {TECHNIQUE_LEVEL_LABELS[techniqueLevel] ?? techniqueLevel}
          </span>
        </div>
      )}

      {/* Session cards */}
      <div className="space-y-3">
        {sessions.map((s, i) => {
          const typeKey = String(s.session_type ?? "").toLowerCase();
          const badgeClass = SESSION_TYPE_BADGE[typeKey] ?? "bg-slate-800 text-slate-300";
          const typeLabel = SESSION_TYPE_LABELS[typeKey] ?? (s.session_type ? String(s.session_type) : "Séance");
          const sets = s.sets ?? [];
          const cues = s.coaching_cues ?? [];

          return (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
              {/* Session header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-200">Séance {s.session_number}</span>
                  <span className={`px-2 py-0.5 text-xs rounded ${badgeClass}`}>{typeLabel}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>{s.total_distance_m} m</span>
                  {s.css_target_sec_per_100m != null && (
                    <span>CSS {formatCss(s.css_target_sec_per_100m)}/100m</span>
                  )}
                </div>
              </div>

              {/* Sets table */}
              {sets.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-800">
                        <th className="text-left py-1.5 pr-3 text-slate-500 font-medium">Distance</th>
                        <th className="text-left py-1.5 pr-3 text-slate-500 font-medium">Description</th>
                        <th className="text-left py-1.5 text-slate-500 font-medium">Repos</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sets.map((set, si) => (
                        <tr key={si} className="border-b border-slate-800/50 last:border-0">
                          <td className="py-1.5 pr-3 text-slate-300 whitespace-nowrap">{set.distance_m} m</td>
                          <td className="py-1.5 pr-3 text-slate-400 leading-relaxed">{set.description}</td>
                          <td className="py-1.5 text-slate-400 whitespace-nowrap">{set.rest_s}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Coaching cues */}
              {cues.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Conseils techniques</p>
                  <ul className="space-y-0.5">
                    {cues.map((cue, ci) => (
                      <li key={ci} className="text-xs text-slate-400">• {cue}</li>
                    ))}
                  </ul>
                </div>
              )}
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

      {/* LLM notes */}
      {plan.notes && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Note</h3>
          <p className="text-sm text-slate-300 leading-relaxed">{plan.notes}</p>
        </div>
      )}
    </div>
  );
}
