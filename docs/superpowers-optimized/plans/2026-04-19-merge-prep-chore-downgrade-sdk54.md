# Merge Prep: chore/downgrade-sdk54 → main

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-optimized:executing-plans to implement this plan task-by-task.

**Goal:** Préparer un merge propre de la branche UI mobile vers main — audit, santé, cleanup, docs, PR template.
**Architecture:** Branche chore/downgrade-sdk54 contient 67 commits, 129 fichiers, ~22K insertions. Travail purement frontend/mobile (Expo SDK 54). Backend inchangé.
**Tech Stack:** pnpm monorepo, Expo SDK 54, React Native, TypeScript, FastAPI (backend frozen).
**Assumptions:**
- Backend frozen — ne pas toucher. Échec pytest isolé non-bloquant UNIQUEMENT si zéro fichier backend/** dans `git diff main --stat` (vérifié Task 2 Step 5).
- 5 pages placeholder (Today's Session, Metric Detail, Nutrition Log, Profile/Settings, Connectors) — Today's Session confirmé absent (aucun `session.tsx` dans tabs, `state.md` le liste sous "À venir").
- Pas de merge auto. Pas de gh pr create exécuté. Juste affiché.
- OS: Windows. Shell: bash (via git bash). Séparateur de commandes: `;` (pas `&&`).

---

## Context

| Fait | Valeur |
|---|---|
| Commits ahead of main | 67 |
| Fichiers changés | 129 |
| Insertions / suppressions | +22 527 / -2 078 |
| state.md | Modifié non-commité (à commmiter étape 1) |
| Fichiers untracked notables | .backup-polish×5, .backup-sdk55×2, .expo/, docs×4 |

---

## Task 1: Audit état branche

**Files:**
- Run: bash (lecture seule)

**Red-team gate:** Working tree pas clean OU diff > 500 fichiers → STOP et rapport.

- [ ] **Step 1: Vérifier état working tree**

```bash
cd /c/Users/simon/resilio-plus
git status
```

Expected: seul `state.md` apparaît Modified. Les .backup sont untracked (pas commités = OK).

- [ ] **Step 2: Commmiter state.md avant d'aller plus loin**

```bash
cd /c/Users/simon/resilio-plus
git add state.md
git commit -m "docs: state.md — branch ready for merge prep"
```

- [ ] **Step 3: Rapport commits**

```bash
git log main..HEAD --oneline
git log main..HEAD --oneline | wc -l
```

Expected: 68 commits (67 + le commit state.md ci-dessus).

- [ ] **Step 4: Rapport diff taille**

```bash
git diff main --stat | tail -5
```

Expected: ~129 files, ~22 500 insertions. Si > 500 fichiers → STOP.

- [ ] **Step 5: Rapport concis**

Afficher:
```
AUDIT RÉSULTAT
  Commits ahead main : 68
  Fichiers changés   : 129
  Insertions         : +22 527
  Suppressions       : -2 078
  Working tree       : CLEAN ✅
  Gate > 500 fichiers: PASS ✅
```

---

## Task 2: Vérifications santé

**Files:**
- Run: bash (lecture seule + installs)

**Red-team gate:** Un seul check rouge → STOP rapport, ne pas continuer.

- [ ] **Step 1: pnpm install**

```bash
cd /c/Users/simon/resilio-plus
pnpm install
```

Expected: résolution propre, 0 erreur.

- [ ] **Step 2: Mobile typecheck**

```bash
cd /c/Users/simon/resilio-plus/apps/mobile
pnpm typecheck
```

Expected: 0 erreur TypeScript.

- [ ] **Step 3: Workspace typecheck (web)**

```bash
cd /c/Users/simon/resilio-plus
pnpm -w typecheck
```

Expected: 0 erreur TypeScript.

- [ ] **Step 4: Workspace lint**

```bash
cd /c/Users/simon/resilio-plus
pnpm -w lint
```

Expected: 0 erreur ESLint.

- [ ] **Step 5: Backend (frozen — vérification conditionnelle)**

D'abord vérifier si des fichiers backend sont dans le diff:
```bash
cd /c/Users/simon/resilio-plus
git diff main --stat | grep "^backend/" | head -20
```

- Si **zéro résultat** → lancer pytest, échec isolé = noise non-bloquant:
  ```bash
  cd backend
  poetry run pytest tests/ -x --tb=short -q 2>&1 | tail -20
  ```
  Expected: ≥ 2430 passing. Échec → noter, continuer.

- Si **fichiers backend/** présents dans diff → **STOP strict. Rapport immédiat.**

---

## Task 3: Cleanup diff

**Files:**
- Modify: potentiellement plusieurs fichiers mobile + ajout à .gitignore

**Protocol:** Lister TOUTES les trouvailles AVANT de modifier. Attendre GO explicite du user. Ensuite seulement appliquer.

**Red-team gate:** Après cleanup, re-run typecheck + lint pour confirmer rien cassé.

- [ ] **Step 1: Scanner console.log ajoutés sur la branche**

```bash
cd /c/Users/simon/resilio-plus
git diff main -- "apps/mobile/**" "packages/ui-mobile/**" | grep "^+" | grep "console\.log" | grep -v "^+++"
```

Expected: aucun console.log de debug non-intentionnel.

- [ ] **Step 2: Scanner TODO ajoutés sur la branche (hors TODO légitimes documentés)**

```bash
git diff main -- "apps/mobile/**" "packages/ui-mobile/**" | grep "^+" | grep "TODO" | grep -v "^+++"
```

Expected: lister tous, vérifier lesquels sont légitimes (ex: `// TODO: wire backend` = acceptable dans les mocks).

- [ ] **Step 3: Vérifier que les .backup ne sont PAS commités**

```bash
git ls-files | grep "backup"
```

Expected: aucun résultat. Les .backup doivent être untracked uniquement.

- [ ] **Step 4: Vérifier mocks hors apps/mobile/src/mocks/**

```bash
git diff main --name-only | grep "mock" | grep -v "apps/mobile/src/mocks"
```

Expected: tout mock commité est dans apps/mobile/src/mocks/ OU est un mock de test légitime ailleurs.

- [ ] **Step 5: Scanner secrets/tokens hardcodés**

```bash
git diff main -- "apps/mobile/**" "packages/ui-mobile/**" | grep "^+" | grep -iE "(api_key|secret|token|password|bearer|sk-|ANTHROPIC)" | grep -v "^+++" | grep -v "//.*mock\|// TODO\|mock.*token\|placeholder"
```

Expected: aucun résultat.

- [ ] **Step 6: AFFICHER LISTE TROUVAILLES + proposition .gitignore → attendre GO user**

Afficher liste structurée incluant la proposition .gitignore:
```
CLEANUP FINDINGS
  console.log      : [N trouvés / 0]
  TODO             : [liste ou 0]
  .backup commités : [liste ou CLEAN]
  mocks hors mocks/: [liste ou CLEAN]
  secrets          : [liste ou CLEAN]

PROPOSITIONS (attente GO)
  .gitignore       : ajouter *.backup-* et .expo/ (untracked, clutter)
  [toute autre suppression listée ici]
```

Ne rien modifier avant GO explicite du user.

Attendre GO avant de passer à Step 7.

- [ ] **Step 7 (après GO): Appliquer corrections validées**

Appliquer uniquement ce que le user a approuvé.

Si .gitignore à mettre à jour:
```bash
cd /c/Users/simon/resilio-plus
# vérifier existence
ls .gitignore
# ajouter les entrées via Edit tool (ne pas utiliser echo >>)
```
Ajouter à la fin de .gitignore:
```
# Backup files (created during dev sessions)
*.backup-*
.expo/
```

Si console.log à supprimer → éditer les fichiers concernés avec Edit tool.

- [ ] **Step 8: Re-run typecheck + lint post-cleanup**

```bash
cd /c/Users/simon/resilio-plus/apps/mobile
pnpm typecheck

cd /c/Users/simon/resilio-plus
pnpm -w typecheck
pnpm -w lint
```

Expected: 0 erreur.

- [ ] **Step 9: Commit cleanup**

```bash
cd /c/Users/simon/resilio-plus
git add .gitignore
# + tout fichier modifié lors du cleanup
git commit -m "chore: pre-merge cleanup — .gitignore .backup/.expo, [console.logs si supprimés]"
```

---

## Task 4: Documentation

**Files:**
- Create or modify: `docs/CHANGELOG.md`
- Conditionally modify: `CLAUDE.md` (seulement si état frontend changé de façon non-documentée)

- [ ] **Step 1: Vérifier si CHANGELOG.md existe**

```bash
ls /c/Users/simon/resilio-plus/docs/CHANGELOG.md 2>&1
```

- [ ] **Step 2: Créer/compléter la section UI Mobile Rework**

Créer `docs/CHANGELOG.md` si absent, ou ajouter section en tête si présent:

```markdown
## 2026-04 — UI Mobile Rework P1–P6 (chore/downgrade-sdk54)

### Pages livrées (5/10)
- **P1 Auth**: Login, Signup, Forgot-password — FloatingLabelInput, Button Wave 1
- **P2 Onboarding**: 5 étapes avec slide animation (Animated.Value, pas reanimated), SegmentedControl
- **P4 Training History**: Calendrier grille-mois + discipline dots, liste semaines groupées, drawer détail jour
- **P5 Coach Chat**: Conversation UI + HITL bottom sheet (single/multi/rank), BlurView, PanResponder drag
- **P6 Home Dashboard** (rewrite complet): ReadinessRingHome 160px sémantique, MetricsStrip 3 cols, HomeSessionCard, CognitiveLoadBar 24 segments, toggle DEV via tap avatar

### Placeholders restants (5/10) — non bloquants pour merge
- Today's Session (`/session/live`) — route non créée, listée sous "À venir" dans state.md
- Metric Detail (`/metric/[id]`)
- Nutrition Log (`/nutrition`)
- Profile / Settings (`/profile`) — scaffold vide
- Connectors (`/connectors`)

### Ce qui N'est PAS inclus
- Wiring backend (toutes les pages utilisent des mocks locaux dans `apps/mobile/src/mocks/`)
- Connecteurs réels (Strava OAuth, Hevy, Terra)
- Authentification réelle (handleLogin/handleSignup contiennent des TODOs)
- Apple Sign In (expo-apple-authentication installé, non connecté)
- Tests unitaires composants Wave 1 (Button, FloatingLabelInput, HeroNumber, ProgressSegments, SegmentedControl)

### Stack technique confirmée
- Expo SDK 54 (downgrade depuis SDK 55 pour compatibilité Expo Go)
- expo-router v3 (file-based routing)
- NativeTabs via `expo-router/unstable-native-tabs` (iOS liquid glass, SDK 54 OK)
- PanResponder + Animated.Value pour drag (reanimated worklets absents du binaire Expo Go SDK 54)
- Space Grotesk exclusivement (Inter retiré)
- Amber/terracotta accent (#B8552E light / #D97A52 dark)
- Mocks dans `apps/mobile/src/mocks/`
```

- [ ] **Step 3: Vérifier si CLAUDE.md doit être mis à jour**

Chercher dans CLAUDE.md:
- SDK 54 confirmé → déjà documenté?
- Structure mocks → déjà documenté?
- NativeTabs liquid glass → déjà documenté?
- PanResponder pour HITL → déjà documenté?

```bash
grep -n "SDK 54\|NativeTabs\|PanResponder\|mocks" /c/Users/simon/resilio-plus/CLAUDE.md | head -20
```

Si tout est déjà présent → ne pas toucher CLAUDE.md. Si des éléments manquent → ajouter uniquement la section mobile frontend, après le bloc "Vague 1 Frontend" existant.

- [ ] **Step 4: Red-team reviewer externe**

Relire CHANGELOG comme dev qui n'a pas vu la branche:
- Scope clair? Peut-il distinguer "livré" vs "pas encore fait"?
- Contraintes techniques (pas de reanimated, SDK 54) explicites?
- Attendu PR: oui si tout lisible.

- [ ] **Step 5: Commit documentation**

```bash
cd /c/Users/simon/resilio-plus
git add docs/CHANGELOG.md CLAUDE.md
git commit -m "docs: CHANGELOG + CLAUDE.md — UI Mobile Rework P1-P6 scope"
```

---

## Task 5: Préparation PR

**Files:**
- Create: `.github/pull_request_templates/ui-mobile-rework.md`
- Push: origin chore/downgrade-sdk54

**Ne pas exécuter `gh pr create`. Afficher seulement.**

- [ ] **Step 1: Créer répertoire si absent**

```bash
mkdir -p /c/Users/simon/resilio-plus/.github/pull_request_templates/
```

- [ ] **Step 2: Créer le template PR**

Écrire `.github/pull_request_templates/ui-mobile-rework.md`:

```markdown
## Résumé technique

Rework complet de l'app mobile Expo (SDK 54) depuis un scaffold. 5 pages
livrées et testées manuellement sur iPhone via Expo Go. Toutes les pages
utilisent des mocks locaux — pas de wiring backend dans cette PR.
SDK downgrade 55→54 nécessaire pour compatibilité binaire Expo Go (reanimated
worklets absents de SDK 54, remplacés par Animated.Value + PanResponder).

---

## Pages livrées ✅

| Page | Route | Notes |
|---|---|---|
| Auth | `/auth/login`, `/auth/signup`, `/auth/forgot-password` | FloatingLabelInput, Button |
| Onboarding | `/onboarding` | 5 étapes, slide Animated.Value |
| Home Dashboard | `/(tabs)/` | P6 rewrite, ReadinessRing, MetricsStrip |
| Training History | `/(tabs)/training` | Calendrier + liste + drawer |
| Coach Chat | `/(tabs)/chat` | Conversation + HITL sheet |

## Pages placeholder (non bloquantes) 🚧

- Today's Session (`/session/live`) — route non créée
- Metric Detail (`/metric/[id]`)
- Nutrition Log (`/nutrition`)
- Profile / Settings (`/profile`)
- Connectors (`/connectors`)

---

## Ce qui N'est PAS dans cette PR

- Wiring backend (mocks only)
- Authentification réelle (handleLogin/handleSignup = TODO)
- Apple Sign In (installé, non connecté)
- Connecteurs Strava / Hevy / Terra
- Tests unitaires composants Wave 1

---

## Checklist QA manuelle (Expo Go iPhone)

Avant merge, valider sur device physique iOS (iPhone + Expo Go SDK 54):

### Navigation
- [ ] Tab bar iOS liquid glass visible (NativeTabs amber tintColor)
- [ ] Navigation Auth → Onboarding → Home fonctionnelle
- [ ] Back gesture iOS native opérationnel sur toutes les pages

### Home Dashboard
- [ ] Ring Readiness affiche valeur 78 (état normal)
- [ ] Tap avatar "SR" (dev toggle) → cycle 3 états: optimal/normal/récupération
- [ ] Ring couleur change (vert/amber/rouge) selon état
- [ ] MetricsStrip 3 colonnes visible, valeurs tabular-nums
- [ ] CTA "Voir la session" fonctionnel

### Coach Chat
- [ ] Messages s'affichent, input bar visible au-dessus clavier et NativeTabs
- [ ] HITL sheet s'ouvre par-dessus (BlurView backdrop)
- [ ] Type single: radio selection
- [ ] Type multi: checkbox multi-selection
- [ ] Type rank: drag PanResponder (grip dots ⋮⋮), swap avec haptics

### Training History
- [ ] Calendrier scroll mois (← →)
- [ ] Dots discipline colorés sur jours d'entraînement
- [ ] Tap jour → drawer slide-up avec détail session

### Clavier
- [ ] Sur Coach Chat: input collé au-dessus du clavier quand ouvert
- [ ] Sur Auth: champs non cachés par clavier

### Screenshots à attacher manuellement
> Attacher screenshots iPhone: Home (3 états), Chat + HITL sheet, Training History

---

## Tech Stack

- Expo SDK 54 / expo-router v3 / React Native 0.73.x
- NativeTabs: `expo-router/unstable-native-tabs`
- Animations: `Animated.Value` + `PanResponder` (reanimated absent SDK 54 Expo Go)
- Fonts: Space Grotesk via `expo-font`
- Bottom sheets: `@gorhom/bottom-sheet` + `expo-blur`
- Tokens: `@resilio/design-tokens`
```

- [ ] **Step 3: Commit template**

```bash
cd /c/Users/simon/resilio-plus
git add .github/pull_request_templates/ui-mobile-rework.md
git commit -m "chore: add PR template for ui-mobile-rework merge"
```

- [ ] **Step 4: Push branche**

```bash
cd /c/Users/simon/resilio-plus
git push -u origin chore/downgrade-sdk54
```

Expected: push réussi, branche tracked sur origin.

- [ ] **Step 5: Red-team PR template**

Relire template comme reviewer externe:
- Scope exhaustif (livré / non-livré)?
- QA checklist couvre les 3 états mock via tap avatar?
- Screenshot reminder présent?
- Commande gh pr create prête?

- [ ] **Step 6: AFFICHER (ne pas exécuter) la commande gh pr create**

```
gh pr create \
  --base main \
  --head chore/downgrade-sdk54 \
  --title "feat(mobile): UI rework P1-P6 — 5 pages Expo SDK 54 (mocks only)" \
  --body-file .github/pull_request_templates/ui-mobile-rework.md
```

---

## Rapport final

Afficher après Task 5:

```
MERGE PREP — RAPPORT FINAL
  Health checks       : ✅ typecheck + lint + pytest
  Commits             : 68 (main..HEAD)
  Fichiers diff       : 129
  Cleanup             : ✅ [résumé des corrections]
  CHANGELOG           : ✅ docs/CHANGELOG.md
  CLAUDE.md           : [mis à jour / inchangé]
  PR template         : ✅ .github/pull_request_templates/ui-mobile-rework.md
  Push origin         : ✅ chore/downgrade-sdk54
  gh pr create        : AFFICHÉ (non exécuté) — copier-coller pour créer la PR
```
