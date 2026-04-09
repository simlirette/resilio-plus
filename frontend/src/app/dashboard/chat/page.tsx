"use client";

import { useState, FormEvent, useRef, useEffect } from "react";

// Simon demo athlete state (copied from plan/running/page.tsx)
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

interface PendingDecision {
  conflict_id?: string;
  situation: string;
  recommendation: string;
  status?: string;
}

interface WorkflowResponse {
  status: "complete" | "awaiting_decision";
  thread_id?: string;
  pending_decision?: PendingDecision;
  unified_plan?: Record<string, unknown>;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SYSTEM_MESSAGE: Message = {
  role: "assistant",
  content:
    "Bonjour. Je suis le Head Coach Resilio+. Envoyez n'importe quel message pour générer votre plan de la semaine. Je coordonnerai tous vos agents spécialistes.",
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("resilio_token");
}

async function callWorkflow(path: string, body: Record<string, unknown>): Promise<WorkflowResponse> {
  const token = getToken();
  const resp = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok && resp.status !== 202) {
    let errMsg = `Erreur API (${resp.status})`;
    try {
      const errData = await resp.json();
      if (errData?.detail) errMsg = String(errData.detail);
    } catch {
      // ignore parse errors
    }
    throw new Error(errMsg);
  }

  return resp.json() as Promise<WorkflowResponse>;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([SYSTEM_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [awaitingConfirm, setAwaitingConfirm] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, awaitingConfirm]);

  function addMessage(msg: Message) {
    setMessages((prev) => [...prev, msg]);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");
    addMessage({ role: "user", content: userText });
    setLoading(true);

    try {
      const data = await callWorkflow("/workflow/plan", { athlete_state: SIMON_ATHLETE_STATE });

      if (data.status === "awaiting_decision" && data.pending_decision) {
        const pd = data.pending_decision;
        const assistantText = `${pd.situation}\n\n${pd.recommendation}`;
        addMessage({ role: "assistant", content: assistantText });
        setThreadId(data.thread_id ?? null);
        setAwaitingConfirm(true);
      } else if (data.status === "complete") {
        addMessage({ role: "assistant", content: "Plan généré avec succès. Consultez le Calendrier pour voir vos séances." });
      } else {
        addMessage({ role: "assistant", content: "Réponse inattendue du serveur. Réessayez." });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      const isNetwork = msg.toLowerCase().includes("fetch") || msg.toLowerCase().includes("network") || msg.toLowerCase().includes("failed");
      addMessage({
        role: "assistant",
        content: isNetwork
          ? "Erreur de connexion à l'API. Vérifiez que le backend est démarré."
          : `Erreur : ${msg}`,
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!threadId || loading) return;
    setAwaitingConfirm(false);
    setLoading(true);

    try {
      const data = await callWorkflow("/workflow/plan/resume", {
        thread_id: threadId,
        user_decision: "CONFIRM",
      });

      if (data.status === "complete") {
        addMessage({ role: "assistant", content: "Plan déployé avec succès. Consultez le Calendrier pour voir vos séances." });
      } else if (data.status === "awaiting_decision" && data.pending_decision) {
        const pd = data.pending_decision;
        addMessage({ role: "assistant", content: `${pd.situation}\n\n${pd.recommendation}` });
        setThreadId(data.thread_id ?? threadId);
        setAwaitingConfirm(true);
      } else {
        addMessage({ role: "assistant", content: "Plan déployé. Consultez le Calendrier pour voir vos séances." });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      addMessage({ role: "assistant", content: `Erreur lors de la confirmation : ${msg}` });
    } finally {
      setLoading(false);
      setThreadId(null);
    }
  }

  function handleCancel() {
    setAwaitingConfirm(false);
    setThreadId(null);
    addMessage({ role: "assistant", content: "Plan annulé. Envoyez un nouveau message pour régénérer." });
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <h2 className="text-xl font-semibold text-slate-100 mb-4">Chat — Head Coach</h2>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-1">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-violet-700 text-white"
                  : "bg-slate-800 text-slate-200 border border-slate-700"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-lg px-4 py-2 text-sm bg-slate-800 text-slate-400 border border-slate-700 italic">
              Analyse en cours... (peut prendre 20-30 secondes)
            </div>
          </div>
        )}

        {awaitingConfirm && !loading && (
          <div className="flex justify-start gap-2 pl-1">
            <button
              onClick={handleConfirm}
              className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors"
            >
              Confirmer
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-2 text-sm rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors"
            >
              Annuler
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={awaitingConfirm ? "Confirmez ou annulez le plan ci-dessus..." : "Écrivez votre message..."}
          disabled={loading || awaitingConfirm}
          className="flex-1 px-3 py-2 text-sm rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={loading || awaitingConfirm || !input.trim()}
          className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
}
