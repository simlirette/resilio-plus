# UI Rework — Diagnostic
*2026-04-18 — Phase 1*

## Décisions architecturales (levées en Phase 0)

| Sujet | Décision |
|---|---|
| Accent couleur | Amber unique — `#B8552E` light / `#D97A52` dark. Lime supprimé définitivement. |
| Fond dark | Unifié `#131210` pour toutes les pages en V1. |
| Font | Space Grotesk (400/500/600/700) uniquement. Retirer Inter. |
| Transition Mode A→B | Navigation RN push vers route `session/live.tsx`. |
| Home scroll | ScrollView. |
| Auth erreurs | Inline sous l'input concerné. Pas de toast. |
| Mode A→B | Route dédiée. |

---

## 1. Extraction visuelle par page

### 1.1 Flow Auth (login / signup / forgot-password)

**Palette**

| Token | Light | Dark |
|---|---|---|
| bg | `#F5F5F2` | `#17171A` (→ token `#131210` choisi) |
| surface input | transparent | transparent |
| border | `#E3E0D8` | `#2E2D2A` |
| borderFocus | accent | accent |
| accent | `#B8552E` | `#D97A52` |
| text | `#1A1A17` | `#F0EEE8` |
| textSec | `#6B6862` | `#9E9A90` |
| textMuted | `#9A968D` | `#6B6862` |
| onAccent | `#FAFAF7` | `#17171A` |
| Apple btn | `#000000` bg | `#FFFFFF` bg |
| divider | `#E8E6E0` | `#262523` |

**Typo**

| Élément | Size | Weight | Notes |
|---|---|---|---|
| Wordmark "Resilio+" | 17px | 600 | tracking -0.3, "+" en accent |
| Titre h1 | 32px | 700 | tracking -0.5, aligné gauche |
| Floating label | 11px | 500 | uppercase, tracking +0.14em |
| Placeholder | 15px | 400 | textMuted |
| CTA | 16px | 600 | — |
| Lien "Mot de passe oublié" | 14px | 500 | accent |
| Footer lien | 14px | 400 | accent |
| Légal signup | 12px | 400 | textMuted, liens soulignés |

**Spacing**

- Padding horizontal: 24px
- Gap entre inputs: 14px
- Hauteur input: 56px, radius 10px
- Hauteur CTA: 54px, radius 12px
- Footer ancré bas (flex-grow sur espace intermédiaire)

**Comportements**
- Floating label: translateY + scale (150ms ease-out via reanimated)
- Border: 1px → 1.5px accent au focus (compensé -0.5px margin)
- Apple Sign In: couleur inverse selon le mode
- Forgot Password post-submit: bloc confirmation inline (pas modal), input email disparaît
- CTA loading: spinner centré sur fond accent (pas de texte)
- Auto-focus email au montage (login)

---

### 1.2 Onboarding (5 étapes)

**Palette**

| Token | Light | Dark |
|---|---|---|
| bg | `#F5F5F2` | `#17161A` (→ `#131210`) |
| surface | `#FFFFFF` | `#201E23` |
| surfaceAlt | `#FAFAF7` | `#26232A` |
| border | `#E2E0DB` | border dark |
| accent | `#B8552E` | `#D97A52` |
| accentSoft | `rgba(184,85,46,0.10)` | `rgba(217,122,82,0.14)` |
| accentText | `#FFFFFF` | `#131210` |

**Typo**

| Élément | Size | Weight |
|---|---|---|
| Label étape small-caps | 11px | 500 |
| Titre étape | 26–28px | 700 |
| Sous-titre | 15px | 400 |
| Item discipline/objectif | 16px / 13px | 600 / 400 |
| CTA | 16px | 600 |

**Spacing**
- Padding horizontal: 20px
- Hauteur item discipline: 64px
- Hauteur CTA: 54px, radius 12px, fixé bas
- Séparateurs: hairline 1px (pas de gap entre rows)

**Comportements**
- Progress: 5 segments fins, swap instantané (pas de transition animée)
- Transition entre étapes: slide horizontal translateX via reanimated
- Étape 01 Profil: KeyboardAvoidingView + ScrollView
- Étape 02 Sports: tap toggle, CTA disabled si 0 sélectionné
- Étape 03 Niveau: segmented 4 niveaux par discipline
- Étape 04 Objectif: radio, un seul choix, CTA disabled si aucun
- Étape 05 Connecteurs: bouton "Passer" uniquement sur cet écran

---

### 1.3 Home Dashboard

**Palette**

