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

async function _reqRaw(path: string, init: RequestInit = {}): Promise<any> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...headers, ...(init.headers as Record<string, string> || {}) } })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json()
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
  id: string
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

export interface SessionLogResponse {
  id: string
  session_id: string
  actual_duration_min: number | null
  skipped: boolean
  rpe: number | null
  notes: string
  actual_data: Record<string, unknown>
  logged_at: string
}

export interface SessionDetailResponse {
  session_id: string
  plan_id: string
  date: string
  sport: Sport
  workout_type: string
  duration_min: number
  fatigue_score: FatigueScore
  notes: string
  log: SessionLogResponse | null
}

export interface SessionLogRequest {
  actual_duration_min?: number
  skipped?: boolean
  rpe?: number
  notes?: string
  actual_data?: Record<string, unknown>
}

export interface WeekSummary {
  plan_id: string
  week_number: number
  start_date: string
  end_date: string
  phase: string
  planned_hours: number
  sessions_total: number
  sessions_logged: number
  completion_pct: number
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

  getSession: (athleteId: string, sessionId: string) =>
    request<SessionDetailResponse>(`/athletes/${athleteId}/sessions/${sessionId}`),

  logSession: (athleteId: string, sessionId: string, data: SessionLogRequest) =>
    request<SessionLogResponse>(`/athletes/${athleteId}/sessions/${sessionId}/log`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSessionLog: (athleteId: string, sessionId: string) =>
    request<SessionLogResponse>(`/athletes/${athleteId}/sessions/${sessionId}/log`),

  getHistory: (athleteId: string) =>
    request<WeekSummary[]>(`/athletes/${athleteId}/history`),

  getConnectors: (athleteId: string): Promise<{ connectors: Array<{ provider: string; connected: boolean; expires_at?: number | null; last_sync?: string | null }> }> =>
    request(`/athletes/${athleteId}/connectors`),

  connectHevy: (athleteId: string, apiKey: string): Promise<{ provider: string; connected: boolean }> =>
    request(`/athletes/${athleteId}/connectors/hevy`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    }),

  connectTerraUserId: (athleteId: string, terraUserId: string): Promise<{ provider: string; connected: boolean }> =>
    request(`/athletes/${athleteId}/connectors/terra`, {
      method: 'POST',
      body: JSON.stringify({ terra_user_id: terraUserId }),
    }),

  disconnectConnector: (athleteId: string, provider: 'strava' | 'hevy' | 'terra'): Promise<void> =>
    request(`/athletes/${athleteId}/connectors/${provider}`, { method: 'DELETE' }),

  stravaAuthorize: (athleteId: string): Promise<{ auth_url: string }> =>
    request(`/athletes/${athleteId}/connectors/strava/authorize`, { method: 'POST' }),

  // Connector sync
  hevySync: (athleteId: string): Promise<{ synced: number; skipped: number }> =>
    request(`/athletes/${athleteId}/connectors/hevy/sync`, { method: 'POST' }),

  terraSync: (athleteId: string): Promise<{ synced: number; hrv_rmssd: number | null }> =>
    request(`/athletes/${athleteId}/connectors/terra/sync`, { method: 'POST' }),

  stravaSync: (athleteId: string): Promise<{ synced: number; skipped: number }> =>
    request(`/athletes/${athleteId}/connectors/strava/sync`, { method: 'POST' }),

  appleHealthUpload: (
    athleteId: string,
    data: { snapshot_date: string; hrv_rmssd?: number; sleep_hours?: number; hr_rest?: number }
  ): Promise<{ uploaded: boolean; snapshot_date: string }> =>
    request(`/athletes/${athleteId}/connectors/apple-health/upload`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  uploadGpx: (athleteId: string, file: File): Promise<{ imported: boolean; session_id?: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    return _reqRaw(`/athletes/${athleteId}/connectors/files/gpx`, { method: 'POST', body: formData })
  },

  uploadFit: (athleteId: string, file: File): Promise<{ imported: boolean; session_id?: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    return _reqRaw(`/athletes/${athleteId}/connectors/files/fit`, { method: 'POST', body: formData })
  },

}

// ── Analytics ──────────────────────────────────────────────────────────────
export interface AcwrPoint {
  date: string;
  acwr: number;
  acute: number;
  chronic: number;
}

export interface TrainingLoadPoint {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
}

export interface LoadAnalytics {
  acwr: AcwrPoint[];
  training_load: TrainingLoadPoint[];
}

export interface SportBreakdown {
  [sport: string]: number;
}

export interface PerformancePoint {
  date: string;
  value: number;
}

export interface PerformanceAnalytics {
  vdot: PerformancePoint[];
  e1rm: PerformancePoint[];
}

export function getLoadAnalytics(athleteId: string): Promise<LoadAnalytics> {
  return request<LoadAnalytics>(`/athletes/${athleteId}/analytics/load`);
}

export function getSportBreakdown(athleteId: string): Promise<SportBreakdown> {
  return request<SportBreakdown>(`/athletes/${athleteId}/analytics/sport-breakdown`);
}

export function getPerformanceAnalytics(athleteId: string): Promise<PerformanceAnalytics> {
  return request<PerformanceAnalytics>(`/athletes/${athleteId}/analytics/performance`);
}
