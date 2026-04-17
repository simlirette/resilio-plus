/**
 * Mock data for the Home screen (FE-MOBILE-2).
 * Types aligned with backend schemas:
 *   - AthleteMetrics (backend/app/models/athlete_state.py:218)
 *   - ReadinessResponse (resilio-master-v3.md:285)
 *   - PlanSnapshot / WorkoutSlot (athlete_state.py)
 *
 * Replace with real API calls in Session FE-MOBILE-BACKEND-WIRING.
 */

export type MetricState = 'green' | 'yellow' | 'red';
export type AcwrStatus = 'safe' | 'caution' | 'danger';
export type AllostaticTrend = 'improving' | 'stable' | 'declining';
export type SportType = 'running' | 'lifting' | 'swimming' | 'cycling' | 'rest';

export interface WorkoutSlotStub {
  sport: SportType;
  title: string;
  duration_min: number;
  zone: string;
  is_rest_day: boolean;
}

export interface HomeData {
  /** Readiness score (0–100). Maps to AthleteMetrics.readiness_score */
  readiness: {
    value: number;
    state: MetricState;
    trend: AllostaticTrend;
    /** Objective (HRV+ACWR+sleep) vs subjective (check-in) blend */
    objective_score: number;
    subjective_score: number | null;
  };
  /** Nutrition adherence (0–100). Not in backend yet — will be NutritionCoach output */
  nutrition: {
    value: number;
    state: MetricState;
  };
  /** Muscle strain index (0–100). Maps to max(MuscleStrainScore axes) */
  strain: {
    value: number;
    state: MetricState;
  };
  /** Sleep quality (0–100). Derived: min(100, sleep_hours / 8 * 100) until Terra score available */
  sleep: {
    value: number;
    state: MetricState;
    sleep_hours: number | null;
  };
  /** Cognitive / allostatic load (0–100). Maps to AllostaticSummary.avg_score_7d */
  cognitiveLoad: {
    value: number;
    state: MetricState;
  };
  /** ACWR status from AthleteMetrics.acwr_status */
  acwrStatus: AcwrStatus;
  /** Today's planned sessions. null = rest day. Maps to PlanSnapshot.today */
  todaysSessions: WorkoutSlotStub[] | null;
}

// ─── Scenario A: Green day — good readiness ──────────────────────────────────
export const mockHomeDataGreen: HomeData = {
  readiness: {
    value: 82,
    state: 'green',
    trend: 'improving',
    objective_score: 85,
    subjective_score: 78,
  },
  nutrition: {
    value: 74,
    state: 'yellow',
  },
  strain: {
    value: 38,
    state: 'green',
  },
  sleep: {
    value: 88,
    state: 'green',
    sleep_hours: 7.5,
  },
  cognitiveLoad: {
    value: 28,
    state: 'green',
  },
  acwrStatus: 'safe',
  todaysSessions: [
    {
      sport: 'running',
      title: 'Easy Run Z1',
      duration_min: 45,
      zone: 'Zone 1 (60–74% FCmax)',
      is_rest_day: false,
    },
  ],
};

// ─── Scenario B: Yellow day — moderate readiness ─────────────────────────────
export const mockHomeDataYellow: HomeData = {
  readiness: {
    value: 61,
    state: 'yellow',
    trend: 'stable',
    objective_score: 58,
    subjective_score: 65,
  },
  nutrition: {
    value: 52,
    state: 'yellow',
  },
  strain: {
    value: 67,
    state: 'yellow',
  },
  sleep: {
    value: 69,
    state: 'yellow',
    sleep_hours: 6.0,
  },
  cognitiveLoad: {
    value: 55,
    state: 'yellow',
  },
  acwrStatus: 'caution',
  todaysSessions: [
    {
      sport: 'lifting',
      title: 'Muscu — Upper Pull',
      duration_min: 50,
      zone: 'MEV — volume modéré',
      is_rest_day: false,
    },
  ],
};

// ─── Scenario C: Rest day ─────────────────────────────────────────────────────
export const mockHomeDataRestDay: HomeData = {
  readiness: {
    value: 72,
    state: 'green',
    trend: 'stable',
    objective_score: 70,
    subjective_score: null,
  },
  nutrition: {
    value: 80,
    state: 'green',
  },
  strain: {
    value: 85,
    state: 'red',
  },
  sleep: {
    value: 76,
    state: 'green',
    sleep_hours: 7.0,
  },
  cognitiveLoad: {
    value: 72,
    state: 'yellow',
  },
  acwrStatus: 'safe',
  todaysSessions: null, // rest day
};

// ─── Default export — used by FE-MOBILE-2 Home screen ────────────────────────
export const mockHomeData: HomeData = mockHomeDataGreen;
