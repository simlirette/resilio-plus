# Agents Validation Report

**Date:** 2026-04-10  
**Branch:** feat/agents-integration  
**Tests:** 1623 passing (64 nouveaux)

---

## Résumé global

| Agent | Statut | Tests | Problèmes trouvés | Problèmes corrigés |
|-------|--------|-------|-------------------|--------------------|
| Running Coach | ✅ | 19 | Paces non incluses dans WorkoutSlot | ✅ Corrigé |
| Lifting Coach | ✅ | 13 | Aucun | — |
| Recovery Coach V3 | ✅ | 25 | Aucun | — |
| Energy Coach | ✅ | 26 | Aucun | — |
| Head Coach | ✅ | 9 | Aucun | — |
| Nutrition Coach | ✅ | 9 | Aucun | — |
| Swimming Coach | ✅ | (via suite existante) | Aucun | — |
| Biking Coach | ✅ | (via suite existante) | Aucun | — |

---

## 1. Running Coach

### Tests créés : `tests/e2e/test_agents_integration.py::TestRunningCoachSimonE2E`

**Profil de test :** Simon — VDOT 45, 78.5 kg, 8h/semaine, sport primaire running, phase build (27 semaines restantes)

### Résultats

| Test | Statut | Valeurs générées |
|------|--------|-----------------|
| VDOT 45 lu depuis profil | ✅ | Notes: "VDOT 45 \| Phase: specific_prep \| Week: 2" |
| Aucun champ None dans sessions | ✅ | date, sport, workout_type, duration_min, fatigue_score tous renseignés |
| Notes d'allure depuis vdot_paces.json | ✅ | easy_z1: "5:36–6:12/km \| Z1 easy (60-74% HRmax)" |
| Allure easy_z1 VDOT 45 | ✅ | 5:36–6:12/km |
| Allure tempo_z2 VDOT 45 | ✅ | 4:48/km (seuil) |
| TID 80/20 respecté | ✅ | Z1 + session qualité (tempo/VO2max) |
| Zones FC dans notes | ✅ | "Z1 (60-74% HRmax)", "Z2 (80-88% HRmax)", "Z3 (95-100% HRmax)" |
| Deload semaine 4 | ✅ | Charge réduite vs semaine normale |
| Tapering race -1 semaine | ✅ | Uniquement easy_z1 + activation_z3 |
| Fallback sans Strava | ✅ | VDOT 45 du profil utilisé, prescription complète |
| Fallback sans Terra (pas de HRV) | ✅ | readiness_modifier = 1.0, pas de crash |
| Sessions sur jours disponibles | ✅ | Offsets respectés |

### Problème trouvé et corrigé

**Avant :** `generate_running_sessions()` produisait des `WorkoutSlot.notes = ""` — aucune allure ni zone FC.

**Correction :** Ajout de `get_vdot_paces(vdot: float) -> dict` dans `backend/app/core/running_logic.py` :
- Lit `data/vdot_paces.json` (table Daniels complète, VDOT 20-85)
- Clamp et arrondi au VDOT disponible le plus proche
- Fallback gracieux si fichier absent → dict vide, pas de crash
- Inject via paramètre `_paces` pour les tests (évite I/O)

`_build_pace_note(workout_type, paces)` génère le message :
- `easy_z1` → `"5:36–6:12/km | Z1 easy (60-74% HRmax)"`
- `tempo_z2` → `"4:48/km | Z2 tempo (80-88% HRmax)"`
- `vo2max_z3` → `"4:21/km | Z3 VO2max (95-100% HRmax)"`

### Prescription exemple (Simon, VDOT 45, semaine 2 build)

```
Session 1 (Samedi) : long_run_z1, 82 min
  → "5:54/km | Z1 long run (60-74% HRmax)"

Session 2 (Dimanche) : tempo_z2, 58 min
  → "4:48/km | Z2 tempo (80-88% HRmax)"

Session 3 (Lundi) : easy_z1, 64 min
  → "5:36–6:12/km | Z1 easy (60-74% HRmax)"
```

---

## 2. Lifting Coach

### Tests créés : `tests/e2e/test_agents_integration.py::TestLiftingCoachSimonE2E`

