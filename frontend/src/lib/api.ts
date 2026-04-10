// frontend/src/lib/api.ts
const API_BASE = 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) throw new ApiError(401, 'Unauthorized')
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, (body as { detail?: string }).detail ?? 'Request failed')
  }
  return res.json() as Promise<T>
}

export type Sport = 'running' | 'lifting' | 'swimming' | 'biking'

export interface FatigueScore {
  local_muscular: number
  cns_load: number
  metabolic_cost: number
  recovery_hours: number
  affected_muscles: string[]
}

export interface WorkoutSlot {
  date: string
  sport: Sport
  workout_type: string
  duration_min: number
  fatigue_score: FatigueScore
  notes: string
}

export interface TrainingPlanResponse {
  id: string
  athlete_id: string
  start_date: string
  end_date: string
  phase: string
  total_weekly_hours: number
  acwr: number
  sessions: WorkoutSlot[]
}

export interface WeekStatusResponse {
  week_number: number
  plan: TrainingPlanResponse
  planned_hours: number
  actual_hours: number
  completion_pct: number
  acwr: number | null
}

export interface WeeklyReviewResponse {
  review_id: string
  week_number: number
  planned_hours: number
  actual_hours: number
  acwr: number
  adjustment_applied: number
  next_week_suggestion: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  athlete_id: string
}

export interface OnboardingResponse {
  athlete: Record<string, unknown>
  plan: TrainingPlanResponse
  access_token: string
  token_type: string
}

export interface OnboardingRequestData {
  email: string
  password: string
  plan_start_date: string
  name: string
  age: number
  sex: 'M' | 'F' | 'other'
  weight_kg: number
  height_cm: number
  primary_sport: Sport
  sports: Sport[]
  goals: string[]
  available_days: number[]
  hours_per_week: number
}

export interface WeeklyReviewRequestData {
  week_end_date: string
  readiness_score?: number
  hrv_rmssd?: number
  sleep_hours_avg?: number
  comment?: string
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  onboarding: (data: OnboardingRequestData) =>
    request<OnboardingResponse>('/athletes/onboarding', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getWeekStatus: (athleteId: string) =>
    request<WeekStatusResponse>(`/athletes/${athleteId}/week-status`),

  getPlan: (athleteId: string) =>
    request<TrainingPlanResponse>(`/athletes/${athleteId}/plan`),

  submitReview: (athleteId: string, data: WeeklyReviewRequestData) =>
    request<WeeklyReviewResponse>(`/athletes/${athleteId}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
