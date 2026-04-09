"use client";

import { useState } from "react";
import { api } from "@/lib/api";

// Simon demo athlete state — matches tests/conftest.py
const SIMON_ATHLETE_STATE = {
  athlete_id: "00000000-0000-0000-0000-000000000001",
  updated_at: new Date().toISOString(),
  profile: {
    first_name: "Simon",
    age: 32,
    sex: "M",
    weight_kg: 78.5,
    height_cm: 178,
    body_fat_percent: 16.5,
    resting_hr: 58,
    max_hr_measured: 188,
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
    weekly_km_current: 22, weekly_km_target: 35, max_long_run_km: 12,
    cadence_avg: 168, preferred_terrain: "road",
  },
  lifting_profile: {
    training_split: "upper_lower", sessions_per_week: 3,
    current_volume_per_muscle: {
      quadriceps: 8, hamstrings: 6, chest: 10, back: 12, shoulders: 8, biceps: 6, triceps: 6, calves: 4,
    },
    volume_landmarks: {
      quadriceps: { mev: 6, mav: 10, mrv_hybrid: 12 },
      hamstrings:  { mev: 4, mav: 8,  mrv_hybrid: 10 },
      chest:       { mev: 6, mav: 14, mrv_hybrid: 18 },
      back:        { mev: 6, mav: 14, mrv_hybrid: 20 },
      shoulders:   { mev: 6, mav: 12, mrv_hybrid: 16 },
      biceps:      { mev: 4, mav: 10, mrv_hybrid: 14 },
      triceps:     { mev: 4, mav: 8,  mrv_hybrid: 12 },
      calves:      { mev: 4, mav: 8,  mrv_hybrid: 6  },
    },
    progression_model: "double_progression", rir_target_range: [1, 3],
  },
  nutrition_profile: {
    tdee_estimated: 2800,
    macros_target: { protein_g: 160, carbs_g: 300, fat_g: 80 },
    supplements_current: ["creatine_5g"], dietary_restrictions: [], allergies: [],
  },
};

interface Session {
  day?: string;
  date?: string;
  type?: string;
  sport?: string;
  description?: string;
  [key: string]: unknown;
}

interface PlanResult {
  sessions?: Session[];
  [key: string]: unknown;
}

const DAYS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

const DAY_MAP: Record<string, string> = {
  monday: "Lundi", tuesday: "Mardi", wednesday: "Mercredi",
  thursday: "Jeudi", friday: "Vendredi", saturday: "Samedi", sunday: "Dimanche",
};

function sessionBadge(sport: string): string {
  if (sport === "running") return "bg-emerald-900 border-emerald-700 text-emerald-200";
  if (sport === "lifting") return "bg-blue-900 border-blue-700 text-blue-200";
  return "bg-slate-800 border-slate-700 text-slate-300";
}

function PlanDetail({ title, plan, sport }: { title: string; plan: PlanResult | null; sport: string }) {
  if (!plan) return null;
  const sessions = plan.sessions ?? [];
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
      <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      <div className="space-y-2">
        {sessions.length === 0 && (
          <p className="text-xs text-slate-500">Aucune séance retournée.</p>
        )}
        {sessions.map((s, i) => (
          <div key={i} className={`rounded border p-2 text-xs ${sessionBadge(sport)}`}>
            <span className="font-medium capitalize">
              {String(s.day ?? s.date ?? `Séance ${i + 1}`)}
            </span>
            {" — "}
            <span className="opacity-80">
              {String(s.type ?? s.description ?? s.sport ?? "")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const [runPlan, setRunPlan] = useState<PlanResult | null>(null);
  const [liftPlan, setLiftPlan] = useState<PlanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadPlan() {
    setLoading(true);
    setError("");
    try {
      const [run, lift] = await Promise.all([
        api.post<PlanResult>("/plan/running", { athlete_state: SIMON_ATHLETE_STATE }),
        api.post<PlanResult>("/plan/lifting", { athlete_state: SIMON_ATHLETE_STATE }),
      ]);
      setRunPlan(run);
      setLiftPlan(lift);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement du plan");
    } finally {
      setLoading(false);
    }
  }

  // Build day → sessions map
  const byDay: Record<string, Array<{ sport: string; session: Session }>> = {};
  DAYS_FR.forEach((d) => (byDay[d] = []));

  function addSessions(plan: PlanResult | null, sport: string) {
    if (!plan?.sessions) return;
    for (const s of plan.sessions) {
      const frDay = DAY_MAP[s.day?.toLowerCase() ?? ""];
      if (frDay) byDay[frDay].push({ sport, session: s });
    }
  }
  addSessions(runPlan, "running");
  addSessions(liftPlan, "lifting");

  const hasPlan = runPlan !== null || liftPlan !== null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-100">Calendrier hebdomadaire</h2>
        <button
          onClick={loadPlan}
          disabled={loading}
          className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white transition-colors"
        >
          {loading ? "Chargement..." : "Charger plan démo (Simon)"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {!hasPlan && !loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
          <p className="text-slate-400 text-sm">
            Cliquez sur &quot;Charger plan démo&quot; pour générer un plan hebdomadaire via le Head Coach.
          </p>
        </div>
      )}

      {hasPlan && (
        <div className="grid grid-cols-7 gap-2">
          {DAYS_FR.map((day) => (
            <div key={day} className="space-y-2">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider text-center pb-1 border-b border-slate-800">
                {day.slice(0, 3)}
              </div>
              {byDay[day].length === 0 ? (
                <div className="h-16 rounded border border-dashed border-slate-800 flex items-center justify-center">
                  <span className="text-xs text-slate-600">Repos</span>
                </div>
              ) : (
                byDay[day].map((item, i) => (
                  <div key={i} className={`rounded border p-2 text-xs ${sessionBadge(item.sport)}`}>
                    <div className="font-semibold capitalize mb-1">
                      {item.sport === "running" ? "Course" : "Muscu"}
                    </div>
                    <div className="truncate opacity-80">
                      {String(
                        item.session.type ??
                        item.session.description ??
                        item.session.sport ??
                        "Séance"
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      )}

      {hasPlan && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <PlanDetail title="Plan course" plan={runPlan} sport="running" />
          <PlanDetail title="Plan musculation" plan={liftPlan} sport="lifting" />
        </div>
      )}
    </div>
  );
}
