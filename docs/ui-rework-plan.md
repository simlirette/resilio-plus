# UI Rework — Plan d'exécution
*2026-04-18 — Phase 1*

Référence: `docs/ui-rework-diagnostic.md`
Hiérarchie d'autorité: screenshots > SPEC.md > code source > tout le reste.

---

## Stratégie de validation visuelle

À chaque gate:
1. Tester dans Expo Go sur simulateur iOS (ou appareil physique)
2. Screenshot le rendu
3. Comparer côte-à-côte avec `docs/design/<page>/screenshots/`
4. Light mode puis dark mode
5. Lister les écarts mesurables (px, couleur, font weight)
6. Si écarts: sous-commits correctifs jusqu'à "OK"
7. Tag git `ui-rework-<item>-done` à la validation finale

---

## Commit 0 — Nettoyage SPEC + décisions (aucun code app)

**Objectif**: synchroniser les sources de vérité avec les décisions actées.

### Tâches

- [ ] `docs/design/todays session/SPEC.md`: retirer toutes mentions lime / `#C8FF4D` / `accentCTA` / `accentCTAInk`. Remplacer par amber (`#B8552E` light / `#D97A52` dark).
- [ ] `docs/design/homedashboard/SPEC.md`: corriger la tab bar — "Entraînement" remplace "Check-in". 5 onglets: Accueil | Entraînement | Coach | Métriques | Profil (icône).
- [ ] `frontend/UI-RULES.md`: retirer la section "Accent action session — Lime électrique" + supprimer `#C8FF4D` partout. Ajouter note "Système dual-accent abandonné — amber unique pour tous les CTA."
- [ ] Aucun autre fichier modifié dans ce commit.

**Commit**: `docs: remove lime accent — amber canonical for all CTAs`

---

## Commit 1 — Dépendances

**Objectif**: installer les 4 packages manquants.

```bash
pnpm add @gorhom/bottom-sheet expo-blur react-native-draggable-flatlist expo-apple-authentication --filter @resilio/mobile
```

Puis: `pnpm typecheck` sur `@resilio/mobile` doit passer.

**Commit**: `chore(mobile): add bottom-sheet, expo-blur, draggable-flatlist, apple-auth deps`

---

## Commit 2 — Fonts + Tokens + Tabs

**Objectif**: infrastructure de base correcte avant tout composant.

### 2a — Fonts

**`apps/mobile/app/_layout.tsx`**:
- Retirer imports `@expo-google-fonts/inter` et `@expo-google-fonts/space-mono`
- Ajouter imports `SpaceGrotesk_400Regular`, `SpaceGrotesk_500Medium`, `SpaceGrotesk_600SemiBold`, `SpaceGrotesk_700Bold` depuis `@expo-google-fonts/space-grotesk`
- Mettre à jour `useFonts({})` avec les 4 variantes Space Grotesk
- Retirer Inter et SpaceMono si non utilisés ailleurs

**`packages/design-tokens/src/typography.ts`**:
- `fontSans` → `"'Space Grotesk', -apple-system, system-ui, sans-serif"`
- Retirer `fontMono` si SpaceMono retiré
- Ajouter noms de police RN: `fontFamily: { regular: 'SpaceGrotesk_400Regular', medium: 'SpaceGrotesk_500Medium', semibold: 'SpaceGrotesk_600SemiBold', bold: 'SpaceGrotesk_700Bold' }`

### 2b — Tokens couleurs

**`packages/design-tokens/src/colors.ts`**:

Ajouter top-level:
```ts
accentDark: '#D97A52',  // amber dark mode

physio: {
  green:  { light: '#3F8A4A', dark: '#8FCB82' },
  yellow: { light: '#B8863A', dark: '#E8C86A' },  // light = amber réutilisé
  red:    { light: '#B64536', dark: '#E27A6F' },
},
```

Corriger:
```ts
zoneRed: '#B64536',        // était #ef4444 (rouge froid) → terracotta chaud cohérent
zoneRedBg: 'rgba(182,69,54,0.10)',
zoneRedRgb: '182, 69, 54',
```

Corriger `dark.background` si nécessaire (déjà `#131210` — OK).

### 2c — Tab bar