| Token | Light | Dark |
|---|---|---|
| bg | `#F5F5F2` | `#161412` (→ `#131210`) |
| surface | `#FAFAF7` | `#1F1D1A` |
| surfaceAlt | `#EFEEE9` | `#282622` |
| accent | `#B8552E` | `#D97A52` |
| physioGreen | `#3F8A4A` | `#8FCB82` |
| physioYellow | amber réutilisé | `#E8C86A` |
| physioRed | `#B64536` | `#E27A6F` |

**Typo**

| Élément | Size | Weight |
|---|---|---|
| Salutation | 28px | 700 |
| Date | 13px | 500 — uppercase, tracking +0.12em |
| Hero readiness | ~72px | 500 — tabular, tracking -2px |
| Label "READINESS" | 11px | 500 — small-caps |
| Delta "+X vs hier" | 13px | 500 — tabular, sémantique |
| Metric values | 17px | 500/600 — tabular |
| Session title | 22px | 700 — tracking -0.3 |
| Session duration | 22px | 400 — tabular |
| CTA "Démarrer" | 16px | 600 |

**Structure**
1. Status bar → Header (greeting + date + avatar) → Ring readiness (160px ⌀, arc 10–12px) → Metrics strip 3 col → Card séance → [Tab bar]
2. ScrollView, pas de hauteur fixe
3. Ring arc animé au montage: 0→valeur, 600ms ease-out, stroke-dashoffset via reanimated + react-native-svg

**Tab bar design** (corrigé): Accueil | Entraînement | Coach | Métriques + icône Profil (5e)

---

### 1.4 Today's Session

**Palette** — Dual-accent SUPPRIMÉ. Amber pour tout.

| Token | Light | Dark |
|---|---|---|
| bg | `#F5F3EE` | `#141311` (→ `#131210`) |
| bgElev | `#FFFFFF` | `#1C1B18` |
| bgElev2 | `#EDEAE2` | `#242320` |
| hairline | `rgba(26,22,16,0.08)` | `rgba(255,248,230,0.08)` |
| ink | `#181613` | `#F3EFE6` |
| accentCTA | `#B8552E` | `#D97A52` — amber, pas lime |
| physioGreen | `#3F8A4A` | `#8FCB82` |
| physioRed | `#B64536` | `#E27A6F` |

**Mode A — Prescription**

| Élément | Size | Weight |
|---|---|---|
| Titre séance | 28px | 700 — tracking -0.5 |
| Header metric values | 17px | 500 — tabular |
| Justif. coach | 14px | 400 |
| Phase label | 15px | 600 |
| Phase détail | 13px | 400 |
| CTA "Démarrer" | 16px | 600 — amber, radius 14px, 56px hauteur |

**Mode B — Exécution (Course)**

| Élément | Size | Weight |
|---|---|---|
| Hero pace | ~80px | 700 — tabular, tracking -3 |
| Fenêtre | 13px | 400 — textMuted |
| Métriques live | 17px | 500/600 — tabular |

**Mode B — Exécution (Muscu)**

| Élément | Size | Weight |
|---|---|---|
| Nom exercice | 28px | 700 |
| Hero charge/reps | 40px | 700 — tabular |
| CTA "Set terminé" | 16px | 600 — amber, pas lime |
| Countdown repos | 17–20px | 600 — tabular |

**Transition**: Mode A → Mode B = navigation push vers `session/live.tsx`. Pas de SharedTransition V1.

---

### 1.5 Training History / Calendar

**Palette**

| Token | Light | Dark |
|---|---|---|
| bg | `#F5F5F2` | `#1C1A17` (→ `#131210`) |
| surface | `#FAFAF7` | `#242220` |
| surface2 | `#EDECE6` | `#2B2926` |
| accent | `#A85A2F` | `#D98E5E` (≈ amber) |
| physioGreen | `#4F7A43` | `#7FAD6B` |
| physioRed | `#9C4A32` | `#C47A5A` |
| physioYellow | `#A68A2E` | `#D4B34D` |

**Discipline marks (encodage par valeur)**

| Discipline | Glyph |
|---|---|
| Course | disque plein sombre |
| Musculation | disque plein mi-gris |
| Vélo | cercle outline |
| Natation | demi-disque |

**Comportements**
- Segmented Calendrier/Liste: swap contenu
- Navigation mois: slide horizontal via reanimated
- Tap jour → drawer bottom sheet (@gorhom, snap 50%+90%)
- SectionList pour la liste (groupé par semaine)
- Jour sans séance: tap sans effet (pas de drawer vide)