**Profil de test :** Simon — phase build, fatigue quadriceps simulée (squat 100kg×5 × 3 séances)

### Résultats

| Test | Statut | Valeurs générées |
|------|--------|-----------------|
| Types sessions Hevy-compatibles | ✅ | upper_strength, lower_strength, upper_hypertrophy, arms_hypertrophy, full_body_endurance |
| Semaine force (DUP=1, week 1) | ✅ | upper_strength + lower_strength |
| Semaine hypertrophie (DUP=0, week 3) | ✅ | upper_hypertrophy |
| Reduction jambes pour hybride | ✅ | lower_strength < upper_strength (hybrid_reduction 40%) |
| Sessions jours disponibles | ✅ | Offsets respectés |
| Deload semaine 4 | ✅ | weekly_load réduit |
| Fallback sans Hevy | ✅ | BEGINNER assumé, 2 sessions générées |
| Notes Tier d'exercice | ✅ | "Tier 1 \| chest, back..." |
| FatigueScore complet | ✅ | local_muscular, cns_load, metabolic_cost, recovery_hours renseignés |

### Prescription exemple (Simon, semaine 1 force)

```
Session 1 (Mardi) : upper_strength, 75 min
  → "Tier 1 | chest, back, shoulders, triceps, biceps"

Session 2 (Jeudi) : lower_strength, 36 min (hybrid_reduction 40%)
  → "quads, hamstrings"
```

---

## 3. Recovery Coach V3

### Tests existants : `tests/v3/test_recovery_coach_v3.py` (25 tests)

### 5 scénarios de veto validés

| Scénario | Statut | Résultat |
|----------|--------|----------|
| ✅ Vert — tout normal | ✅ | status=green, cap=1.0, veto=False |
| 🟡 Jaune — HRV ratio 0.75 (-25%) | ✅ | status=yellow, cap=0.85, veto=False |
| 🔴 Rouge — EA < 30 (femme) | ✅ | status=red, ea_component=red, veto=True, cap=0.0 |
| 🔴 Rouge — allostatic > 80 | ✅ | status=red, allostatic_component=red, veto=True |
| 🔴 Rouge cycle — menstruel + HRV jaune | ✅ | status=red (2 indicateurs), veto=True |

### Logique de synthèse validée

- **0 indicateur hors zone** → vert, cap 1.0
- **1 indicateur hors zone** → jaune, cap 0.85 (-15%)
- **2+ indicateurs hors zone OU 1 rouge** → rouge, veto déclenché, cap 0.0
- **Fallback HRV absent** → green (cold start, pas de pénalité)
- **Fallback EA absent** → green (non comptabilisé)
- **Cycle non activé** → cycle_component = None (pas comptabilisé)

---

## 4. Energy Coach

### Tests existants : `tests/v3/test_energy_coach.py` (26 tests)

### Validation EnergySnapshot

| Test | Statut | Valeur exemple |
|------|--------|----------------|
| Calcul EA correct | ✅ | (2400 - 400) / 60 = 33.33 kcal/kg FFM |
| Allostatic score 0-100 | ✅ | Score normalisé |
| Veto EA critique (homme < 25) | ✅ | EA = 16.67 → veto=True |
| Veto allostatic > 80 | ✅ | HRV -50% + sommeil 0% + exhausting + significant → score ≈ 84.5 → veto |
| Pas de veto si tout OK | ✅ | EA 49.09, score bas → veto=False |
| Cap 0.85 pour score 61-80 | ✅ | recommended_intensity_cap = 0.85 |
| Cycle_phase propagée | ✅ | snap.cycle_phase = "luteal" |
| Flag red_s_risk après 3 jours | ✅ | ea_history=[22,21] + EA=18.33 → red_s_risk |

### RED-S detection validée

- EA < 30 (femme) ou < 25 (homme) pendant 3 jours consécutifs → flag `red_s_risk`
- Vérifié depuis la fin de l'historique (jours les plus récents)

---

## 5. Head Coach

### Tests créés : `tests/e2e/test_agents_integration.py::TestHeadCoachWorkflowE2E`