**`apps/mobile/app/(tabs)/_layout.tsx`**:
- Remplacer trigger `check-in` (SF `heart`/`heart.fill`) par `training` (SF `figure.run`/`figure.run` — ou `calendar`/`calendar.fill`)
- Ajouter trigger `metrics` (SF `chart.bar`/`chart.bar.fill`) si 5 tabs, sinon fusionner avec profil
- Décision simplifiée V1: 4 tabs — Accueil | Entraînement | Coach | Profil
- Créer fichier vide `apps/mobile/app/(tabs)/training.tsx` (placeholder)
- Supprimer ou rediriger `apps/mobile/app/(tabs)/check-in.tsx`

**`apps/mobile/app/(tabs)/index.tsx`**:
- Retirer `handleCheckin` et le CTA "Check-in quotidien" (pas un tab)
- Check-in est une action in-screen ou sera intégrée au profil plus tard

**Validation**: `pnpm typecheck` + app démarre dans Expo Go sans crash

**Commit**: `chore(mobile): Space Grotesk fonts, physio tokens, fix zoneRed, tab bar Training`

---

## Wave 1 — Primitives (composants partagés)

### W1-A — Text (refonte)

**Fichier**: `packages/ui-mobile/src/components/Text.tsx`

Ajouter/modifier:
- Variante `heroNumber`: 72–80px, `SpaceGrotesk_500Medium`, `fontVariant: ['tabular-nums']`, `letterSpacing: -2`
- Variante `heroLarge`: 40px, bold, tabular
- Variante `smallCaps`: 11px, medium, `textTransform: 'uppercase'`, `letterSpacing: 2`
- Variante `wordmark`: 17px, semibold, `letterSpacing: -0.3`
- Variante `caption`: 12–13px, regular
- S'assurer que `fontFamily` utilise les noms Space Grotesk dans tous les cas

Gate: créer `apps/mobile/app/_debug/text-showcase.tsx` qui affiche toutes les variantes en light + dark.
**→ STOP. Tester Expo Go. Attendre "OK".**

**Commit**: `feat(ui-mobile): Text variants with Space Grotesk — heroNumber, smallCaps, wordmark`

### W1-B — FloatingLabelInput

**Fichier**: `packages/ui-mobile/src/components/FloatingLabelInput.tsx`

Props: `label`, `value`, `onChangeText`, `secureTextEntry`, `keyboardType`, `autoComplete`, `autoCapitalize`, `error?`, `autoFocus?`

Comportement:
- Label flotte quand `value !== ''` ou focus — translateY + scale via reanimated `withTiming(150ms, ease-out)`
- Border: `1px neutral → 1.5px accent` au focus (marginCompensation: -0.5px)
- Icône œil toggle pour `secureTextEntry`
- Message d'erreur inline sous l'input (rouge terracotta `physio.red.light/dark`)
- Hauteur: 56px, radius: 10px

Gate: `apps/mobile/app/_debug/inputs-showcase.tsx` — états: vide, rempli, focus, erreur, password
**→ STOP. Tester Expo Go. Attendre "OK".**

**Commit**: `feat(ui-mobile): FloatingLabelInput with animated label and error state`

### W1-C — Button (extension)

**Fichier**: `packages/ui-mobile/src/components/Button.tsx`

Ajouter variantes:
- `ghost`: fond transparent, border accent, texte accent
- `apple`: fond noir/blanc selon mode, texte inverse, logo Apple (ne pas importer expo-apple-authentication dans ui-mobile — wrapper dans apps/mobile)

Modifier `primary`: s'assurer radius 12px, hauteur 54–56px, `fontVariant: ['tabular-nums']` non, mais `SpaceGrotesk_600SemiBold`.

Modifier `disabled`: opacité 0.4 (pas 0.2).

Gate: `apps/mobile/app/_debug/buttons-showcase.tsx`
**→ STOP. Tester Expo Go. Attendre "OK".**

**Commit**: `feat(ui-mobile): Button ghost + apple variants, radius 12, disabled opacity 0.4`

### W1-D — ProgressSegments

**Fichier**: `packages/ui-mobile/src/components/ProgressSegments.tsx`

Props: `total: number`, `current: number`

