# UI Docs Preparation Report — 2026-04-18

Session de préparation documentaire pré-intégration pixel-perfect.
Aucun code d'app modifié dans cette session.

---

## 1. Fichiers créés

| Fichier | Taille | Notes |
|---|---|---|
| `docs/design/README.md` | — | Index + hiérarchie d'autorité + cible de port |
| `docs/design/flow auth/SPEC.md` | — | 3 écrans auth, basé screenshots + code source |
| `docs/design/onboarding/SPEC.md` | — | 5 étapes, basé screenshots + tokens.js |
| `docs/design/homedashboard/SPEC.md` | — | 3 états Readiness × 2 modes, basé screenshots + code |
| `docs/design/todays session/SPEC.md` | — | Mode A + B × Course + Muscu, basé screenshots + tokens.jsx |
| `docs/design/training historycalendar/SPEC.md` | — | Calendrier + Liste + Drawer, basé screenshots + theme.js |
| `docs/design/coach chat/SPEC.md` | — | Conversation + 3 types HITL, basé screenshots + code |
| `frontend/UI-RULES.md` | — | Règles UI globales alignées sur les screenshots |

## 2. Fichiers modifiés

Aucun fichier existant modifié. `frontend/UI-RULES.md` n'existait pas — créé.

## 3. Points notables identifiés

### Contradiction majeure résolue — Couleur d'accent
- **Anciennes specs/memories**: #5b5fef (violet) ou #3B74C9 (bleu)
- **Screenshots et code source**: amber/terracotta chaud, ~#B8552E (light) / #D97A52 (dark)
- **Résolution**: les screenshots gagnent. Les anciennes couleurs n'apparaissent dans aucun export. UI-RULES.md documente les valeurs correctes.

### Système dual-accent (non documenté avant)
Le projet utilise deux accents fonctionnellement distincts:
1. **Amber** (~#B8552E): accent UI général (nav, forms, liens, états sélectionnés)
2. **Lime électrique** (#C8FF4D): CTA primaire session uniquement ("Démarrer", "Set terminé")

Ce dual-accent n'était pas documenté explicitement. Les SPEC de chaque page le précisent.

### Dark backgrounds — légère incohérence entre pages
Les fonds dark varient légèrement selon les exports:
- Auth: #17171A
- Dashboard: #161412
- Training History: #1C1A17
- Session execution: #141311

Tous sont warm charcoal non-clinique, mais pas unifiés. Recommandé: choisir une valeur canonique dans `packages/design-tokens/` avant l'intégration.

### Dossier `ui archive/` — confirmé archive
`docs/design/ui archive/home/` contient `DESIGN-ANALYSIS.md` + ancienne version de l'UI. À ignorer. Un `DESIGN-ANALYSIS.md` existait dans ce dossier (fichier supprimé entre la création du repo et ce commit selon le git status initial).

### Coach Chat — références externes clarifiées
Les `uploads/` du dossier coach chat contiennent des screenshots d'un autre projet (UI "Jules/Claude Code agent"). Ces images sont de l'inspiration structurelle pour le pattern HITL uniquement. Le contenu textuel est explicitement ignoré dans le SPEC.

### Page Home — archive vs homedashboard
`ui archive/home/` est distinct de `homedashboard/`. Le SPEC homedashboard le documente. Aucune confusion possible.

---

## 4. Questions ouvertes à trancher avant l'intégration

### Critique (bloque l'implémentation)

1. **Fond dark canonique**: unifier les 4 valeurs (#141311, #161412, #17171A, #1C1A17) en une valeur unique dans `design-tokens`. Ou conserver les différences par contexte (session plus sombre = immersion) ?

2. **Transition Mode A → B (séance)**: navigation RN (push screen) ou remplacement de composant sur le même écran ? SharedTransition sur le titre ?

3. **Persistance session Mode B**: chrono continue en background ? Nécessite background task (expo-task-manager). Périmètre V1 ?

4. **Auth — état d'erreur**: position du message d'erreur (inline sous input fautif, ou toast global) — pas visible dans les screenshots.

### Important (peut démarrer l'implémentation, mais à définir rapidement)

5. **Home Dashboard — scroll**: page scrollable ou hauteur fixe ? Le CTA "Démarrer la séance" semble partiellement rogné → scroll probablement requis.

6. **Home Dashboard — CHARGE COGNITIVE**: indicateur visible en bas des screenshots mais non documenté dans le code disponible. À clarifier.

7. **Training History — tap sur jour sans séance**: ouvre un drawer ou rien ?

8. **Onboarding — animation de transition**: slide horizontal ou fade entre étapes ?

9. **Coach Chat — intensité du blur**: valeur exacte pour expo-blur `intensity` (20 ? 30 ?) derrière la sheet.

10. **HITL sheet snap point**: hauteur exacte (50% ? 60% ? 70%) selon le type de question.

### Mineur (documenté, À trancher en cours d'implémentation)

11. Onboarding — validation étape Profil: taille/poids obligatoires ou optionnels ?
12. Training History — navigation mois future: séances planifiées visibles ?
13. Auth loading state: opacité du CTA désactivé (40% ou 50%) ?
14. Training History — icône filtre (≡): fonctionnalité pour V1 ?

---

## 5. Recommandations pour la session d'intégration

### Ordre d'implémentation recommandé

Commencer par les pages sans dépendances profondes:

1. **Flow Auth** — le plus simple, pas de données live, 3 écrans bien définis
2. **Onboarding** — logique de formulaire, pas de données Resilio
3. **Home Dashboard** — nécessite la readiness ring (react-native-svg)
4. **Training History** — nécessite @gorhom/bottom-sheet
5. **Coach Chat** — le plus complexe (blur, drag, 3 types HITL)
6. **Séance du jour** — le plus complet (dual-accent, two-mode, realtime)

### Avant de coder

- [ ] Synchroniser `packages/design-tokens/` avec les valeurs canoniques identifiées (palette amber, lime, warm backgrounds)
- [ ] Décision sur le fond dark canonique (question 1)
- [ ] Vérifier que `react-native-reanimated` v3 est bien installé dans le workspace
- [ ] Vérifier que `@gorhom/bottom-sheet`, `expo-blur`, `react-native-svg` sont dans le monorepo

### Pattern critique à respecter

**Space Grotesk tabular sur TOUS les chiffres.** C'est la signature visuelle de l'app. Un chiffre proportionnel sur un metric card casse l'ensemble.

**Sémantique physiologique stricte.** Les couleurs green/yellow/red sont réservées Readiness/Strain/Sleep. Les utiliser sur un bouton ou une card non-physiologique est une violation visuelle majeure.

**@gorhom/bottom-sheet pour les drawers.** Modal transparent natif seul ne fonctionne pas correctement (see session log 2026-04-18: `onRequestClose` issue).
