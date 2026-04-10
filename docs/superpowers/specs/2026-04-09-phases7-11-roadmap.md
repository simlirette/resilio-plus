# Resilio Plus — Roadmap Phases 7–11

**Date:** 2026-04-09  
**Statut:** Approuvé

---

## Contexte

Les phases 0–6 sont complètes (v1.0.0 taggé). Le projet dispose d'un backend multi-agents partiel (Head Coach, Running Coach, Lifting Coach), d'un frontend fonctionnel minimal, et d'une infrastructure Docker + E2E tests.

Ce document définit les 5 phases restantes pour compléter la vision du blueprint.

---

## État actuel (v1.0.0 + Phases 7-8)

### Backend — Construit (Phases 0–8)
- Head Coach + 7 agents spécialistes (Running, Lifting, Swimming, Biking, Nutrition, Recovery)
- Core : ACWR, fatigue, periodization, conflict detection, readiness, goal_analysis, biking/swimming/nutrition/recovery logic
- Routes : athletes, auth, onboarding, plans, reviews, sessions, nutrition, recovery, connectors
- Connecteurs : Strava OAuth (actif), Hevy (implémenté), Terra (implémenté), FatSecret (classe — hors scope)
- JWT auth, SQLite, Docker Compose, 7 tables DB
- Tests : 1243+ passing, 7 E2E scenarios

### Frontend — Construit (Phases 4–8)
- Login, onboarding (3 étapes), dashboard, plan, review, session detail, session log, history
- Dark/light theme, auth context, protected routes, Top Nav avec History

---

## Phase 7 — Agents manquants ✅ COMPLÈTE

**Scope :** Backend uniquement  
**Priorité :** ★★★★★  
**Status :** Livré — commits `cea0565`→`6c45cf0` sur `main`

Compléter les 4 agents manquants du blueprint. Sans eux, le plan est vide pour les athlètes cyclistes, nageurs, ou ceux avec des besoins nutritionnels et de récupération spécifiques.

### Livrables
- `backend/app/agents/biking_coach.py` — Zones Coggan, FTP, CTL/ATL/TSB, PPi
- `backend/app/agents/swimming_coach.py` — CSS zones, SWOLF, DPS, eau libre vs piscine
- `backend/app/agents/nutrition_coach.py` — Glucides par type de jour, protéines, intra-effort, suppléments
- `backend/app/agents/recovery_coach.py` — HRV/RMSSD, readiness score, sleep banking, protocoles récup
- `backend/app/core/biking_logic.py` — Logique stateless vélo
- `backend/app/core/swimming_logic.py` — Logique stateless natation
- `backend/app/core/nutrition_logic.py` — Calculs nutritionnels par jour/séance
- `backend/app/core/recovery_logic.py` — Calculs readiness HRV
- Endpoints API pour chaque agent (GET /athletes/{id}/nutrition, GET /athletes/{id}/recovery-status)
- Tests unitaires complets (approx. +200 tests)

### Dépendances
- Aucune dépendance externe — peut démarrer immédiatement après v1.0.0

---

## Phase 8 — Boucle quotidienne ✅ COMPLÈTE

**Scope :** Full stack (backend + frontend)  
**Priorité :** ★★★★★  
**Dépend de :** Phase 7 (sessions enrichies par les nouveaux agents)  
**Status :** Livré — commits `28a328b`→`7fb144d` sur `main`

La boucle quotidienne de l'athlète : voir les détails exacts de sa séance, logger ce qu'il a réellement fait. Ferme la boucle feedback qui rend le coaching adaptatif.

### Livrables Backend
- `POST /athletes/{id}/sessions/{session_id}/log` — Logger réel vs prévu (durée, sets/reps/charges effectifs, notes)
- `GET /athletes/{id}/history` — Historique des semaines passées (plans + reviews)
- `GET /athletes/{id}/sessions/{session_id}` — Détail complet d'une séance
- Modèle DB : `SessionLogModel` (actual_sets, actual_duration, skipped, notes)

### Livrables Frontend
- `frontend/src/app/session/[id]/page.tsx` — Détail de séance : exercices avec sets/reps/charges ou paces/zones course
- `frontend/src/app/session/[id]/log/page.tsx` — Formulaire de logging post-séance
- `frontend/src/app/history/page.tsx` — Historique des semaines avec plans et reviews
- Mise à jour `plan/page.tsx` — Liens vers détail de séance + badge "complété/sauté"

### Dépendances
- Phase 7 requis (sessions plus riches avec vélo/natation/nutrition)

