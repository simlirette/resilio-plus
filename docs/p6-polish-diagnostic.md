# P6 Polish — Diagnostic Phase 1 (v2, 4 corrections appliquées)
_Branche: `chore/downgrade-sdk54` | 2026-04-19_

---

## CORRECTION A — Branche confirmée

`git branch --show-current` → `chore/downgrade-sdk54` ✅

Le header v1 du diagnostic mentionnait `chore/color-purge-amber-canonical` par erreur (branche d'une autre session). Code analysé = branche correcte.

---

## 1.1 — draggable-flatlist / reanimated sur Expo Go SDK 54

### État des packages
- `react-native-draggable-flatlist: "^4.0.3"` — installé dans `apps/mobile/package.json`
- `react-native-reanimated: "4.1.7"` — installé dans `apps/mobile/package.json`

### Verdict : **⚠️ Risque élevé — PanResponder fallback recommandé**

`react-native-draggable-flatlist` v4 dépend de `react-native-reanimated` pour ses animations de drag. Or, reanimated 4.x utilise les Turbo Modules (worklets JSI) qui **ne sont pas compilés dans le binaire Expo Go SDK 54**. Ce pattern a déjà causé un crash sur cette branche lors de P2 Onboarding (erreur `TurboModule RCTWorkletRuntime not found`) — corrigé en supprimant reanimated du fichier concerné.

**Deux options pour Bug 5 :**

| Option | Approche | Risque |
|---|---|---|
| A — PanResponder natif | Drag avec `PanResponder` + `Animated.Value` (legacy API) | Zéro crash, 100% Expo Go safe |
| B — draggable-flatlist | Import conditionnel + test sur device | Crash probable en Expo Go SDK 54 |

**Décision recommandée : Option A — PanResponder.**

Implémentation : chaque `RankRow` porte un `PanResponder` sur la zone handle `⋮⋮`. Le drag vertical (`dy`) est converti en swap d'items quand le seuil dépasse la hauteur d'une row (~52px). `Animated.Value` pour le décalage visuel pendant le drag. La liste est un tableau `useState` simple mis à jour au `onPanResponderRelease`. Haptic `ImpactFeedbackStyle.Light` au moment du swap.

---

## 1.2 — NativeTabs / Liquid Glass sur SDK 54

### CORRECTION B — Bug 6 ROUVERT (diagnostic v1 incorrect)

**NativeTabs est disponible sur SDK 54 / expo-router v6.**

Preuves vérifiées :
1. `ls node_modules/expo-router/build/ | grep -i native` → dossier `native-tabs` présent ✅
2. Commit `e2d1810` ("feat(mobile): migrate to NativeTabs for iOS liquid glass tab bar") — fait sur cette branche (SDK 54), complet et fonctionnel ✅
3. API : `import { NativeTabs } from 'expo-router/unstable-native-tabs'` — disponible dans la build SDK 54 d'expo-router

**Régression identifiée :**

Le `_layout.tsx` actuel a **réverté à `<Tabs>` standard** avec un commentaire erroné :
```ts
// NativeTabs (SDK 55 only) replaced with standard expo-router Tabs for SDK 54 compat.
```
Ce commentaire est faux. La régression s'est produite lors d'un commit ultérieur à e2d1810. Les tabs actuels ont aussi 2 hex hardcodés en violation des règles :
- `backgroundColor: '#1A1816'` → devrait être `colors.dark.background`
- `'rgba(255,255,255,0.45)'` → devrait être `colors.dark.textMuted`

**Verdict : Bug 6 DANS le scope, restauration via pattern e2d1810 adapté.**

### Plan de restauration

Adaptations nécessaires vs e2d1810 :
- 4 tabs actuels : `index`, `training`, `chat`, `profile` (vs `index`, `check-in`, `chat`, `profile` dans e2d1810)
- `tintColor: colors.accent` (amber `#B8552E`) — vs `colors.accent` qui était blue à l'époque
- SF Symbols adaptés :
  - `index` → `house` / `house.fill`
  - `training` → `calendar` / `calendar.fill`
  - `chat` → `message` / `message.fill`
  - `profile` → `person` / `person.fill`
- `blurEffect: "systemChromeMaterial"` (inchangé)
- 0 hex hardcodé

---

## 1.3 — Drag Handle — Pattern visuel (screenshot référence)

Source : `docs/design/coach chat/screenshots/coach chat - order question.png`

### Description exacte
- **Icône :** Grille 2×3 points `⋮⋮` (6 dots en 2 colonnes) — style "grip"
- **Position :** Alignée à **droite** de chaque row de rang
- **Couleur :** Gris atténué (`textMuted`) — discret, non-accent
- **Hint textuel :** `"GLISSE POUR RÉORDONNER"` — affiché sous la liste, uppercase, petite taille, centré
- **Interaction :** Drag depuis la zone handle (pas longPress — drag immédiat)
- **Pas de flèches ↑↓** dans le design final

### Implémentation cible (Phase 2)
```
RankRow layout:
  [N°]  [Texte du choix ...........]  [⋮⋮]
   32px  flex:1                        24px zone PanResponder
```
- `⋮⋮` via 6 View circulaires 3px dans 2 colonnes × 3 rangées, couleur `textMuted`
- `PanResponder` sur zone handle uniquement
- Haptic `ImpactFeedbackStyle.Light` au swap (dy > 52px threshold)

---

## Bug 1 — Mesure pixel-perfect (CORRECTION D)

### Source : `docs/design/homedashboard/screenshots/homedashboard - light.png`

**Mesures dans l'image (téléphone "Normal — Readiness 78") :**

| Élément | Hauteur image (px) | 
|---|---|
| Ring outer diameter | ~155px |
| "78" numeral height | ~75px |

**Ratio design :** 75 / 155 = **48% du diamètre outer**

**Calcul device :**
- Ring = 160pt (notre impl) × 48% = **77pt** — mais l'utilisateur confirme que 72px est trop grand à l'écran réel

**Analyse :** Le design source montre ~75px, notre impl à 72px est fidèle au design, mais l'utilisateur ressent le chiffre comme trop dominant une fois rendu sur iPhone physique. Réduction intentionnelle vs design — cible : **52px** (33% de réduction vs 72px, soit 33% du diamètre outer plutôt que 48%).

Justification 52px : `inner diameter` = 160 - 2×10 = 140pt. 52px ≈ 74% du rayon intérieur (70pt) → chiffre confortable sans dominer le ring.

---

## CORRECTION C — Bug 4 texte verbatim

**Texte exact à produire (2 lignes) :**
- **L1 :** `SEMAINE DU 13 AVRIL` (uppercase, pleine orthographe, PAS d'abréviation "SEM.")
- **L2 :** `7 SÉANCES - 7H05 TOT. - 381 CHARGE` (séparateur ` - ` tiret simple, "TOT." présent)

---

## Résumé décisions Phase 2

| Bug | Décision |
|---|---|
| 1 — Ring number trop grand | Réduire de 72px → **52px** |
| 2 — "Fatigue musculaire" 3 lignes | `numberOfLines={2}` + texte condensé ou `adjustsFontSizeToFit` |
| 3 — Header CogLoad | Supprimer "CHARGE COGNITIVE" ; "Charge allostatique" → couleur `text` (pas `textFaint`) |
| 4 — Week header training | 2 lignes : L1 `SEMAINE DU 13 AVRIL` ; L2 `7 SÉANCES - 7H05 TOT. - 381 CHARGE` |
| 5 — Rank drag | PanResponder + Animated.Value + handle `⋮⋮` droite, Haptics.Light au swap |
| 6 — NativeTabs | **ROUVERT** — restaurer pattern e2d1810, 4 tabs actuels, amber tintColor |
