# State — UI Mobile Rework
_2026-04-19 — chore/downgrade-sdk54_

## Current Goal
P1–P6 livrés. Branche chore/downgrade-sdk54 pushed. Prochains: tests Expo Go + décision suppression composants obsolètes.

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
- **P2 Onboarding**: 5 étapes, SegmentedControl variant="accent" — Signup → /onboarding → /(tabs)
- **Crash fix (Expo Go SDK 54)**: react-native-worklets Turbo Module absent du binaire. Suppression reanimated dans onboarding, remplacé par Animated.Value + translateX
- **P3 Home Dashboard**: Readiness ring 216px + MetricRow + CognitiveLoadDial + SessionCard + CTA check-in. Fix Inter_* → SpaceGrotesk_* dans Circle + SessionCard ✅
- **P4 Training History**: Calendrier (grille mois + discipline dots + nav) + Liste (semaines groupées + totaux) + Drawer détail jour (Modal slide-up, Durée/Charge/RPE/Distance). Stats semaine + delta vs S-1 ✅

- **P5 Coach Chat**: Conversation UI + HITL bottom sheet (3 types: single/multi/rank). Animated.Value spring + expo-blur BlurView. ✅
- **P6 Home Dashboard**: Rewrite complet. ReadinessRingHome 160px sémantique, MetricsStrip texte 3 cols, HomeSessionCard + CTA footer, CognitiveLoadBar 24 segments. Toggle DEV via tap avatar "SR". `colors.accentText`/`accentTextDark` ajoutés aux tokens. 0 hex inline. ✅
- **P6 Polish** (6 commits, tous poussés): ✅
  - Bug 1: ring value 72→52px (letterSpacing -2.5, lineHeight 58)
  - Bug 2: "Fatigue musculaire" numberOfLines={2}, plus de \n explicite
  - Bug 3: "CHARGE COGNITIVE" supprimé, "Charge allostatique" → foreground
  - Bug 4: week headers 2 lignes — L1 "SEMAINE DU X MOIS", L2 "N SÉANCES - Xh TOT. - Z CHARGE"
  - Bug 5: Rank drag PanResponder — GripDots ⋮⋮, translateY natif, swap multi-slot, Haptics Light/Medium
  - Bug 6: NativeTabs restauré (expo-router/unstable-native-tabs, SDK 54 OK, amber tintColor, SF Symbols)

### À venir
- **Tests Expo Go**: Valider P6 polish sur iPhone physique (6 bugs à valider)
- **Ajustement ring si besoin**: 52px = première itération, sous-commit 52-60px autorisé sans plan
- **Décision suppression**: MetricRow, SessionCard, CognitiveLoadDial, ReadinessStatusBadge (voir docs/p6-home-plan.md)
- **Today's Session (Mode A + B)**: route /session/live.tsx

## Décisions actées
- Lime supprimé — amber (#B8552E/#D97A52) pour TOUS les CTA
- Dark bg unifié #131210
- Space Grotesk uniquement (Inter retiré)
- 4 tabs: Accueil | Entraînement | Coach | Profil via NativeTabs (unstable-native-tabs, SDK 54 validé)
- NativeTabs API: `Label` et `Icon` = imports séparés, enfants de `NativeTabs.Trigger` (pas sous-composants)
- `calendar.fill` invalide en sf-symbols 2.2 → utiliser `calendar.circle.fill`
- Check-in: route non-tab /check-in
- Mode A→B: navigation push /session/live.tsx
- Auth erreurs: inline sous input (pas de toast)
- zoneRed: #B64536 (terracotta)
- @types/react maintenu à ~19.2.0 (19.1.x casse react-native-svg class types)

## Open Issues
- Tests Wave 1 non écrits (Button/FloatingLabelInput/HeroNumber/ProgressSegments/SegmentedControl)
- Apple Sign In stub (expo-apple-authentication non connecté)
- Auth screens pas connectées au backend (TODO dans handleLogin/handleSignup)