---

### 1.6 Coach Chat + HITL Sheet

**Palette**

| Token | Light | Dark |
|---|---|---|
| bg | `#F5F5F2` | `#1A1715` (→ `#131210`) |
| surface | `#FFFFFF` | `#26231F` |
| surfaceMuted | `#EDEBE5` | `#2C2824` |
| surfaceSubtle | `#E8E5DE` | `#332E29` |
| accent | `#B8552E` | `#D97A52` |
| userBubble | surface light | `#3A3530` dark |
| online | `#3C9A5F` | `#4FB874` |

**Bulle coach**: radius 18px, coin bas-gauche 4px, fond surfaceMuted, avatar "HC" 26px
**Bulle user**: radius 18px, coin bas-droit 4px, fond userBubble, alignée droite

**HITL Sheet**
- Backdrop: expo-blur BlurView (`intensity=20`) + dim overlay `rgba(0,0,0,0.5)`
- Sheet: @gorhom/bottom-sheet, snap 60%–95%
- Header: question 18px/700/tracking -0.3 + compteur "X/Y" + bouton ×
- Footer: "Passer" gauche + bouton → cercle 44px accent droite
- Type 1 (choix unique): rows numérotés, pill 28px, flèche → sur sélection
- Type 2 (multi): checkboxes 22px, radius 6px, fond accent coché
- Type 3 (ordre): react-native-draggable-flatlist, handle ⋮⋮ droite

**Comportements**
- Sheet ouverture: slide-up 300ms spring
- Transition entre questions: slide horizontal X
- Checkbox check: scale bounce 200ms

---

## 2. Gaps web → React Native

| Problème web | Solution RN |
|---|---|
| CSS transitions floating label | `withTiming(translateY, {duration:150})` + `withTiming(fontSize, ...)` via reanimated |
| `backdrop-filter: blur` | `expo-blur` `BlurView` sur un `View` positionné en absolue |
| HTML drag (réordonnage HITL) | `react-native-draggable-flatlist` — longPress + handle |
| `position: sticky` header mois | `SectionList` `renderSectionHeader` + `stickySectionHeadersEnabled` |
| SVG arc/anneau readiness | `react-native-svg` `Circle` + `stroke-dashoffset` animé |
| `border-bottom` hairline | `StyleSheet.hairlineWidth` ou `1 / PixelRatio.get()` |
| Modals / drawers | `@gorhom/bottom-sheet` — jamais Modal transparent seul |
| Safe area CSS | `react-native-safe-area-context` `useSafeAreaInsets()` |
| Keyboard push layout | `KeyboardAvoidingView behavior="padding"` iOS uniquement |
| Clavier dismiss on tap | `ScrollView keyboardShouldPersistTaps="handled"` |
| `font-feature-settings: tnum` | `fontVariant: ['tabular-nums']` sur chaque `Text` numérique |
| CSS `transform: translateX` animation | `SharedValue` + `useAnimatedStyle` + `withTiming` |
| Segmented control | Composant custom avec `Pressable` + border + fond conditionnel |
| Apple Sign In bouton | `expo-apple-authentication` `AppleAuthenticationButton` |

---

## 3. Composants partagés — Classement par wave

### Wave 1 — Primitives (aucune dépendance composant)

| Composant | Fichier cible | Description |
|---|---|---|
| `SpaceGroteskText` | `packages/ui-mobile/src/components/Text.tsx` | Refonte de l'existant — variantes + tabular + small-caps |
| `FloatingLabelInput` | `packages/ui-mobile/src/components/FloatingLabelInput.tsx` | Input animé floating label, border focus accent |
| `Button` | (existant, étendre) | Ajouter variantes: ghost, apple-sign-in |
| `ProgressSegments` | `packages/ui-mobile/src/components/ProgressSegments.tsx` | Barre de progression en segments fins |
| `SegmentedControl` | `packages/ui-mobile/src/components/SegmentedControl.tsx` | Segmented control 2–4 segments |
| `HeroNumber` | `packages/ui-mobile/src/components/HeroNumber.tsx` | Affichage grand chiffre tabular + unité + tracking |
| `SmallCapsLabel` | (variante de Text) | Label 11px uppercase tabular — extrait si répétitif |

### Wave 2 — Composés (utilise Wave 1 + libs)

