# State — UI Mobile Rework
_2026-04-18 — chore/downgrade-sdk54_

## Current Goal
Gate Wave 1: tester Space Grotesk + FloatingLabelInput sur Expo Go SDK 54 physique.

## Plan Reference
`docs/ui-rework-plan.md` — plan complet.
`docs/ui-rework-diagnostic.md` — extraction visuelle.

## Plan Status

### Terminé ✅
- Commit 0: SPEC lime cleanup (todays session + homedashboard + UI-RULES)
- Commit 1: deps (@gorhom/bottom-sheet, expo-blur, draggable-flatlist, apple-auth)
- Commit 2: Space Grotesk fonts, physio tokens, zoneRed fix, tab bar 4 onglets
- W1-A: Text (Space Grotesk, toutes variantes, back-compat)
- W1-B: FloatingLabelInput (float label animé, border focus, error inline)
- W1-C/D/E/F: Button (4 variants), HeroNumber, ProgressSegments, SegmentedControl
- **SDK downgrade**: Expo SDK 55→54 (expo-router v4, expo-constants pinned, NativeTabs→Tabs)

### En attente (gate utilisateur)
**STOP — gate Wave 1**: utilisateur doit tester dans Expo Go SDK 54:
- `/_debug/text-showcase` → Space Grotesk + variantes hero + small-caps
- `/_debug/inputs-showcase` → float label + border focus + error state
Attendre "OK" avant Wave 2.

### À venir
- Wave 2: ReadinessRing, MetricStrip, SessionPrescriptionCard, DisciplineToggleRow, ObjectiveRadioRow, ConnectorRow, PhaseRow, ExerciseRow, CalendarGrid, WeeklyMetricStrip, TrainingListRow, ChatBubble, QuickReplyChip
- Wave 3: HITLSheet, DayDetailDrawer
- P1: Auth (login + signup + forgot-password)
- P2: Onboarding (5 étapes)
- P3: Home Dashboard (rework)
- P4: Training History
- P5: Coach Chat
- P6: Today's Session (Mode A + B)

## Décisions actées
- Lime supprimé — amber (#B8552E/#D97A52) pour TOUS les CTA
- Dark bg unifié #131210
- Space Grotesk uniquement (Inter retiré)
- 4 tabs: Accueil | Entraînement | Coach | Profil
- Check-in: route non-tab /check-in (hors tabs)
- Mode A→B: navigation push /session/live.tsx
- Auth erreurs: inline sous input
- zoneRed: #B64536 (terracotta, pas #ef4444 froid)
- SDK 54: NativeTabs remplacé par Tabs standard (NativeTabs = API SDK 55 only)
- SDK 54: react@19.2 + react-native@0.83.4 + reanimated@4.2.1 inchangés

## Open Issues
- Tests Wave 1 non écrits (Button/FloatingLabelInput/HeroNumber/ProgressSegments/SegmentedControl)
- Expo Go gate en attente — ne pas avancer Wave 2 sans "OK"
