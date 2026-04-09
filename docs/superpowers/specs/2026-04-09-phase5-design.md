# Phase 5 — Frontend
**Date:** 2026-04-09
**Status:** Approved

---

## Objectif

Construire le frontend Next.js qui rend le backend Phase 4 utilisable. Quatre pages : onboarding, dashboard, plan, revue hebdomadaire.

Chat Head Coach reporté à Phase 6 (nécessite backend streaming non encore implémenté).

---

## Stack

- **Framework:** Next.js 14, App Router
- **Styling:** Tailwind CSS + shadcn/ui
- **Thème:** dark/light toggle via `next-themes`
- **Tests:** Vitest + React Testing Library
- **Auth:** JWT dans `localStorage`

---

## Architecture

Toutes les pages sont des Client Components (`"use client"`). Pas de server-side data fetching — tous les appels API partent du navigateur vers FastAPI (`http://localhost:8000`). Next.js gère uniquement le routing et le layout.

**Viewport:** Desktop + breakpoints mobile. Pas mobile-first.

**Navigation:** Top nav horizontal (logo + liens + theme toggle + nom utilisateur).

---

## Structure des fichiers

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout : AuthProvider + ThemeProvider + TopNav
│   │   ├── page.tsx                # Redirect : /dashboard si token, sinon /onboarding
│   │   ├── onboarding/page.tsx     # Wizard 3 étapes (public)
│   │   ├── login/page.tsx          # Formulaire login (public)
│   │   ├── dashboard/page.tsx      # Semaine en cours : progression + prochaine séance
│   │   ├── plan/page.tsx           # Liste des séances du plan courant
│   │   └── review/page.tsx         # Formulaire revue hebdomadaire
│   ├── components/
│   │   ├── top-nav.tsx             # Barre de navigation + theme toggle
│   │   ├── protected-route.tsx     # Redirige vers /login si pas de token
│   │   └── ui/                     # Primitives shadcn/ui (Button, Card, Input, etc.)
│   └── lib/
│       ├── api.ts                  # Client fetch typé (lit JWT, ajoute header, gère 401)
│       └── auth.tsx                # AuthContext : token + athlete_id, login(), logout()
├── package.json
├── tailwind.config.ts
└── next.config.ts
```

---

## Pages

### 1. `/onboarding` — Wizard 3 étapes (public)

**Étape 1 — Compte**
- `email: string`
- `password: string` (min 8 caractères)

**Étape 2 — Profil athlète (champs requis uniquement)**
- `name: string`
- `age: int` (14–100)
- `sex: "M" | "F" | "other"` (select)
- `weight_kg: float`
- `height_cm: float`
- `primary_sport: Sport` (RUNNING | LIFTING | SWIMMING | BIKING)
- `sports: list[Sport]` (multi-select, pré-rempli avec primary_sport)
- `goals: list[string]` (champ texte libre, plusieurs valeurs possibles)
- `available_days: list[int]` (0=Lun … 6=Dim, sélecteur de jours)
- `hours_per_week: float`

Les champs optionnels (`max_hr`, `vdot`, `ftp_watts`, etc.) utilisent leurs valeurs par défaut — non affichés en onboarding (YAGNI).

**Étape 3 — Plan**
- `plan_start_date: date` (date picker, défaut = lundi prochain)

**Submit:** `POST /athletes/onboarding` → stocke `token` + `athlete_id` dans localStorage → redirect `/dashboard`.

**Erreurs:** email dupliqué → message inline. Mot de passe trop court → validation inline.

---

### 2. `/login` — Login (public)

- `email` + `password`
- `POST /auth/login` → stocke token → redirect `/dashboard`
- Lien vers `/onboarding` si pas encore de compte

---

### 3. `/dashboard` — Semaine en cours (protégé)

**Données:** `GET /athletes/{id}/week-status`

**Layout progress-first:**
- En-tête : `Week N of M · PHASE NAME`
- Barre de progression : `completion_pct` (%)
- Métriques secondaires : heures planifiées / réelles, ACWR avec indicateur coloré (vert < 0.8, jaune 0.8–1.3, rouge > 1.3)
- Prochaine séance : première session non encore passée du plan
- Lien → `/plan` pour voir toutes les séances
- Lien → `/review` si fin de semaine (basé sur `week_end_date`)

**État vide:** "Aucun plan actif" + bouton "Générer un plan" → `POST /athletes/{id}/plan`.

---

### 4. `/plan` — Plan de la semaine (protégé)

**Données:** `GET /athletes/{id}/plan`

**Layout:** Liste de séances groupées par jour.

Chaque séance affiche :
- Jour + type (Run, Lift, etc.)
- Durée et intensité
- Description courte

---

### 5. `/review` — Revue hebdomadaire (protégé)

**Données soumises:** `POST /athletes/{id}/review`

**Champs:**
- `week_end_date: date` (défaut = dimanche dernier)
- `readiness_score: number | null` (slider 1–10)
- `hrv_rmssd: number | null`
- `sleep_hours_avg: number | null`
- `comment: string` (textarea)

**Résultat affiché après submit :**
- ACWR calculé
- Ajustement appliqué (`adjustment_applied`)
- `next_week_suggestion` (message lisible)

---

## Flux de données

1. App charge → `AuthProvider` lit `localStorage` pour `token` + `athlete_id`
2. `/` vérifie token → redirect `/dashboard` ou `/onboarding`
3. Pages protégées encapsulent `<ProtectedRoute>` → redirect `/login` si pas de token
4. Tous les appels API passent par `api.ts` : ajoute `Authorization: Bearer <token>`, lève une erreur sur 401
5. Sur 401 → `auth.logout()` → vide localStorage → redirect `/login`
6. Onboarding : `POST /athletes/onboarding` → stocke token + athlete_id → redirect `/dashboard`
7. Login : `POST /auth/login` → stocke token + athlete_id → redirect `/dashboard`

---

## Gestion d'erreurs

| Cas | Comportement |
|---|---|
| 401 sur n'importe quel appel | logout + redirect `/login` |
| 404 sur week-status | État vide "Aucun plan" + lien génération |
| Erreur réseau | Toast d'erreur en haut de page |
| Validation formulaire | Erreurs inline par champ |

---

## Design visuel

- Thème : professionnel, minimaliste, épuré
- Dark mode par défaut, toggle dark/light
- Top nav : `RESILIO+` logo + liens + toggle + nom utilisateur
- Palette : violet (`#7c3aed`, `#a78bfa`) comme couleur accent, verts pour succès (`#34d399`), ambre pour avertissement ACWR (`#fbbf24`)
- La skill `frontend-design` est utilisée par les subagents lors de l'implémentation de chaque page pour garantir une qualité visuelle production