Comportement: `total` segments fins (hauteur 3px, gap 6px), couleur: accent si complété ou courant, neutral sinon. Pas de transition.

**Commit**: `feat(ui-mobile): ProgressSegments for onboarding`

### W1-E — SegmentedControl

**Fichier**: `packages/ui-mobile/src/components/SegmentedControl.tsx`

Props: `options: string[]`, `selected: number`, `onChange: (i: number) => void`

Style: fond surfaceAlt, segment actif fond surface blanc/foncé, radius 8–10px, texte 14px medium. Hauteur 36px.

Gate: inclure dans `_debug/inputs-showcase.tsx`

**Commit**: `feat(ui-mobile): SegmentedControl`

### W1-F — HeroNumber

**Fichier**: `packages/ui-mobile/src/components/HeroNumber.tsx`

Props: `value: string | number`, `unit?: string`, `size?: 'xl' | 'xxl'`, `color?: string`

`xl` = 40px bold tabular, `xxl` = 72–80px medium tabular tracking -2 à -3.

**Commit**: `feat(ui-mobile): HeroNumber`

---

## Wave 2 — Composés

### W2-A — ReadinessRing

**Fichier**: `packages/ui-mobile/src/components/ReadinessRing.tsx`

- SVG `Circle` de react-native-svg
- Arc 160px ⌀, épaisseur 10–12px, couleur selon score (<70 physioRed, 70–84 amber, ≥85 physioGreen)
- Animation montage: `stroke-dashoffset` de 0 à valeur, 600ms ease-out via reanimated
- Centre: `HeroNumber` (72px) + label "READINESS" smallCaps + delta "+X vs hier" sémantique

Gate: `apps/mobile/app/_debug/readiness-ring.tsx` — 3 états (45, 78, 92), light + dark
**→ STOP. Tester Expo Go. Attendre "OK".**

**Commit**: `feat(ui-mobile): ReadinessRing SVG animated arc with semantic color`

### W2-B — MetricStrip

**Fichier**: `packages/ui-mobile/src/components/MetricStrip.tsx`

3 colonnes égales séparées par hairline verticale. Props: `nutrition`, `strain`, `sleep` (valeurs + états).
- Nutrition: `X / Y kcal` + barre progression
- Strain: chiffre + "Fatigue musculaire" (couleur sémantique)
- Sommeil: "Xh XX" + "Score XX"

**Commit**: `feat(ui-mobile): MetricStrip 3-column`

### W2-C — SessionPrescriptionCard

**Fichier**: `packages/ui-mobile/src/components/SessionPrescriptionCard.tsx`

Card Home Dashboard: label "SÉANCE DU JOUR", titre 22px, durée, description, métriques secondaires (3 colonnes), CTA "Démarrer la séance →" pleine largeur amber.

**Commit**: `feat(ui-mobile): SessionPrescriptionCard for home dashboard`

### W2-D — DisciplineToggleRow

**Fichier**: `packages/ui-mobile/src/components/DisciplineToggleRow.tsx`

Row 64px: icône monoline + label + sous-label + checkmark accent (si sélectionné). Fond accentSoft si sélectionné.

**Commit**: `feat(ui-mobile): DisciplineToggleRow for onboarding`

### W2-E — ObjectiveRadioRow

**Fichier**: `packages/ui-mobile/src/components/ObjectiveRadioRow.tsx`

Row: bullet radio outline/plein + label 16px. Fond accentSoft si sélectionné.

**Commit**: `feat(ui-mobile): ObjectiveRadioRow for onboarding`

### W2-F — ConnectorRow

**Fichier**: `packages/ui-mobile/src/components/ConnectorRow.tsx`

Row: icône + nom + dot statut (vert/neutre) + bouton "Connecter"/"Déconnecter".

**Commit**: `feat(ui-mobile): ConnectorRow for onboarding`

### W2-G — PhaseRow + ExerciseRow

**Fichiers**: `PhaseRow.tsx`, `ExerciseRow.tsx`

- PhaseRow: label phase (WARM-UP/MAIN/COOL-DOWN) + allure + durée
- ExerciseRow: numéro + nom + sets×reps@RPE + note technique

**Commit**: `feat(ui-mobile): PhaseRow and ExerciseRow for session prescription`

