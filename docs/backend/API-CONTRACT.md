# API Contract — Resilio Plus Backend

> **Source de vérité** pour la session frontend mobile du weekend.
> Généré le 2026-04-16 depuis le code source (`backend/app/routes/`, `backend/app/schemas/`).
> Toute divergence code ↔ doc = le code gagne. Ne pas éditer manuellement.

---

## Table des matières

1. [Quick Start frontend](#quick-start-frontend)
2. [Conventions](#conventions)
3. [Authentification](#authentification)
4. [Onboarding](#onboarding)
5. [Athletes](#athletes)
6. [Plans (legacy)](#plans-legacy)
7. [Coaching Workflow (LangGraph)](#coaching-workflow-langgraph)
8. [Weekly Review](#weekly-review)
9. [Sessions & Historique](#sessions--historique)
10. [Check-in / Énergie](#check-in--énergie)
11. [Mode](#mode)
12. [Nutrition](#nutrition)
13. [Recovery](#recovery)
14. [Strain musculaire](#strain-musculaire)
15. [Analytics](#analytics)
16. [Connecteurs](#connecteurs)
17. [Intégration Strava](#intégration-strava)
18. [Plan externe (tracking mode)](#plan-externe-tracking-mode)
19. [Recherche alimentaire](#recherche-alimentaire)
20. [Admin](#admin)
21. [Health probes](#health-probes)
22. [Codes d'erreur de référence](#codes-derreur-de-référence)

---

## Quick Start frontend

### Auth flow complet

```
1. POST /athletes/onboarding        → { access_token, refresh_token, athlete_id, athlete, plan }
                    OU
   POST /auth/login                 → { access_token, refresh_token, athlete_id }

2. Stocker access_token (mémoire) + refresh_token (SecureStore)

3. Chaque requête protégée :
   Authorization: Bearer <access_token>

4. Access token expiré (HTTP 401) :
   POST /auth/refresh  { refresh_token }  →  nouveau { access_token, refresh_token }
   Rotation : l'ancien refresh_token est révoqué immédiatement.

5. Logout :
   POST /auth/logout  { refresh_token }
```

### Premier appel — données reçues

```typescript
// Après login
const { access_token, refresh_token, athlete_id } = await login(email, password);

// Charger le tableau de bord
const [status, today, readiness] = await Promise.all([
  GET(`/athletes/${athlete_id}/workflow/status`),   // phase, ACWR, has_plan
  GET(`/athletes/${athlete_id}/today`),              // séances du jour
  GET(`/athletes/${athlete_id}/readiness`),          // feux tricolores
]);
```

---

## Conventions

| Paramètre | Format |
|-----------|--------|
| `athlete_id` | UUID v4 string (ex: `"3fa85f64-5717-4562-b3fc-2c963f66afa6"`) |
| `session_id` | UUID string (fourni dans `WorkoutSlot.id`) |
| `thread_id` | Opaque string LangGraph (ex: `"thr_abc123"`) |
| Dates | ISO 8601 : `"2026-04-16"` |
| Datetimes | ISO 8601 avec timezone : `"2026-04-16T08:30:00+00:00"` |
| Durées | Secondes (int) ou minutes (int) selon le champ — voir schéma |
| IDs food | String préfixé : `"usda_789"`, `"off_3017620422003"`, `"fcen_456"` |

**Base URL** : `http://localhost:8000` en dev · configurable via `BACKEND_URL` env.

**Versioning** : pas de préfixe `/v1/` — tous les endpoints sont à la racine.

**Auth** : JWT HS256, `Authorization: Bearer <token>`.
- Access token : TTL 15 min (env `JWT_ACCESS_TTL_MINUTES`, défaut 15)
- Refresh token : TTL 30 jours (env `JWT_REFRESH_TTL_DAYS`, défaut 30), rotation à chaque usage

---

## Authentification

### `POST /auth/login`

Échange email/password contre tokens.

**Auth requise** : Non

**Request**
```typescript
interface LoginRequest {
  email: string;
  password: string;
}
```

**Response 200**
```typescript
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  athlete_id: string;  // UUID string
}
```

**Erreurs**
| Code | Detail |
|------|--------|
| 401 | `"Invalid credentials"` |
| 403 | `"Account disabled"` |

**curl**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"simon@example.com","password":"secret123"}'
```

---

### `POST /auth/refresh`

Rotation du refresh token — invalide l'ancien.

**Auth requise** : Non

**Request**
```typescript
interface RefreshRequest {
  refresh_token: string;
}
```

**Response 200** : `TokenResponse` (voir ci-dessus)

**Erreurs**
| Code | Detail |
|------|--------|
| 401 | `"Invalid or expired refresh token"` |

---

### `POST /auth/logout`

Révoque le refresh token. L'access token expire naturellement.

**Auth requise** : Oui

**Request**
```typescript
interface LogoutRequest {
  refresh_token: string;
}
```

**Response 200**
```json
{ "message": "Logged out" }
```

---

### `GET /auth/me`

Profil utilisateur courant.

**Auth requise** : Oui

**Response 200**
```typescript
interface MeResponse {
  athlete_id: string;
  email: string;
  created_at: string;   // datetime ISO
  is_active: boolean;
}
```

**Erreurs** : 404 si utilisateur introuvable.

---

### `POST /auth/forgot-password`

Envoie un email de réinitialisation. Réponse identique si email inconnu (anti-enumération).

**Auth requise** : Non

**Request** : `{ email: string }`

**Response 200** : `{ "message": "If this email is registered, a reset link has been sent." }`

---

### `POST /auth/reset-password`

Applique le nouveau mot de passe. Révoque tous les refresh tokens actifs.

**Auth requise** : Non

**Request**
```typescript
interface ResetPasswordRequest {
  token: string;       // token reçu par email
  new_password: string; // min_length: 8
}
```

**Response 200** : `{ "message": "Password updated successfully. Please log in again." }`

**Erreurs**
| Code | Detail |
|------|--------|
| 400 | `"Invalid or expired reset token"` |

---

## Onboarding

### `POST /athletes/onboarding`

Crée athlete + user + plan initial en une seule transaction. Retourne tokens immédiatement — pas besoin de login séparé.

**Auth requise** : Non

**Request** : `OnboardingRequest` — extends `AthleteCreate` avec champs supplémentaires :

```typescript
interface OnboardingRequest extends AthleteCreate {
  email: string;
  password: string;      // min_length: 8
  plan_start_date: string; // date ISO
}

interface AthleteCreate {
  name: string;
  age: number;           // ge: 14, le: 100
  sex: "M" | "F" | "other";
  weight_kg: number;     // gt: 0
  height_cm: number;     // gt: 0
  sports: Sport[];
  primary_sport: Sport;
  goals: string[];
  target_race_date?: string | null;  // date ISO
  available_days: number[];          // 0=Lun … 6=Dim
  hours_per_week: number;            // gt: 0
  equipment?: string[];
  max_hr?: number | null;
  resting_hr?: number | null;
  ftp_watts?: number | null;
  vdot?: number | null;
  css_per_100m?: number | null;
  sleep_hours_typical?: number;      // défaut: 7.0
  stress_level?: number;             // ge: 1, le: 10, défaut: 5
  job_physical?: boolean;            // défaut: false
  coaching_mode?: "full" | "tracking_only"; // défaut: "full"
}

type Sport = "running" | "lifting" | "swimming" | "biking";
```

**Response 201**
```typescript
interface OnboardingResponse {
  athlete: AthleteResponse;
  plan: TrainingPlanResponse;
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}
```

**Erreurs**
| Code | Detail |
|------|--------|
| 409 | `"Email already registered"` |

**TypeScript**
```typescript
const res = await fetch('/athletes/onboarding', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Simon', age: 34, sex: 'M',
    weight_kg: 78, height_cm: 180,
    sports: ['running', 'lifting'], primary_sport: 'running',
    goals: ['Marathon sub-3h'],
    available_days: [1, 2, 3, 4, 6],
    hours_per_week: 8,
    email: 'simon@example.com', password: 'secret123',
    plan_start_date: '2026-04-21',
  }),
});
const { athlete, plan, access_token, refresh_token } = await res.json();
```

---

## Athletes

### `GET /athletes/`

Liste tous les athletes (admin — protégé par `get_current_athlete_id`).

**Auth requise** : Oui

**Response 200** : `AthleteResponse[]`

---

### `POST /athletes/`

Crée un athlete sans user (pré-onboarding uniquement — préférer `/athletes/onboarding`).

**Auth requise** : Non

**Request** : `AthleteCreate` (voir Onboarding)

**Response 201** : `AthleteResponse`

---

### `GET /athletes/{athlete_id}`

Récupère le profil d'un athlete. Accès restreint au propriétaire.

**Auth requise** : Oui (propriétaire uniquement)

**Response 200**
```typescript
interface AthleteResponse {
  id: string;            // UUID
  name: string;
  age: number;
  sex: "M" | "F" | "other";
  weight_kg: number;
  height_cm: number;
  sports: Sport[];
  primary_sport: Sport;
  goals: string[];
  target_race_date: string | null;
  available_days: number[];
  hours_per_week: number;
  equipment: string[];
  max_hr: number | null;
  resting_hr: number | null;
  ftp_watts: number | null;
  vdot: number | null;
  css_per_100m: number | null;
  sleep_hours_typical: number;
  stress_level: number;
  job_physical: boolean;
  coaching_mode: "full" | "tracking_only";
}
```

**Erreurs** : 403 (accès refusé), 404 (introuvable)

---

### `PUT /athletes/{athlete_id}`

Mise à jour complète ou partielle du profil (tous les champs optionnels).

**Auth requise** : Oui (propriétaire)

**Request** : `AthleteUpdate` — tous les champs de `AthleteCreate` rendus optionnels (`null` = inchangé)

**Response 200** : `AthleteResponse`

**curl**
```bash
curl -X PUT http://localhost:8000/athletes/${ATHLETE_ID} \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"vdot": 52.5, "ftp_watts": 280}'
```

---

### `DELETE /athletes/{athlete_id}`

Suppression complète (cascade sur plans, sessions, reviews, etc.).

**Auth requise** : Oui (propriétaire)

**Response** : 204 No Content

---

## Plans (legacy)

> Ces endpoints créent des plans via la logique directe (sans LangGraph). Pour les nouveaux flows, utiliser le **Coaching Workflow** ci-dessous.

### `POST /athletes/{athlete_id}/plan`

Génère un plan d'entraînement.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface PlanRequest {
  start_date: string;  // date ISO
  end_date: string;    // date ISO
}
```

**Response 201** : `TrainingPlanResponse`

```typescript
interface TrainingPlanResponse {
  id: string;
  athlete_id: string;
  start_date: string;      // date ISO
  end_date: string;
  phase: string;           // "base" | "build" | "peak" | "taper" | "recovery"
  total_weekly_hours: number;
  acwr: number;            // ACWR courant — safe: 0.8–1.3
  status: string;          // "active"
  sessions: WorkoutSlot[];
}

interface WorkoutSlot {
  id: string;              // UUID — utiliser comme session_id
  date: string;
  sport: Sport;
  workout_type: string;
  duration_min: number;    // gt: 0
  fatigue_score: FatigueScore;
  notes: string;
}

interface FatigueScore {
  local_muscular: number;  // 0–100
  cns_load: number;        // 0–100
  metabolic_cost: number;  // 0–100
  recovery_hours: number;  // ge: 0
  affected_muscles: string[];
}
```

---

### `GET /athletes/{athlete_id}/plans`

Tous les plans de l'athlete.

**Auth requise** : Oui (propriétaire)

**Response 200** : `TrainingPlanResponse[]`

---

### `GET /athletes/{athlete_id}/plan`

Plan actif le plus récent.

**Auth requise** : Oui (propriétaire)

**Response 200** : `TrainingPlanResponse`

---

## Coaching Workflow (LangGraph)

Flow principal de coaching — utilise LangGraph avec checkpoints. La création de plan est asynchrone (interrupt/resume).

### `GET /athletes/{athlete_id}/workflow/status`

État courant du workflow — point d'entrée du dashboard.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface WorkflowStatus {
  athlete_id: string;
  phase: "onboarding" | "no_plan" | "active" | "weekly_review_due";
  has_plan: boolean;
  plan_id: string | null;
  plan_start_date: string | null;   // date ISO
  plan_end_date: string | null;
  weeks_completed: number;
  sessions_logged_this_week: number;
  weekly_review_due: boolean;
  acwr: number | null;
  readiness: "green" | "yellow" | "red" | null;
}
```

---

### `POST /athletes/{athlete_id}/workflow/create-plan`

Lance la génération du plan via LangGraph. Retourne un `thread_id` pour l'approbation.

**Auth requise** : Oui + `coaching_mode: "full"` obligatoire

**Request**
```typescript
interface PlanCreateRequest {
  start_date: string;   // date ISO
  weeks?: number;       // défaut: 8
}
```

**Response 200**
```typescript
interface PlanCreateResponse {
  success: boolean;
  plan_id: string | null;
  phase: string | null;
  weeks: number | null;
  sessions_total: number | null;
  message: string;
  thread_id: string | null;       // à utiliser pour approve/revise
  requires_approval: boolean;
}
```

---

### `POST /athletes/{athlete_id}/workflow/plans/{thread_id}/approve`

Approuve le plan proposé — le matérialise en base.

**Auth requise** : Oui + `coaching_mode: "full"`

**Response 200**
```typescript
interface PlanApproveResponse {
  success: boolean;
  plan_id: string | null;
  message: string;
}
```

---

### `POST /athletes/{athlete_id}/workflow/plans/{thread_id}/revise`

Demande une révision avec feedback texte libre.

**Auth requise** : Oui + `coaching_mode: "full"`

**Request**
```typescript
interface PlanReviseRequest {
  feedback: string;
  weeks?: number | null;
}
```

**Response 200** : `PlanCreateResponse` avec nouveau `thread_id`

---

### `POST /athletes/{athlete_id}/workflow/weekly-sync`

Synchronisation hebdomadaire — met à jour ACWR, charge, recommandations.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface WeeklySyncResponse {
  success: boolean;
  week_number: number;
  sessions_completed: number;
  sessions_planned: number;
  completion_rate: number;
  acwr: number | null;
  readiness: "green" | "yellow" | "red" | null;
  recommendations: string[];
  next_week_adjusted: boolean;
}
```

---

### `POST /athletes/{athlete_id}/plan/review/start`

Démarre une review hebdomadaire (LangGraph thread).

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface ReviewStartResponse {
  thread_id: string;
  review_summary: Record<string, unknown> | null;
  message: string;
}
```

---

### `POST /athletes/{athlete_id}/plan/review/confirm`

Confirme ou rejette la review.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface ReviewConfirmRequest {
  thread_id: string;
  approved?: boolean;  // défaut: true
}
```

**Response 200**
```typescript
interface ReviewConfirmResponse {
  success: boolean;
  review_id: string | null;
  message: string;
}
```

---

### `GET /athletes/{athlete_id}/coach/session/{thread_id}/state`

État brut du checkpoint LangGraph — debug uniquement.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface SessionStateResponse {
  thread_id: string;
  state: Record<string, unknown> | null;
  checkpoint_ts: string | null;
}
```

---

## Weekly Review

### `GET /athletes/{athlete_id}/week-status`

État de la semaine courante.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface WeekStatusResponse {
  week_number: number;
  plan: TrainingPlanResponse;
  planned_hours: number;
  actual_hours: number;
  completion_pct: number;
  acwr: number | null;
}
```

---

### `POST /athletes/{athlete_id}/review`

Soumet la review hebdomadaire.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface WeeklyReviewRequest {
  week_end_date: string;         // date ISO (string)
  readiness_score?: number | null;  // ge: 1.0, le: 10.0
  hrv_rmssd?: number | null;
  sleep_hours_avg?: number | null;
  comment?: string;
}
```

**Response 201**
```typescript
interface WeeklyReviewResponse {
  review_id: string;
  week_number: number;
  planned_hours: number;
  actual_hours: number;
  acwr: number;
  adjustment_applied: number;
  next_week_suggestion: string;
}
```

---

## Sessions & Historique

### `GET /athletes/{athlete_id}/today`

Séances prévues aujourd'hui.

**Auth requise** : Oui (propriétaire)

**Query params** : `target_date?: string` (date ISO — override date courante)

**Response 200**
```typescript
interface TodayResponse {
  date: string;
  is_rest_day: boolean;
  plan_id: string | null;
  sessions: SessionDetailResponse[];
}

interface SessionDetailResponse {
  session_id: string;
  plan_id: string;
  date: string;
  sport: Sport;
  workout_type: string;
  duration_min: number;
  fatigue_score: FatigueScore;
  notes: string;
  log: SessionLogResponse | null;  // null si séance non encore loguée
}
```

---

### `GET /athletes/{athlete_id}/sessions/{session_id}`

Détail d'une séance.

**Auth requise** : Oui (propriétaire)

**Response 200** : `SessionDetailResponse`

---

### `POST /athletes/{athlete_id}/sessions/{session_id}/log`

Logger une séance planifiée.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface SessionLogRequest {
  actual_duration_min?: number | null;  // ge: 1
  skipped?: boolean;                    // défaut: false
  rpe?: number | null;                  // ge: 1, le: 10
  notes?: string;
  actual_data?: Record<string, unknown>;
}
```

**Response 201**
```typescript
interface SessionLogResponse {
  id: string;
  session_id: string;
  actual_duration_min: number | null;
  skipped: boolean;
  rpe: number | null;
  notes: string;
  actual_data: Record<string, unknown>;
  logged_at: string;  // datetime ISO
}
```

---

### `GET /athletes/{athlete_id}/sessions/{session_id}/log`

Récupère le log existant.

**Auth requise** : Oui (propriétaire)

**Response 200** : `SessionLogResponse`

---

### `POST /athletes/{athlete_id}/workouts`

Log manuel d'un entraînement hors plan.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface ManualWorkoutRequest {
  sport: Sport;
  workout_type: string;
  date: string;
  actual_duration_min: number;  // ge: 1, le: 600
  rpe?: number | null;          // ge: 1, le: 10
  notes?: string;
  actual_data?: Record<string, unknown>;
}
```

**Response 201**
```typescript
interface ManualWorkoutResponse {
  id: string;
  session_id: string;
  sport: Sport;
  workout_type: string;
  date: string;
  actual_duration_min: number;
  rpe: number | null;
  notes: string;
  actual_data: Record<string, unknown>;
  logged_at: string;
}
```

---

### `GET /athletes/{athlete_id}/history`

Historique des semaines passées.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface WeekSummary {
  plan_id: string;
  week_number: number;
  start_date: string;
  end_date: string;
  phase: string;
  planned_hours: number;
  sessions_total: number;
  sessions_logged: number;
  completion_pct: number;
}
```

**TypeScript complet**
```typescript
const history: WeekSummary[] = await apiFetch(`/athletes/${athleteId}/history`);
history.forEach(w => console.log(`Semaine ${w.week_number}: ${w.completion_pct}%`));
```

---

## Check-in / Énergie

### `POST /athletes/{athlete_id}/checkin`

Check-in quotidien — déclenche le calcul de readiness + allostatic score.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface CheckInInput {
  work_intensity: "light" | "normal" | "heavy" | "exhausting";
  stress_level: "none" | "mild" | "significant";
  legs_feeling: "fresh" | "normal" | "heavy" | "dead";
  energy_global: "great" | "ok" | "low" | "exhausted";
  cycle_phase?: "menstrual" | "follicular" | "ovulation" | "luteal" | null;
  comment?: string | null;  // max_length: 140
}
```

**Response 201**
```typescript
interface ReadinessResponse {
  date: string;
  objective_score: number;     // 0–100 (HRV, sleep, ACWR)
  subjective_score: number;    // 0–100 (check-in)
  final_readiness: number;     // 0–100 (composite)
  divergence: number;          // |objectif − subjectif|
  divergence_flag: "none" | "moderate" | "high";
  traffic_light: "green" | "yellow" | "red";
  allostatic_score: number;    // 0–100
  energy_availability: number; // kcal/kg FFM
  intensity_cap: number;       // 0.0–1.0 (cap applicable aux séances)
  insights: string[];          // messages coach générés
}
```

---

### `GET /athletes/{athlete_id}/readiness`

Dernier ReadinessResponse (sans check-in).

**Auth requise** : Oui (propriétaire)

**Response 200** : `ReadinessResponse`

---

### `GET /athletes/{athlete_id}/energy/history`

Historique des snapshots énergétiques.

**Auth requise** : Oui (propriétaire)

**Query params** : `days?: number` (ge: 1, le: 90, défaut: 28)

**Response 200**
```typescript
interface EnergySnapshotSummary {
  date: string;
  objective_score: number | null;
  subjective_score: number | null;
  allostatic_score: number;
  energy_availability: number;
  intensity_cap: number;
  veto_triggered: boolean;
  traffic_light: string;
}
```

---

### `PATCH /athletes/{athlete_id}/hormonal-profile`

Met à jour le profil hormonal (suivi du cycle menstruel).

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface HormonalProfileUpdate {
  enabled: boolean;
  cycle_length_days?: number;   // ge: 21, le: 45, défaut: 28
  last_period_start?: string | null;  // date ISO
  tracking_source?: "manual" | "apple_health";  // défaut: "manual"
  notes?: string | null;
}
```

**Response 200**
```typescript
interface HormonalProfileResponse {
  athlete_id: string;
  enabled: boolean;
  cycle_length_days: number;
  last_period_start: string | null;
  tracking_source: string;
  notes: string | null;
}
```

---

## Mode

### `PATCH /athletes/{athlete_id}/mode`

Bascule entre coaching complet (LangGraph) et tracking uniquement.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface ModeSwitchRequest {
  coaching_mode: "full" | "tracking_only";
}
```

**Response 200**
```typescript
interface ModeSwitchResponse {
  athlete_id: string;
  coaching_mode: string;
  message: string;
}
```

---

## Nutrition

### `GET /athletes/{athlete_id}/nutrition-directives`

Directives nutritionnelles complètes par type de journée.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
type DayType = "rest" | "strength" | "endurance_short" | "endurance_long" | "race";

interface MacroTarget {
  carbs_g_per_kg: number;    // ge: 0
  protein_g_per_kg: number;  // ge: 0
  fat_g_per_kg: number;      // ge: 0
  calories_total: number;    // gt: 0, entier
}

interface DayNutrition {
  day_type: DayType;
  macro_target: MacroTarget;
  intra_effort_carbs_g_per_h: number | null;   // ge: 0
  sodium_mg_per_h: number | null;              // ge: 0
}

interface NutritionPlan {
  id: string;          // UUID
  athlete_id: string;
  weight_kg: number;
  targets_by_day_type: Record<DayType, DayNutrition>;
}
```

---

### `GET /athletes/{athlete_id}/nutrition-today`

Directives pour aujourd'hui (ou date passée en query param).

**Auth requise** : Oui (propriétaire)

**Query params** : `target_date?: string` (date ISO)

**Response 200**
```typescript
interface NutritionTodayResponse {
  date: string;
  day_type: DayType;
  macro_target: MacroTarget;
  intra_effort_carbs_g_per_h: number | null;
  sodium_mg_per_h: number | null;
}
```

---

## Recovery

### `GET /athletes/{athlete_id}/recovery-status`

Statut de récupération courant (HRV, sommeil, banking).

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface RecoveryStatusResponse {
  readiness_modifier: number;       // multiplicateur (-1.0 → +1.0)
  hrv_trend: string;                // "improving" | "stable" | "declining"
  sleep_avg_hours: number | null;
  sleep_banking_active: boolean;
  recommendation: string;           // texte libre du Recovery Coach
}
```

---

## Strain musculaire

### `GET /athletes/{athlete_id}/strain`

Index de fatigue par groupe musculaire (calculé via EWMA).

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface MuscleStrainResponse {
  computed_at: string;              // date ISO
  scores: Record<string, number>;  // groupe → 0–100
  peak_group: string;               // groupe le plus chargé
  peak_score: number;
}
```

**Groupes musculaires** : `quads`, `posterior_chain`, `glutes`, `calves`, `chest`, `upper_pull`, `shoulders`, `triceps`, `biceps`, `core`

**Seuils radar chart** : 0–69 → vert · 70–84 → orange · 85–100 → rouge

---

## Analytics

### `GET /athletes/{athlete_id}/analytics/load`

Charge d'entraînement et ACWR.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
interface LoadAnalytics {
  acwr: number | null;
  training_load: Record<string, unknown>;
}
```

---

### `GET /athletes/{athlete_id}/analytics/sport-breakdown`

Répartition des séances par sport.

**Auth requise** : Oui (propriétaire)

**Response 200** : `Record<string, number>` — ex: `{ "running": 12, "lifting": 8 }`

---

### `GET /athletes/{athlete_id}/analytics/performance`

Métriques de performance agrégées.

**Auth requise** : Oui (propriétaire)

**Response 200** : `Record<string, unknown>` (structure variable selon les connecteurs actifs)

---

## Connecteurs

### `POST /athletes/{athlete_id}/connectors/hevy`

Connecte le compte Hevy (API key).

**Auth requise** : Non (vérifie seulement que l'athlete existe)

**Request**
```typescript
interface HevyConnectRequest {
  api_key: string;  // min_length: 1
}
```

**Response 201**
```typescript
interface ConnectorStatus {
  provider: string;           // "strava" | "hevy" | "terra"
  connected: boolean;
  expires_at: number | null;  // epoch Unix (null pour providers à API key)
  last_sync: string | null;   // datetime ISO de la dernière sync réussie
}
```

---

### `POST /athletes/{athlete_id}/connectors/terra`

Connecte Terra (HRV, sommeil).

**Auth requise** : Oui (propriétaire)

**Request** : `{ terra_user_id: string }`

**Response 201** : `ConnectorStatus`

---

### `POST /athletes/{athlete_id}/connectors/apple-health/upload`

Upload d'un snapshot Apple Health.

**Auth requise** : Oui (propriétaire)

**Request**
```typescript
interface AppleHealthUploadRequest {
  snapshot_date: string;        // date ISO (string)
  hrv_rmssd?: number | null;
  sleep_hours?: number | null;
  hr_rest?: number | null;
}
```

**Response 200** : `{ uploaded: boolean, snapshot_date: string, hrv_rmssd: number | null, sleep_hours: number | null }`

---

### `GET /athletes/{athlete_id}/connectors`

Liste les connecteurs actifs.

**Auth requise** : Non (vérifie que l'athlete existe)

**Response 200**
```typescript
interface ConnectorListResponse {
  connectors: ConnectorStatus[];
}
```

---

### `POST /athletes/{athlete_id}/connectors/hevy/sync`

Déclenche une sync manuelle Hevy.

**Auth requise** : Oui (propriétaire)

**Response 200** : `{ message: string, synced: number }`

---

### `POST /athletes/{athlete_id}/connectors/terra/sync`

Déclenche une sync manuelle Terra.

**Auth requise** : Oui (propriétaire)

**Response 200** : `{ message: string }`

---

### `POST /athletes/{athlete_id}/connectors/sync`

Sync tous les connecteurs actifs.

**Auth requise** : Oui (propriétaire)

**Response 200**
```typescript
type ProviderStatus = "ok" | "skipped" | "error";

interface SyncAllResponse {
  synced_at: string;   // datetime ISO
  results: Record<string, ProviderStatus>;
  errors: Record<string, string>;
}
```

---

### `DELETE /athletes/{athlete_id}/connectors/{provider}`

Déconnecte un connecteur.

**Auth requise** : Non (vérifie que l'athlete existe)

**Path param** : `provider: "strava" | "hevy" | "terra"`

**Response** : 204 No Content

---

### `POST /athletes/{athlete_id}/connectors/files/gpx`

Import d'un fichier GPX.

**Auth requise** : Oui (propriétaire)

**Request** : multipart/form-data avec champ `file`

**Response 200** : `{ message: string, activity_id: string }`

---

### `POST /athletes/{athlete_id}/connectors/files/fit`

Import d'un fichier FIT (Garmin/Wahoo).

**Auth requise** : Oui (propriétaire)

**Request** : multipart/form-data avec champ `file`

**Response 200** : `{ message: string }`

---

## Intégration Strava

### `POST /integrations/strava/connect`

Initie le flow OAuth2 Strava — retourne l'URL d'autorisation.

**Auth requise** : Oui

**Response 200** : `{ auth_url: string }`

---

### `GET /integrations/strava/callback`

Callback OAuth2 (Strava redirige ici). Enregistre les tokens chiffrés (Fernet).

**Auth requise** : Non

**Query params** : `code: string`, `state: string`

**Response 200** : `{ message: string, athlete_id: string }`

**Erreurs** : 400 (code invalide), 502 (erreur Strava)

---

### `POST /integrations/strava/sync`

Sync incrémentale des activités Strava depuis `last_sync_at`.

**Auth requise** : Oui

**Response 200**
```typescript
interface SyncSummary {
  synced: number;
  skipped: number;                     // sport_type non reconnu
  sport_breakdown: Record<string, number>; // ex: { "running": 3, "biking": 1 }
}
```

**Erreurs** : 404 (athlete inconnu), 429 (rate limit Strava avec header `Retry-After`)

---

### `POST /integrations/hevy/import`

Import CSV Hevy (export direct depuis l'app Hevy).

**Auth requise** : Oui

**Request** : multipart/form-data avec `file` (CSV) + query param `unit: "kg" | "lbs"` (défaut: `"kg"`)

**Response 200** : `{ imported: number, skipped: number, errors: string[] }`

**Erreurs** : 422 (CSV malformé)

---

## Plan externe (tracking mode)

> Disponible uniquement si `coaching_mode: "tracking_only"`.

### `POST /athletes/{athlete_id}/external-plan`

Crée un plan externe.

**Auth requise** : Oui (tracking mode)

**Request**
```typescript
interface ExternalPlanCreate {
  title: string;
  start_date?: string | null;
  end_date?: string | null;
}
```

**Response 201**
```typescript
interface ExternalPlanOut {
  id: string;
  athlete_id: string;
  title: string;
  source: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;   // datetime ISO
  sessions: ExternalSessionOut[];
}
```

---

### `GET /athletes/{athlete_id}/external-plan`

Plan externe actif.

**Auth requise** : Oui (tracking mode)

**Response 200** : `ExternalPlanOut`

---

### `POST /athletes/{athlete_id}/external-plan/sessions`

Ajoute une séance au plan externe.

**Auth requise** : Oui (tracking mode)

**Request**
```typescript
interface ExternalSessionCreate {
  session_date: string;   // date ISO
  sport: string;
  title: string;
  description?: string | null;
  duration_min?: number | null;
}
```

**Response 201**
```typescript
interface ExternalSessionOut {
  id: string;
  plan_id: string;
  athlete_id: string;
  session_date: string;
  sport: string;
  title: string;
  description: string | null;
  duration_min: number | null;
  status: string;   // "planned" | "completed" | "skipped"
}
```

---

### `PATCH /athletes/{athlete_id}/external-plan/sessions/{session_id}`

Met à jour une séance externe.

**Auth requise** : Oui (tracking mode)

**Request**
```typescript
interface ExternalSessionUpdate {
  session_date?: string | null;
  sport?: string | null;
  title?: string | null;
  description?: string | null;
  duration_min?: number | null;
  status?: "planned" | "completed" | "skipped" | null;
}
```

**Response 200** : `ExternalSessionOut`

---

### `DELETE /athletes/{athlete_id}/external-plan/sessions/{session_id}`

Supprime une séance externe.

**Response** : 204 No Content

---

### `POST /athletes/{athlete_id}/external-plan/import`

Importe un plan depuis un fichier texte/PDF (parsé par Claude Haiku). Retourne un draft à confirmer.

**Auth requise** : Oui (tracking mode)

**Request** : multipart/form-data avec `file`

**Response 200**
```typescript
interface ExternalPlanDraft {
  title: string;
  sessions_parsed: number;
  sessions: ExternalPlanDraftSession[];
  parse_warnings: string[];
}

interface ExternalPlanDraftSession {
  session_date: string | null;
  sport: string;
  title: string;
  description: string | null;
  duration_min: number | null;
}
```

---

### `POST /athletes/{athlete_id}/external-plan/import/confirm`

Confirme et enregistre le draft importé.

**Auth requise** : Oui (tracking mode)

**Request** : `ExternalPlanDraft` (retourné par `/import`)

**Response 201** : `ExternalPlanOut`

---

## Recherche alimentaire

### `GET /nutrition/search`

Recherche dans les bases USDA FDC, Open Food Facts et FCÉN.

**Auth requise** : Oui

**Query params** :
- `q: string` (min_length: 1, obligatoire)
- `limit?: number` (ge: 1, le: 50, défaut: 20)

**Response 200**
```typescript
interface FoodItem {
  id: string;                 // "usda_789" | "off_xxx" | "fcen_456"
  source: string;             // "usda" | "off" | "fcen"
  name: string;               // nom affiché (français si disponible)
  name_en: string;
  name_fr: string | null;
  calories_per_100g: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
  sodium_mg: number | null;
  sugar_g: number | null;
}
```

**curl**
```bash
curl "http://localhost:8000/nutrition/search?q=poulet&limit=5" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

### `GET /nutrition/food/{food_id}`

Détail d'un aliment par ID.

**Auth requise** : Oui

**Path param** : `food_id: string` (ex: `"usda_167812"`)

**Response 200** : `FoodItem`

**Erreurs** : 404 si introuvable

---

## Admin

> Accès restreint : `athlete_id` doit correspondre à `ADMIN_ATHLETE_ID` (variable d'environnement).

### `GET /admin/jobs`

État des jobs background (APScheduler).

**Auth requise** : Oui + admin

**Response 200**
```json
{
  "jobs": [...],
  "summary": {
    "total_jobs": 5,
    "errors_24h": 0,
    "next_run": "2026-04-17T04:00:00Z"
  }
}
```

**Erreurs** : 403 si non-admin

---

### `GET /admin/metrics`

Métriques HTTP/agent/job in-memory depuis le dernier démarrage.

**Auth requise** : Oui + admin

**Response 200** : snapshot `Metrics` (voir `docs/backend/OBSERVABILITY.md`)

---

## Health probes

### `GET /health`

Liveness — toujours 200 si le process est vivant.

**Auth requise** : Non

**Response 200** : `{ "status": "ok" }`

---

### `GET /ready`

Readiness — vérifie la connexion DB (SELECT 1).

**Auth requise** : Non

**Response 200** : `{ "status": "ready", "db": "ok" }`

**Response 503** : `{ "status": "degraded", "db": "<message d'erreur>" }`

---

### `GET /ready/deep`

Deep readiness — vérifie DB + connectivité Anthropic API (httpx).

**Auth requise** : Non

**Response 200** : `{ "status": "ready", "db": "ok", "anthropic": "ok" }`

**Response 503** : `{ "status": "degraded", "db": "...", "anthropic": "..." }`

---

## Codes d'erreur de référence

| Code | Signification | Actions frontend |
|------|--------------|-----------------|
| 200 | OK | — |
| 201 | Created | Rafraîchir la liste |
| 204 | No Content | Supprimer de l'UI |
| 400 | Bad Request | Afficher `detail` à l'utilisateur |
| 401 | Unauthorized | Tenter refresh → si échec, redirecter login |
| 403 | Forbidden | Afficher erreur ou redirecter |
| 404 | Not Found | Afficher état vide |
| 409 | Conflict | Email déjà utilisé (onboarding) |
| 422 | Unprocessable Entity | Erreur de validation — lire `detail[].msg` |
| 429 | Rate Limited | Lire header `Retry-After`, attendre |
| 500 | Internal Server Error | Log côté client, afficher message générique |
| 502 | Bad Gateway | Erreur connecteur externe (Strava) |
| 503 | Service Unavailable | Probe `/ready` dégradée — retry avec backoff |

### Format d'erreur FastAPI standard

```json
{
  "detail": "Invalid credentials"
}
```

Pour les erreurs 422 (validation) :

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

---

## Exemples TypeScript — client générique

```typescript
// lib/api.ts — client minimaliste avec refresh automatique

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAccessToken(); // depuis votre store
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) { redirectToLogin(); return; }
    return apiFetch(path, options); // retry once
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, err.detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// Usage
const status = await apiFetch<WorkflowStatus>(`/athletes/${athleteId}/workflow/status`);
const today = await apiFetch<TodayResponse>(`/athletes/${athleteId}/today`);
```