---

## Tests

Vitest + React Testing Library. Le client API (`src/lib/api.ts`) est mocké globalement.

| Fichier | Ce qui est testé |
|---|---|
| `tests/frontend/test_onboarding.tsx` | Navigation 3 étapes, soumission, erreur email dupliqué |
| `tests/frontend/test_login.tsx` | Login réussi, mauvais mot de passe → erreur |
| `tests/frontend/test_dashboard.tsx` | Rendu week-status, état vide sans plan |
| `tests/frontend/test_plan.tsx` | Rendu liste séances |
| `tests/frontend/test_review.tsx` | Soumission formulaire, affichage suggestion ACWR |

---

## Architecture globale après Phase 5

```
/onboarding     ← public, wizard 3 étapes
/login          ← public
/dashboard      ← protégé, semaine en cours
/plan           ← protégé, séances du plan
/review         ← protégé, revue hebdomadaire
```

---

## Livrables

- `frontend/src/lib/api.ts`
- `frontend/src/lib/auth.tsx`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/onboarding/page.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/plan/page.tsx`
- `frontend/src/app/review/page.tsx`
- `frontend/src/components/top-nav.tsx`
- `frontend/src/components/protected-route.tsx`
- `frontend/package.json`, `tailwind.config.ts`, `next.config.ts`
- Tests : 5 fichiers Vitest
- Branche : `feat/phase5-frontend`