### W2-H — CalendarGrid

**Fichier**: `packages/ui-mobile/src/components/CalendarGrid.tsx`

Grille 7 colonnes × N semaines. Props: `month`, `year`, `sessions: SessionDot[]`, `selected?: Date`, `onDayPress`.
- Discipline marks (composant interne): disque plein / mi-gris / outline / demi-disque (≤3 dots par jour)
- Jour sélectionné: border accent
- Aujourd'hui: border neutre

**Commit**: `feat(ui-mobile): CalendarGrid with discipline marks`

### W2-I — WeeklyMetricStrip

**Fichier**: `packages/ui-mobile/src/components/WeeklyMetricStrip.tsx`

Identique MetricStrip mais valeurs: Séances / Volume / Charge + delta "↑+X vs 7j".

**Commit**: `feat(ui-mobile): WeeklyMetricStrip for training history`

### W2-J — TrainingListRow

**Fichier**: `packages/ui-mobile/src/components/TrainingListRow.tsx`

Row: [jour+date] [icône discipline] [titre+type] [durée+charge].

**Commit**: `feat(ui-mobile): TrainingListRow`

### W2-K — ChatBubble + QuickReplyChip

**Fichiers**: `ChatBubble.tsx`, `QuickReplyChip.tsx`

- ChatBubble: coach (gauche, surfaceMuted, avatar HC) / user (droite, userBubble). radius 18px, coin spécifique 4px.
- QuickReplyChip: ghost border, 34px, radius 17px, 13px

**Commit**: `feat(ui-mobile): ChatBubble and QuickReplyChip`

---

## Wave 3 — Complexes

### W3-A — HITLSheet

**Fichier**: `packages/ui-mobile/src/components/HITLSheet.tsx`

- @gorhom/bottom-sheet, snap [0.6, 0.95]
- Backdrop: expo-blur `intensity=20` + dim overlay
- Header: question text + compteur X/Y + bouton ×
- Body: switch sur type (SingleChoice | MultiChoice | Order)
- SingleChoiceOption, CheckboxOption, DraggableOption comme composants internes
- Footer: Passer + bouton → cercle

Gate: `apps/mobile/app/_debug/hitl-sheet.tsx` — 3 types, light + dark
**→ STOP. Tester Expo Go. Attendre "OK".**

**Commit**: `feat(ui-mobile): HITLSheet with 3 HITL question types`

### W3-B — DayDetailDrawer

**Fichier**: `packages/ui-mobile/src/components/DayDetailDrawer.tsx`

- @gorhom/bottom-sheet, snap [0.5, 0.9]
- Handle bar + titre date + métriques jour + cards séances (DaySessionCard interne)

**Commit**: `feat(ui-mobile): DayDetailDrawer for training history`

---

## Pages — Implémentation

### P1 — Auth

**Route**: `apps/mobile/app/(auth)/login.tsx` (réécrire), `signup.tsx` (créer), `forgot-password.tsx` (créer)

Fichiers à créer/modifier:
- `app/(auth)/login.tsx` — refonte complète selon SPEC
- `app/(auth)/signup.tsx` — nouveau
- `app/(auth)/forgot-password.tsx` — nouveau
- `app/(auth)/_layout.tsx` — Stack header masqué, bg canonique

Navigation:
- Login → Signup → Forgot-password (liens footer)
- Forgot-password post-submit: inline (pas de navigation)
- Login succès → `/(tabs)`

**Validation**: screenshot login (empty, filled, focus, loading) + signup + forgot-password, light + dark
**→ STOP. Comparer avec `docs/design/flow auth/screenshots/`.**

**Tag**: `git tag ui-rework-auth-done`

**Commit**: `feat(mobile): auth screens pixel-perfect — login, signup, forgot-password`

---

### P2 — Onboarding

