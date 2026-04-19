# Changelog

## 2026-04 — UI Mobile Rework P1–P6 (chore/downgrade-sdk54)

### Pages livrées (5/10)
- **P1 Auth**: Login, Signup, Forgot-password — FloatingLabelInput, Button Wave 1
- **P2 Onboarding**: 5 étapes avec slide animation (Animated.Value, pas reanimated), SegmentedControl variant="accent"
- **P4 Training History**: Calendrier grille-mois + discipline dots, liste semaines groupées, drawer détail jour (durée/charge/RPE/distance)
- **P5 Coach Chat**: Conversation UI + HITL bottom sheet (3 types: single/multi/rank), BlurView backdrop, PanResponder drag-and-drop
- **P6 Home Dashboard** (rewrite complet): ReadinessRingHome 160px sémantique, MetricsStrip 3 cols tabular-nums, HomeSessionCard + CTA footer, CognitiveLoadBar 24 segments, toggle DEV via tap avatar "SR"

### Placeholders restants (5/10) — non bloquants pour merge
- **Today's Session** (`/session/live`) — route non créée, listée sous "À venir" dans state.md
- **Metric Detail** (`/metric/[id]`)
- **Nutrition Log** (`/nutrition`)
- **Profile / Settings** (`/profile`) — scaffold vide
- **Connectors** (`/connectors`)

### Ce qui N'est PAS inclus dans cette PR
- Wiring backend (toutes les pages utilisent des mocks locaux dans `apps/mobile/src/mocks/`)
- Connecteurs réels (Strava OAuth, Hevy, Terra)
- Authentification réelle (`handleLogin`/`handleSignup` contiennent des `// TODO: real auth call`)
- Apple Sign In (`expo-apple-authentication` installé, non connecté)
- Tests unitaires composants Wave 1 (Button, FloatingLabelInput, HeroNumber, ProgressSegments, SegmentedControl)

### Stack technique confirmée
- **Expo SDK 54** — downgrade depuis SDK 55 pour compatibilité Expo Go (binaire SDK 54 sans reanimated worklets Turbo Module)
- **expo-router v3** — file-based routing, `/(tabs)/` layout
- **NativeTabs** via `expo-router/unstable-native-tabs` — iOS liquid glass tab bar, SDK 54 OK
- **Animations**: `Animated.Value` + `PanResponder` (reanimated worklets absents du binaire Expo Go SDK 54)
- **Space Grotesk** exclusivement via `expo-font` (Inter retiré)
- **Accent**: Amber/terracotta `#B8552E` light / `#D97A52` dark
- **Mocks**: `apps/mobile/src/mocks/`
- **Tokens**: `@resilio/design-tokens` — 0 hex inline dans les composants

### Contraintes techniques à retenir
- `react-native-draggable-flatlist` v4 **incompatible** Expo Go SDK 54 (dépend reanimated worklets) — utiliser PanResponder
- `calendar.fill` invalide en SF Symbols 2.2 — utiliser `calendar.circle.fill`
- `@types/react` maintenu à `~19.2.0` (19.1.x casse `react-native-svg` class types)
- `NativeTabs.Trigger.Label` / `.Icon` ne sont PAS des sous-composants — imports séparés de `expo-router/unstable-native-tabs`