| Test | Statut |
|------|--------|
| build_week() retourne WeeklyPlan | ✅ |
| Plan contient des sessions | ✅ |
| Readiness level valide (green/yellow/red) | ✅ |
| Readiness verte avec bonnes données Terra | ✅ |
| ACWR en zone sûre avec charge stable | ✅ |
| Conflit CRITICAL détecté (VO2max + lifting même jour) | ✅ |
| Résolution : session courte supprimée | ✅ |
| Notes de tous les agents collectées | ✅ |
| FatigueScore global calculé | ✅ |
| Budgets sport injectés (running prioritaire) | ✅ |
| Human-in-the-loop : structure WeeklyPlan complète | ✅ |

### Workflow de détection et résolution de conflit

```
Running VO2max (45min, Lundi) + Lifting lower_strength (30min, Lundi)
→ detect_conflicts() → CRITICAL: "hiit_strength_same_session"
→ _arbitrate() → session la plus courte (lifting 30min) supprimée
→ Plan final : VO2max (45min) uniquement ce lundi
```

---

## 6. Nutrition Coach

### Tests créés : `tests/e2e/test_agents_integration.py::TestNutritionCoachE2E`

**Profil de test :** Simon, 78.5 kg

### Prescription par type de jour

| Jour | Carbs (g/kg) | Protéines (g/kg) | Graisses (g/kg) | Calories (Simon 78.5 kg) |
|------|--------------|------------------|-----------------|--------------------------|
| Repos | 3.5 | 1.8 | 1.2 | 2,033 kcal |
| Force | 4.5 | 1.8 | 1.2 | 2,347 kcal |
| Endurance courte | 5.5 | 1.8 | 1.2 | 2,661 kcal |
| Endurance longue | 6.5 | 1.8 | 1.2 | 2,975 kcal |
| Race | 7.0 | 1.8 | 1.2 | 3,132 kcal |

### Phase lutéale validée

| Ajustement | Statut | Valeur |
|------------|--------|--------|
| +0.2g protéines/kg | ✅ | "protein+0.2g/kg" dans notes |
| +200 kcal/jour | ✅ | "kcal+200" dans notes |
| Suppléments fer + magnésium | ✅ | "supp=iron,magnesium" dans notes |

### Phase menstruelle validée

| Ajustement | Statut | Valeur |
|------------|--------|--------|
| Suppléments fer + magnésium + oméga-3 | ✅ | "supp=iron,magnesium,omega3" dans notes |

---

## Problèmes restants

### Non critiques (hors scope actuel)

1. **Running Coach — Warmup/cooldown structuré** : Le `WorkoutSlot` ne contient pas de blocs structurés (warmup, main, cooldown). Les paces sont dans les notes (string) mais pas dans un format structuré. À traiter en V3 avec un nouveau schéma `SessionBlock`.

2. **Lifting Coach — Charges et RPE par exercice** : Le `WorkoutSlot` contient le type de session et le Tier d'exercice dans les notes, mais pas les charges spécifiques ni les RPE cibles par exercice. Ces données sont dans `exercise-database.json` et `volume-landmarks.json` mais non injectées dans le WorkoutSlot. À traiter avec un nouveau champ `exercises: list[ExerciseSlot]`.

3. **Swimming Coach** : Non couvert par les nouveaux tests E2E (les tests existants vérifient la structure de base). Couverture complète à ajouter en Phase 9.

4. **Biking Coach** : Idem Swimming Coach.

5. **Head Coach — Human-in-the-loop API** : Le workflow de confirmation athlète n'est pas implémenté en route HTTP. Le `WeeklyPlan` est structurellement complet et prêt à être affiché, mais le cycle requête/confirmation/modification n'existe pas encore. À implémenter en Phase 11.

---

## Tests totaux après cette session

| Suite | Avant | Après | Delta |
|-------|-------|-------|-------|
| tests/ (total) | 1559 | 1623 | +64 |
| tests/e2e/ | 7 | 71 | +64 |
| tests/v3/ | 76 | 76 | 0 |
| tests/backend/agents/ | 51 | 51 | 0 |

Tous les tests passent. Aucune régression.
