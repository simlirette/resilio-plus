# UI-RULES — Resilio+ Mobile

> **REGLE D'OR**: Relis ce fichier avant chaque modification frontend. Les anti-patterns listés ici ont été réintroduits plusieurs fois par dilution de contexte. Ce document est la source de vérité visuelle.

## Changelog
- 2026-04-19: ajout règle d'or, exemples concrets par anti-pattern, correction animation (Animated.Value SDK 54), mise à jour globals.css (@import url supprimé).
- 2026-04-18: création initiale depuis analyse des screenshots `docs/design/`. Correction couleur d'accent (remplacement violet #5b5fef et bleu #3B74C9 par amber/terracotta confirmé visuellement). Clarification direction visuelle. Documentation dual-accent system (amber + lime). Dark bg canonique non-clinique.

---

## Direction visuelle

Resilio+ est une app d'athlètes sérieux. L'UI doit transmettre précision, lisibilité et densité d'information — comme Apple Health, pas comme une app de motivation.

**Inspirations légitimes**: Apple Health (structure, densité, hiérarchie typographique), Whoop 5.0 (warm neutrals, readiness ring, chiffres tabular), interfaces cliniques modernes (clarté, pas de bruit décoratif).

**Explicitement rejetés**: Bevel (fonds photo paysage, typo serif display), dark clinique pur style `#08080e` (trop froid), pastels, gradients décoratifs, pill-shape systématique, drop-shadows lourds.

Light et dark mode **tous deux obligatoires** pour V1. Pas de mode unique.

---

## Palette canonique

### Accent principal — Amber/Terracotta

L'accent est un **amber chaud** (teinte orange-terracotta), pas violet, pas bleu.

```
Light mode:  #B8552E  (ou oklch(0.62–0.64 0.14 35–55) selon le fichier source)
Dark mode:   #D97A52  (ou oklch(0.68–0.72 0.13–0.14 38–65) selon le fichier source)
```

Utilisé pour:
- Tab bar icône + label actif
- CTAs de navigation et formulaires (Suivant, Se connecter, Envoyer)
- Liens actifs (accent text)
- État sélectionné (radio, checkbox fill, segmented control actif)
- Bouton send dans le chat
- Compteur HITL sheet `→`

**Jamais** utilisé pour:
- Indicateurs physiologiques (Readiness, Strain, Sommeil, HRV)
- Fonds de card décoratifs
- Gradients

### Sémantique physiologique

Ces 3 couleurs sont **réservées** aux états physiologiques: Readiness ring, Strain, Sleep score, HRV, FC live, allure vs cible. **Ne jamais les utiliser pour l'UI chrome.**

```
// Light mode
Green (≥85, performance):   #3F8A4A  /  #4F7A43
Yellow (70–84, normal):     couleur accent amber (réutilisée)
Red (<70, récupération):    #B64536  /  #9C4A32

// Dark mode
Green:   #8FCB82  /  #7FAD6B
Yellow:  #E8C86A  /  #D4B34D
Red:     #E27A6F  /  #C47A5A
```

### Fonds et neutres (warm greys)

Tous les neutres ont une légère teinte chaude (jaune/brun). Aucun gris pur froid.

```
// Light
bg:          #F5F5F2    // fond principal off-white
surface:     #FAFAF7    // cards
surfaceAlt:  #EDEAE2    // fonds alternatifs, inputs
border:      #E3E0D8    // hairlines, séparateurs
text:        #1A1A17    // texte principal
textSec:     #6B6862    // labels, sous-titres
textMuted:   #9A968D    // placeholders, timestamps
textFaint:   #C2BEB6    // très discret

// Dark
bg:          #17171A    // fond principal (auth, onboarding)
             #161412    // fond (dashboard)
             #1C1A17    // fond (training history)
             #141311    // fond (session execution)
             // → consensus: entre #141311 et #1C1A17, warm charcoal NON-clinique
surface:     #1F1F22    // cards
surfaceAlt:  #26232A    // fonds alternatifs
border:      #2E2D2A    // hairlines
text:        #F0EEE8    // texte principal
textSec:     #9E9A90
textMuted:   #6B6862
```

> **À trancher pour tokens canoniques**: le fond dark varie légèrement entre les pages (4 valeurs proches). Recommandé: unifier sur `#17171A` ou `#161412` et le documenter dans `packages/design-tokens/`.

---

## Typographie

