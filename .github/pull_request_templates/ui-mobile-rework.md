## Résumé technique

Rework complet de l'app mobile Expo (SDK 54) depuis un scaffold Vague 1.
5 pages livrées et testées manuellement sur iPhone via Expo Go SDK 54.
Toutes les pages utilisent des mocks locaux — pas de wiring backend dans cette PR.
SDK downgrade 55→54 nécessaire pour compatibilité binaire Expo Go (reanimated worklets
absents du binaire SDK 54, remplacés par `Animated.Value` + `PanResponder`).

---

## Pages livrées ✅

| Page | Route | Notes |
|---|---|---|
| Auth | `/(auth)/login`, `/(auth)/signup`, `/(auth)/forgot-password` | FloatingLabelInput, Button Wave 1 |
| Onboarding | `/onboarding` | 5 étapes, slide `Animated.Value` |
| Home Dashboard | `/(tabs)/` | P6 rewrite, ReadinessRing 160px, MetricsStrip |
| Training History | `/(tabs)/training` | Calendrier + liste + drawer détail |
| Coach Chat | `/(tabs)/chat` | Conversation + HITL bottom sheet (single/multi/rank) |

## Pages placeholder (non bloquantes) 🚧

- Today's Session (`/session/live`) — route non créée
- Metric Detail (`/metric/[id]`)
- Nutrition Log (`/nutrition`)
- Profile / Settings (`/(tabs)/profile`) — scaffold vide
- Connectors (`/connectors`)

---

## Ce qui N'est PAS dans cette PR

- Wiring backend (mocks only — `apps/mobile/src/mocks/`)
- Authentification réelle (`handleLogin`/`handleSignup` = `// TODO: real auth call`)
- Apple Sign In (installé, non connecté)
- Connecteurs Strava / Hevy / Terra
- Tests unitaires composants Wave 1

---

## Checklist QA manuelle (Expo Go iPhone)

Avant merge, valider sur device physique iOS (iPhone + Expo Go SDK 54):

### Navigation
- [ ] Tab bar iOS liquid glass visible (NativeTabs, amber tintColor)
- [ ] Navigation Auth → Onboarding → Home fonctionnelle
- [ ] Back gesture iOS native opérationnel sur toutes les pages

### Home Dashboard
- [ ] Ring Readiness affiche valeur 78 (état normal)
- [ ] Tap avatar "SR" (dev toggle) → cycle 3 états: optimal / normal / récupération
- [ ] Ring couleur change (vert / amber / rouge) selon état
- [ ] MetricsStrip 3 colonnes visible, valeurs tabular-nums
- [ ] CTA "Voir la session" visible en footer

### Coach Chat
- [ ] Messages s'affichent correctement
- [ ] Input bar visible **au-dessus** du clavier quand ouvert, **au-dessus** des NativeTabs quand fermé
- [ ] HITL sheet s'ouvre par-dessus (BlurView backdrop)
- [ ] Type single: radio selection fonctionnel
- [ ] Type multi: checkbox multi-selection fonctionnel
- [ ] Type rank: drag PanResponder (grip dots ⋮⋮), swap avec haptics Light/Medium

### Training History
- [ ] Calendrier scroll mois (← →)
- [ ] Dots discipline colorés sur jours d'entraînement
- [ ] Tap jour → drawer slide-up avec détail session

### Auth
- [ ] Champs non cachés par le clavier
- [ ] Erreurs inline sous les inputs (pas de toast)

### Screenshots à attacher manuellement
> Attacher avant merge: Home (3 états readiness), Chat + HITL sheet ouverte, Training History

---

## Stack technique

- Expo SDK 54 / expo-router v3 / React Native 0.73.x
- NativeTabs: `expo-router/unstable-native-tabs` (iOS liquid glass, SDK 54 OK)
- Animations: `Animated.Value` + `PanResponder` (reanimated absent SDK 54 Expo Go)
- Fonts: Space Grotesk via `expo-font`
- Bottom sheets: `@gorhom/bottom-sheet` + `expo-blur`
- Tokens: `@resilio/design-tokens` (0 hex inline)
- Mocks: `apps/mobile/src/mocks/`
