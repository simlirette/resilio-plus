# State — UI Mobile Rework
_2026-04-19 — chore/downgrade-sdk54_

## Current Goal
P1 Auth livré. Prochain: P3 Home Dashboard rework OU P2 Onboarding.

## Plan Reference
`docs/ui-rework-plan.md` — plan complet.
`docs/ui-rework-diagnostic.md` — extraction visuelle.

## Plan Status

### Terminé ✅
- Commit 0: SPEC lime cleanup
- Commit 1: deps (@gorhom/bottom-sheet, expo-blur, draggable-flatlist, apple-auth)
- Commit 2: Space Grotesk fonts, physio tokens, zoneRed fix, tab bar 4 onglets
- W1-A: Text (Space Grotesk, toutes variantes, back-compat)
- W1-B: FloatingLabelInput (float label animé, border focus, error inline)
- W1-C/D/E/F: Button (4 variants), HeroNumber, ProgressSegments, SegmentedControl
- **SDK downgrade**: Expo SDK 55→54 (expo-router v6, RN 0.81.5, expo-constants pinned)
- **P1 Auth**: login + signup + forgot-password (FloatingLabelInput + Button Wave 1)
  - Gate Wave 1 passé: app tourne sur iPhone ✅

### À venir
- Wave 2: ReadinessRing, MetricStrip, SessionPrescriptionCard, DisciplineToggleRow, ObjectiveRadioRow, ConnectorRow, PhaseRow, ExerciseRow, CalendarGrid, WeeklyMetricStrip, TrainingListRow, ChatBubble, QuickReplyChip
- Wave 3: HITLSheet, DayDetailDrawer
- **P2**: Onboarding (5 étapes)
- **P3**: Home Dashboard (rework)
- **P4**: Training History
- **P5**: Coach Chat
- **P6**: Today's Session (Mode A + B)

## Décisions actées
- Lime supprimé — amber (#B8552E/#D97A52) pour TOUS les CTA
- Dark bg unifié #131210
- Space Grotesk uniquement (Inter retiré)
- 4 tabs: Accueil | Entraînement | Coach | Profil
- Check-in: route non-tab /check-in
- Mode A→B: navigation push /session/live.tsx
- Auth erreurs: inline sous input (pas de toast)
- zoneRed: #B64536 (terracotta)
- SDK 54: NativeTabs → Tabs standard, react-native 0.81.5, expo-router v6
- @types/react maintenu à ~19.2.0 (19.1.x casse react-native-svg class types)

## Open Issues
- Tests Wave 1 non écrits (Button/FloatingLabelInput/HeroNumber/ProgressSegments/SegmentedControl)
- Apple Sign In stub (expo-apple-authentication non connecté)
- Auth screens pas connectées au backend (TODO dans handleLogin/handleSignup)