- **Famille**: Space Grotesk 400, 500, 600, 700 — uniquement
- **Chargement**: `expo-font` uniquement. Jamais `@import url()`
- **Chiffres physiologiques**: `fontVariantNumeric: 'tabular-nums'` + `fontFeatureSettings: '"tnum" 1, "zero" 1'` sur tout chiffre de métrique (Readiness, pace, FC, kcal, volumes, RPE, etc.)
- **Tracking serré** sur les gros chiffres hero: `letterSpacing: -2` à `-3` pour les 70px+
- **Small-caps** pour les labels de section: `textTransform: 'uppercase'`, `fontSize: 11`, `fontWeight: '500'`, `letterSpacing: 2` (env. 0.14em)

Échelle courante:
| Usage | Size | Weight | Notes |
|---|---|---|---|
| Hero number (readiness, pace) | 72–80px | 500–700 | tabular, tracking -2 à -3 |
| Titre page | 28px | 700 | tracking -0.5 |
| Titre card/section | 22–26px | 700 | |
| Titre question HITL | 18px | 700 | tracking -0.3 |
| Navigation bar | 17px | 600 | |
| Body | 15px | 400 | |
| Body secondaire | 14px | 400 | |
| Label small-caps | 11px | 500 | uppercase, tracking +2 |
| Caption | 12–13px | 400 | |

---

## Spacing

Échelle observée dans les screenshots:

| Usage | Valeur |
|---|---|
| Padding horizontal écran | 20–24px |
| Gap entre cards/sections | 16–20px |
| Padding interne card | 14–16px |
| Gap entre items de liste | 0 (hairline seulement) |
| Hauteur CTA pleine largeur | 54–56px |
| Hauteur input | 56px |
| Hauteur row liste | 52–56px |
| Hauteur item liste discipline | 64px |
| Padding-bottom au-dessus home indicator | safe area + 16px |

---

## Radii

| Élément | Valeur |
|---|---|
| Cards principales | 14–18px |
| Cards compactes / drawers | 12px |
| Bottom sheets | 20px (top corners) |
| Inputs | 10px |
| Boutons pleine largeur (CTA) | 12–14px |
| Boutons cercle (send, HITL →) | 50% |
| Segmented controls | 8–10px |
| Avatar initiales | 50% |

**Jamais** pill 50% sur les CTA pleine largeur. **Jamais** radius > 20px sur les inputs.

---

## Ton de voix et copy

- **Langue**: français
- **Personne**: deuxième personne singulière ("tu"), pas de vouvoiement
- **Ton**: expert-naturel, déclaratif, phrases courtes. L'athlète sait ce qu'il fait.
- **Terminologie**: technique assumée sans glossaire superflu ("ACWR", "Z2", "TSS", "RPE", "VO2max")
- **Aucun emoji**
- **Aucune copy célébratoire** ("Bravo !", "Super !", "Tu es incroyable !")
- **Aucun point d'exclamation**
- **Aucun call-to-action agressif** ("GO !", "Dépasse-toi !")
- **Pas de "En savoir plus"** sur les métriques — les données sont auto-explicatives

Exemples corrects:
> "Ta Readiness est à 78. Ton ACWR est à 1.12." ✓
> "Bon boulot !" ✗
> "Zone 2 stricte. Respiration nasale privilégiée." ✓

---

## Anti-patterns explicitement interdits

Chaque anti-pattern ci-dessous a été réintroduit au moins une fois. Lire avant de coder.

### 1. `@import url()` pour les fonts

**Mal:**
```css
/* globals.css */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk...');
```

**Bien (web):**
```tsx
// layout.tsx
import { Space_Grotesk } from 'next/font/google';
const spaceGrotesk = Space_Grotesk({ subsets: ['latin'] });
```

**Bien (mobile):**
```tsx
import { useFonts } from 'expo-font';
// ou expo-google-fonts/space-grotesk
```

---

### 2. Gradients décoratifs sur cards ou backgrounds

**Mal:**
```tsx
background: 'linear-gradient(135deg, #B8552E, #D97A52)'  // sur une card
```

**Bien:**
```tsx
backgroundColor: tokens.surface  // fond uni, pas de gradient
```

Gradients uniquement tolérés: anneaux de progression (arc SVG), indicateur de charge (barre linéaire). Jamais sur fond de card, header, ou section.

---

### 3. Couleurs sémantiques hors contexte physiologique

Les couleurs green/yellow/red sont **réservées** aux métriques physiologiques (Readiness, Strain, HRV, Sleep). Jamais pour l'UI chrome.