**Route**: `apps/mobile/app/onboarding/index.tsx` (gestionnaire d'état + animations) + steps internes

Fichiers:
- `app/onboarding/index.tsx` — state machine: currentStep 0–4, slide animation
- `app/onboarding/_layout.tsx`

Câblage navigation: après étape 5 → `/(tabs)` (replace)

**Validation**: toutes les étapes, light + dark, transition slide, CTA disabled états
**→ STOP. Comparer avec `docs/design/onboarding/screenshots/`.**

**Tag**: `git tag ui-rework-onboarding-done`

**Commit**: `feat(mobile): onboarding 5-step flow with slide transitions`

---

### P3 — Home Dashboard

**Route**: `apps/mobile/app/(tabs)/index.tsx` (réécrire)

Changements vs état actuel:
- Remplacer `Circle` + `ReadinessStatusBadge` par `ReadinessRing` (SVG animé)
- Remplacer `MetricRow` par `MetricStrip`
- Remplacer `SessionCard` par `SessionPrescriptionCard`
- Supprimer `CognitiveLoadDial` (absent du SPEC homedashboard — hors scope V1)
- Supprimer CTA "Check-in quotidien"
- Header: greeting 28px/700 + date 13px small-caps + avatar cercle 36px
- ScrollView avec `contentContainerStyle` pb = safeInsets.bottom + 80px (tab bar)

**Validation**: 3 états Readiness (45/78/92), light + dark, anneau animé
**→ STOP. Comparer avec `docs/design/homedashboard/screenshots/`.**

**Tag**: `git tag ui-rework-home-done`

**Commit**: `feat(mobile): home dashboard pixel-perfect — readiness ring, metrics, session card`

---

### P4 — Training History

**Route**: `apps/mobile/app/(tabs)/training.tsx`

Fichiers:
- `app/(tabs)/training.tsx` — écran principal
- State: `view: 'calendar' | 'list'`, `selectedMonth`, `selectedDay`

Structure:
- Header: titre "Entraînement" + icône filtre (placeholder)
- SegmentedControl: Calendrier | Liste
- WeeklyMetricStrip
- Vue conditionnelle: CalendarGrid | SectionList
- DayDetailDrawer (visible si jour sélectionné avec séances)

**Validation**: vue calendrier, vue liste, tap jour → drawer, light + dark
**→ STOP. Comparer avec `docs/design/training historycalendar/screenshots/`.**

**Tag**: `git tag ui-rework-training-done`

**Commit**: `feat(mobile): training history — calendar + list + day drawer`

---

### P5 — Coach Chat

**Route**: `apps/mobile/app/(tabs)/chat.tsx` (réécrire)

Fichiers:
- `app/(tabs)/chat.tsx` — écran chat
- Mocks: 5 bulles coach + 1 bulle utilisateur + quick replies

Structure:
- Header: retour + "Head Coach" + menu
- FlatList bulles (inverted)
- Quick replies ScrollView horizontal
- Input bar (KeyboardAvoidingView)
- HITLSheet (conditionnelle, visible si questions actives)

**Validation**: conversation, sheet type 1 + 2 + 3, blur backdrop, light + dark
**→ STOP. Comparer avec `docs/design/coach chat/screenshots/`.**

**Tag**: `git tag ui-rework-chat-done`

**Commit**: `feat(mobile): coach chat with HITL sheet — 3 question types`

---

### P6 — Today's Session

**Routes**: `apps/mobile/app/session/index.tsx` (Mode A) + `apps/mobile/app/session/live.tsx` (Mode B)

Fichiers:
- `app/session/_layout.tsx`
- `app/session/index.tsx` — Mode A Prescription
- `app/session/live.tsx` — Mode B Exécution (Course ou Muscu selon prop)

Mode A:
- Header commun (date + titre + retour + menu)
- Titre séance 28px + métriques header 3 col
- Bloc "Pourquoi cette séance" (card surfaceAlt)
- Liste phases (course) ou exercices (muscu)
- Profil de zone (course — SVG bar)
- CTA "Démarrer" amber pleine largeur → `router.push('/session/live')`

Mode B course:
- Phase + progression small-caps
- HeroNumber pace 80px
- Fenêtre allure
- Métriques live 2 colonnes (couleur sémantique)
- Bloc courant / restant / suivant
- CTA "Terminer" ghost + pause

Mode B muscu:
- Header + progression exercice
- Nom exercice 28px
- Détail sets×reps@RPE
- Set selector (cercles)
- HeroNumber charge + reps
- RPE selector 1–10
- Countdown repos (setInterval + display)
- CTA "Set terminé" amber → prochain set

**Validation**: Mode A course + muscu, Mode B course + muscu, light + dark
**→ STOP. Comparer avec `docs/design/todays session/screenshots/`.**

**Tag**: `git tag ui-rework-session-done`

**Commit**: `feat(mobile): today's session — prescription and live execution modes`

---

## Phase 3 — Vérification finale

**Après P6 validé:**

```bash
# Re-grep couleurs obsolètes
grep -r '#5b5fef\|#3B74C9\|#C8FF4D\|#0E1200\|sienna\|#08080e' apps/mobile packages/ui-mobile packages/design-tokens

# Re-grep hex en dur dans composants (hors design-tokens)
grep -rn '#[0-9a-fA-F]\{6\}' packages/ui-mobile/src/components/ apps/mobile/app/

# Typecheck complet
pnpm --filter @resilio/mobile typecheck
pnpm --filter @resilio/ui-mobile typecheck
pnpm --filter @resilio/design-tokens typecheck
```

**Objectifs**: 0 couleur obsolète, hex justifiés uniquement (hairlines rgba ou couleurs physio directement utilisées), 0 erreur TS.

**Navigation**: testable de bout en bout — login → tabs → training history → session → chat.

**Light + dark**: chaque page validée dans les deux modes.

**Produce**: `docs/ui-rework-final-report.md`

---

## Ordre global des commits

```
commit-0   docs: remove lime accent — amber canonical for all CTAs
commit-1   chore(mobile): deps — bottom-sheet, expo-blur, draggable-flatlist, apple-auth
commit-2   chore(mobile): Space Grotesk, physio tokens, fix zoneRed, tab bar Training
W1-A       feat(ui-mobile): Text variants with Space Grotesk
W1-B       feat(ui-mobile): FloatingLabelInput animated
W1-C       feat(ui-mobile): Button ghost + apple variants
W1-D       feat(ui-mobile): ProgressSegments
W1-E       feat(ui-mobile): SegmentedControl
W1-F       feat(ui-mobile): HeroNumber
W2-A       feat(ui-mobile): ReadinessRing SVG animated
W2-B       feat(ui-mobile): MetricStrip
W2-C       feat(ui-mobile): SessionPrescriptionCard
W2-D       feat(ui-mobile): DisciplineToggleRow
W2-E       feat(ui-mobile): ObjectiveRadioRow
W2-F       feat(ui-mobile): ConnectorRow
W2-G       feat(ui-mobile): PhaseRow + ExerciseRow
W2-H       feat(ui-mobile): CalendarGrid
W2-I       feat(ui-mobile): WeeklyMetricStrip
W2-J       feat(ui-mobile): TrainingListRow
W2-K       feat(ui-mobile): ChatBubble + QuickReplyChip
W3-A       feat(ui-mobile): HITLSheet
W3-B       feat(ui-mobile): DayDetailDrawer
P1         feat(mobile): auth screens pixel-perfect          [tag: ui-rework-auth-done]
P2         feat(mobile): onboarding 5-step flow              [tag: ui-rework-onboarding-done]
P3         feat(mobile): home dashboard pixel-perfect        [tag: ui-rework-home-done]
P4         feat(mobile): training history                    [tag: ui-rework-training-done]
P5         feat(mobile): coach chat + HITL sheet             [tag: ui-rework-chat-done]
P6         feat(mobile): today's session                     [tag: ui-rework-session-done]
```

---

## Notes d'implémentation critiques

1. **Chaque chiffre physio** = `fontVariant: ['tabular-nums']` + `SpaceGrotesk_500Medium` minimum
2. **Chaque border fine** = `StyleSheet.hairlineWidth` (≈ 0.5px sur @3x)
3. **Chaque CTA primaire** = `expo-haptics ImpactFeedbackStyle.Medium` (Heavy pour "Démarrer")
4. **Chaque écran avec input** = `KeyboardAvoidingView behavior="padding"` iOS
5. **Chaque bottom** = `useSafeAreaInsets().bottom + 16` minimum
6. **Aucun hex en dur dans les composants** — tout via `@resilio/design-tokens`
7. **Jamais Modal transparent pour les drawers** — @gorhom/bottom-sheet uniquement