---

## Phase 9 — Connecteurs complets

**Scope :** Full stack  
**Priorité :** ★★★★☆  
**Dépend de :** Phase 8 (le logging manuel devient automatique)

Automatise le logging de Phase 8. Chaque connecteur remplace la saisie manuelle par un sync automatique.

### Livrables Backend
- Hevy pipeline complet : `GET /athletes/{id}/connectors/hevy/sync` → mappe workouts Hevy → `SessionLogModel`
- Terra intégration : pull HRV (RMSSD), sleep hours → alimente Recovery Coach
- Strava sync amélioré : pull activités récentes → mappe vers sessions de course/vélo/natation

> **Note :** FatSecret retiré du scope — la nutrition est calculée directement dans Resilio via une base de données d'aliments interne (NutritionCoach). Pas besoin d'app externe.

### Livrables Frontend
- `frontend/src/app/settings/page.tsx` — Page settings principale
- `frontend/src/app/settings/connectors/page.tsx` — Statut de chaque connecteur (connecté/déconnecté, dernière sync), boutons connect/disconnect/sync

### Dépendances
- Phase 8 requis (SessionLogModel existe)
- Phase 7 requis (Recovery Coach consomme données Terra)

---

## Phase 10 — Analytics Dashboard

**Scope :** Frontend heavy + quelques endpoints backend  
**Priorité :** ★★★★☆  
**Dépend de :** Phases 8-9 (données historiques accumulées)

Rend le coaching visible et trustworthy. Les charts montrent pourquoi le coach ajuste le plan.

### Livrables Backend
- `GET /athletes/{id}/analytics/load` — Série temporelle ACWR, CTL, ATL, TSB (dernières N semaines)
- `GET /athletes/{id}/analytics/sport-breakdown` — Heures/sport par semaine
- `GET /athletes/{id}/analytics/performance` — VDOT progression, e1RM progression

### Livrables Frontend
- `frontend/src/app/analytics/page.tsx` — Dashboard analytics principal
- Composants charts (Recharts) :
  - `AcwrTrendChart` — ACWR sur 8 semaines avec zones de danger
  - `TrainingLoadChart` — CTL/ATL/TSB
  - `SportBreakdownChart` — Pie/bar chart heures par sport
  - `PerformanceTrendChart` — VDOT et e1RM au fil du temps
- Mise à jour navigation pour inclure "Analytics"

### Dépendances
- Phase 8 requis (SessionLogModel fournit actuals pour analytics)
- Phase 9 recommandé (plus de données = charts plus riches)

---

## Phase 11 — Polish & Power Features

**Scope :** Full stack  
**Priorité :** ★★★☆☆  
**Dépend de :** Phases 8-10 (core features solides)

Features de puissance et polish final pour une expérience coaching premium.

### Livrables
- **Profil éditable** : `PUT /athletes/{id}/profile` + page `/settings/profile` (poids, objectifs, jours dispo, sport primaire)
- **Customisation plan** : `PATCH /athletes/{id}/plan/sessions/{id}` (swap, skip, ajuster volume) + UI drag-and-drop ou menu contextuel
- **Alertes ACWR** : badge/bannière dans dashboard quand ACWR > 1.3 ou > 1.5
- **Nutrition display** : composant `NutritionDirectives` dans dashboard (macros cibles du jour, suggestions intra-effort)
- **Notifications in-app** : toast/banner quand plan semaine généré, quand review en retard

---

## Récapitulatif

| Phase | Scope | Contenu | Priorité | Status |
|-------|-------|---------|----------|--------|
| 7 | Backend | Biking + Swimming + Nutrition + Recovery agents | ★★★★★ | ✅ Complète |
| 8 | Full stack | Session detail + logging + historique | ★★★★★ | ✅ Complète |
| 9 | Full stack | Connecteurs Hevy/Terra/Strava + Settings UI | ★★★★☆ | ❌ À faire |
| 10 | Frontend+ | Analytics charts (ACWR, CTL/ATL/TSB, progression) | ★★★★☆ | ❌ À faire |
| 11 | Full stack | Profil, customisation, alertes, nutrition, notifications | ★★★☆☆ | ❌ À faire |

## Logique de dépendances

```
Phase 7 (agents) → Phase 8 (boucle quotidienne) → Phase 9 (connecteurs auto) → Phase 10 (analytics) → Phase 11 (polish)
```

Chaque phase produit de la valeur standalone — Phase 7 alone complète déjà le backend multi-agent pour tous les sports.