**Mal:**
```tsx
// badge "Actif" en vert sur un élément de navigation
color: '#3F8A4A'
```

**Bien:**
```tsx
// badge de statut de navigation → accent amber
color: tokens.accent
// badge Readiness 85 → vert physiologique
color: tokens.physiological.green
```

---

### 4. Fond photo paysage (style Bevel)

**Mal:**
```tsx
background: `url('/mountain-bg.jpg') center/cover`
```

**Bien:**
```tsx
backgroundColor: tokens.bg  // off-white #F5F5F2 ou warm charcoal #17171A
```

Aucune photo ou illustration en fond. Fond uni uniquement.

---

### 5. Serif display

**Mal:**
```css
font-family: 'Playfair Display', serif;
font-style: italic;
```

**Bien:**
```css
font-family: 'Space Grotesk', sans-serif;
font-weight: 700;
```

Resilio+ = sans-serif exclusivement. Space Grotesk 400–700.

---

### 6. Palettes pastel

**Mal:**
```tsx
backgroundColor: '#E8D5F5'  // violet pastel
color: '#B3D9FF'            // bleu pastel
```

**Bien:**
```tsx
backgroundColor: tokens.surface   // warm grey, pas de teinte pastel
```

Chaque couleur doit avoir un contraste ≥ 4.5:1 sur son fond. Pas de couleurs diluées à 20% d'opacité.

---

### 7. Dark bg clinique pur `#08080e`

**Mal:**
```tsx
backgroundColor: '#08080e'  // trop froid, pas warm
```

**Bien:**
```tsx
backgroundColor: '#17171A'  // warm charcoal — légère teinte chaude
```

Le fond dark de Resilio+ n'est pas noir pur. Il a une légère composante chaude (jaune/brun) cohérente avec les neutres warm grey.

---

### 8. Valeurs hardcodées au lieu des tokens

**Mal:**
```tsx
color: '#B8552E'
paddingHorizontal: 20
borderRadius: 14
```

**Bien:**
```tsx
import { tokens } from '@resilio/design-tokens';
color: tokens.accent.light
paddingHorizontal: tokens.spacing.screenH
borderRadius: tokens.radius.card
```

Exception: valeurs calculées dynamiquement (ex: interpolations d'animation, layout math).

---

### Autres anti-patterns (sans exemples)

**Couleur:**
- Violet `#5b5fef` ou bleu `#3B74C9` — absents des screenshots, non-canoniques

**Layout:**
- Drop-shadows lourds (`box-shadow` > 8px blur)
- Pill-shape systématique sur CTA pleine largeur (radius 50% — jamais)
- Animations cosmétiques sans purpose fonctionnel (shimmer perpétuel, looping décoratif)

**Logique:**
- Pas de logique métier dans les composants UI — dans `shared-logic` ou l'app

---

## Règles techniques de port (web → React Native)

- **Tout style** passe par `StyleSheet.create()` + tokens de `packages/design-tokens`
- **Animations**: `Animated.Value` + `PanResponder` (Expo SDK 54 — les worklets reanimated sont absents du binaire Expo Go SDK 54, Turbo Module crash). Ne pas utiliser `react-native-reanimated` worklets tant que SDK ≥ 55 n'est pas validé sur device.
- **Haptic feedback iOS**: `expo-haptics` systématiquement sur les actions primaires (ImpactFeedbackStyle.Medium ou Heavy)
- **Safe area**: `react-native-safe-area-context` partout — padding-bottom = `insets.bottom + 16px` minimum
- **Clavier**: `KeyboardAvoidingView` behavior `'padding'` sur iOS sur tout écran avec input
- **Bottom sheets**: `@gorhom/bottom-sheet` (pas Modal transparent seul — voir session log)
- **SVG**: `react-native-svg` pour les arcs/anneaux (Readiness ring)
- **Blur**: `expo-blur` BlurView pour les overlays (HITL sheet backdrop)
- **Drag-and-drop**: `react-native-draggable-flatlist` (HITL order question)
- **Fonts numbers tabular**: `fontVariantNumeric` ou `fontFeatureSettings` tnum sur tous les chiffres métriques

---

## Références

- `docs/design/README.md` — structure du dossier design et hiérarchie d'autorité
- `docs/design/<page>/SPEC.md` — règles spécifiques de chaque page
- `docs/design/<page>/screenshots/` — contrat visuel absolu
- `packages/design-tokens/` — tokens canoniques (source à synchroniser avec ce document)