| Composant | Fichier cible | Description |
|---|---|---|
| `ReadinessRing` | `packages/ui-mobile/src/components/ReadinessRing.tsx` | SVG arc animé, couleur sémantique, hero number centre |
| `MetricStrip` | `packages/ui-mobile/src/components/MetricStrip.tsx` | 3 colonnes métriques avec séparateurs hairline |
| `DisciplineToggleRow` | `packages/ui-mobile/src/components/DisciplineToggleRow.tsx` | Row discipline avec icône monoline + toggle |
| `ObjectiveRadioRow` | `packages/ui-mobile/src/components/ObjectiveRadioRow.tsx` | Row radio objectif avec fond accentSoft si sélectionné |
| `ConnectorRow` | `packages/ui-mobile/src/components/ConnectorRow.tsx` | Row connecteur avec statut + bouton |
| `PhaseRow` | `packages/ui-mobile/src/components/PhaseRow.tsx` | Row phase de séance course |
| `ExerciseRow` | `packages/ui-mobile/src/components/ExerciseRow.tsx` | Row exercice muscu avec numéro + détail |
| `CalendarGrid` | `packages/ui-mobile/src/components/CalendarGrid.tsx` | Grille mensuelle avec discipline marks |
| `WeeklyMetricStrip` | `packages/ui-mobile/src/components/WeeklyMetricStrip.tsx` | 3 colonnes métriques hebdo avec delta |
| `TrainingListRow` | `packages/ui-mobile/src/components/TrainingListRow.tsx` | Row séance dans la liste |
| `ChatBubble` | `packages/ui-mobile/src/components/ChatBubble.tsx` | Bulle coach ou utilisateur |
| `QuickReplyChip` | `packages/ui-mobile/src/components/QuickReplyChip.tsx` | Chip suggestion chat ghost border |

### Wave 3 — Complexes (utilise Wave 1+2 + @gorhom + expo-blur + draggable)

| Composant | Fichier cible | Description |
|---|---|---|
| `HITLSheet` | `packages/ui-mobile/src/components/HITLSheet.tsx` | Bottom sheet HITL : 3 types de questions + blur backdrop |
| `DayDetailDrawer` | `packages/ui-mobile/src/components/DayDetailDrawer.tsx` | Bottom sheet détail jour training history |
| `CheckboxOption` | `packages/ui-mobile/src/components/CheckboxOption.tsx` | Row multi-choix HITL avec checkbox animée |
| `SingleChoiceOption` | `packages/ui-mobile/src/components/SingleChoiceOption.tsx` | Row choix unique HITL avec pill numéro + flèche |
| `DraggableOption` | `packages/ui-mobile/src/components/DraggableOption.tsx` | Row réordonnage HITL avec handle |

---

## 4. Dépendances à installer

| Package | Usage | Commit |
|---|---|---|
| `@gorhom/bottom-sheet` | Training History drawer + HITL sheet | commit-deps |
| `expo-blur` | HITL sheet backdrop | commit-deps |
| `react-native-draggable-flatlist` | HITL type 3 réordonnage | commit-deps |
| `expo-apple-authentication` | Auth — Apple Sign In | commit-deps |

**Packages déjà présents (vérifiés):**
- `react-native-reanimated` 4.2.1 ✅
- `react-native-svg` 15.15 ✅
- `expo-haptics` ✅
- `react-native-gesture-handler` ✅ (requis par @gorhom)
- `react-native-safe-area-context` ✅
- `@expo-google-fonts/space-grotesk` ✅ (présent mais pas chargé)

---

## 5. Questions ouvertes résolues

| # | Question | Décision |
|---|---|---|
| 1 | Fond dark canonique | `#131210` unifié |
| 2 | Lime | Supprimé. Amber pour tout. |
| 3 | Mode A→B transition | Navigation push RN |
| 4 | Home scroll | ScrollView |
| 5 | Auth erreurs | Inline sous l'input |
| 6 | Tab bar structure | Entraînement remplace Check-in |
| 7 | Jour sans séance Training History | Pas de drawer |
| 8 | HITL blur intensity | `intensity={20}` (à affiner au test) |
| 9 | HITL snap point | 60% initial (à affiner au test) |
| 10 | Onboarding animation | Slide horizontal translateX |

## 6. Questions ouvertes restantes

| # | Question | Blocage |
|---|---|---|
| A | Check-in tab supprimé: route `/(tabs)/check-in` toujours utilisée dans index.tsx | Désactiver ou rediriger vers profil |
| B | Persistance session Mode B en background | Non-bloquant V1 — timer simple, pas de background task |
| C | Navigation mois futurs en Training History | Afficher séances planifiées si dispo, sinon vide |
| D | Filtre (≡) Training History | Placeholder — pas d'action V1 |
