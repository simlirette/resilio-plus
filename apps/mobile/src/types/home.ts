export type MetricState = 'green' | 'yellow' | 'red' | 'unknown';
export type MetricStatus = 'measured' | 'estimated' | 'unavailable';
export type AcwrStatus = 'safe' | 'caution' | 'danger' | 'unknown';
export type AllostaticTrend = 'improving' | 'stable' | 'declining';
export type SportType = 'running' | 'lifting' | 'swimming' | 'cycling' | 'rest';

export interface MetricSummary {
  value: number | null;
  state: MetricState;
  status: MetricStatus;
}

export interface ReadinessSummary extends MetricSummary {
  trend: AllostaticTrend;
  objective_score: number | null;
  subjective_score: number | null;
  allostatic_score?: number | null;
}

export interface NutritionSummary extends MetricSummary {
  day_type?: string | null;
  calories_target?: number | null;
  protein_g_per_kg?: number | null;
  carbs_g_per_kg?: number | null;
  fat_g_per_kg?: number | null;
}

export interface SleepSummary extends MetricSummary {
  sleep_hours: number | null;
}

export interface WorkoutSlotStub {
  session_id?: string;
  plan_id?: string;
  sport: SportType;
  title: string;
  duration_min: number;
  zone: string;
  is_rest_day: boolean;
  logged?: boolean;
}

export interface HomeDataQuality {
  readiness: MetricStatus;
  nutrition: MetricStatus;
  strain: MetricStatus;
  sleep: MetricStatus;
  sessions: MetricStatus;
}

export interface HomeData {
  athlete_id?: string;
  date?: string;
  readiness: ReadinessSummary;
  nutrition: NutritionSummary;
  strain: MetricSummary;
  sleep: SleepSummary;
  cognitiveLoad: MetricSummary;
  acwrStatus: AcwrStatus;
  todaysSessions: WorkoutSlotStub[] | null;
  dataQuality?: HomeDataQuality;
}
