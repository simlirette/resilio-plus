# Training History / Calendar — Spec d'implémentation

## Source de vérité
- `screenshots/training history - calendar and list.png` — Calendrier light, Calendrier dark, Liste light, Liste dark
- `screenshots/training history - day details.png` — Drawer détail jour light + dark
- `lib/theme.js` — tokens complets
- `lib/screen.jsx`, `lib/views.jsx` — code source écran

## Aperçu visuel
Onglet Training — 2 vues (Calendrier / Liste) switchables par segmented control. Header avec titre + icône filtre. Métriques hebdomadaires en haut (Séances, Volume, Charge). Drawer bas sur tap d'un jour pour le détail.

## Structure

### Header
1. **Status bar** iOS
2. **Titre "Entraînement"** — 28px, 700, aligné gauche
3. **Icône filtre** (≡) alignée droite — 24px, textMuted

### Segmented control
- "Calendrier" | "Liste" — pleine largeur (ou ajusté), radius 10, fond surfaceAlt, segment actif fond surface

### Métriques hebdo (row 3 colonnes)
- SÉANCES / VOLUME / CHARGE — label small-caps 11px + valeur principale (17–20px, 600, tabular) + delta "↑ +X vs 7j préc." (12px, sémantique: vert si positif, rouge si négatif)

### Vue Calendrier
- Mois + année: "Avril 2026" — 18px, 600 + flèches navigation `< >`
- Grille: L M M J V S D — 7 colonnes, hauteur cellule ~44px
- Chaque jour: numéro centré + indicateurs activité (dots) sous le numéro
- Jour sélectionné: border accent (pas de fond plein)
- Jour aujourd'hui sans sélection: border neutre ou subtle
- Indicateurs activité: dots noirs/blancs, demi-cercle, cercle, multiple dots → encode le type de discipline

### Vue Liste
- Regroupée par semaine: header "SEM. DU 13 AVR. · 6 séances · 6h30 · 359 charge" — small-caps, textMuted
- Chaque séance: row avec [jour+date à gauche] [icône discipline] [titre séance + type] [durée + charge]
- Jour en accent si c'est aujourd'hui
- Séparateur hairline entre les séances

### Drawer Détail Jour (bottom sheet)
Apparaît sur tap calendrier:
- Handle bar en haut (trait centré)
- Section "JOUR" small-caps + "Jeudi 16 Avril" 22px, 700
- Row métriques jour: SÉANCES / VOLUME / CHARGE (même pattern que hebdo)
- Chaque séance du jour: card avec icône discipline + titre + type + métriques (DURÉE, CHARGE, RPE, DISTANCE)
- Pas de CTA dans le drawer — lecture seule

## Palette observée (depuis screenshots + theme.js)

### Light mode
```
bg:         #F5F5F2
surface:    #FAFAF7    // cards, drawer
surface2:   #EDECE6    // completed day bg
hairline:   rgba(26,25,22,0.08)
text:       #1A1916
textSec:    #6B6862
textTer:    #9A968E
accent:     #A85A2F    // warm amber-terracotta
accentSoft: rgba(168,90,47,0.10)
physioGreen:  #4F7A43
physioYellow: #A68A2E
physioRed:    #9C4A32
```

### Dark mode
```
bg:         #1C1A17    // warm charcoal
surface:    #242220
surface2:   #2B2926
hairline:   rgba(232,228,220,0.09)
text:       #E8E4DC
textSec:    #9A968E
textTer:    #6B6862
accent:     #D98E5E
accentSoft: rgba(217,142,94,0.14)
physioGreen:  #7FAD6B
physioYellow: #D4B34D
physioRed:    #C47A5A
```

### Discipline marks (calendrier dots)
Encodage par valeur, pas couleur:
```
Course (run):   disque plein sombre
Muscu (lift):   disque plein mid-grey
Vélo (bike):    cercle outline seulement
Natation (swim): demi-disque
```

## Typographie
- Titre page: 28px, 700, tracking -0.5
- Mois: 18px, 600
- Numéros calendrier: 15px, 400 (ou 500 pour le jour actif)
- Labels semaine (small-caps): 11px, 500, uppercase, tracking +0.14em
- Titre séance dans liste: 15px, 600
- Type séance: 12px, 400, textSec
- Durée / charge: 15px, 600, tabular
- Métriques hédo valeurs: 17–20px, 600, tabular
- Delta: 12px, 400, tabular, sémantique

## Spacing et rythme
- Padding horizontal: 16–20px
- Header → segmented: 12px
- Segmented → métriques: 16px
- Métriques → calendrier/liste: 20px
- Hauteur cellule calendrier: 44px
- Padding interne row liste: 12px vertical
- Drawer: padding horizontal 20px, gap sections 16px

## Radii
- Segmented control: 10px
- Cards drawer (détail séance): 12px
- Jour sélectionné calendrier: 8px (border, pas fond plein)
- Drawer (bottom sheet): 20px top corners

## Ombres et élévations
Aucune ombre sur les cards. Le drawer bottom sheet peut avoir une légère ombre vers le haut (rgba(0,0,0,0.08)) mais minimaliste.

## Comportements interactifs

### Switch Calendrier ↔ Liste
- Tap sur le segment: swap de contenu
- Animation: crossfade ou none (À trancher)

### Calendrier — navigation mois
- `<` et `>`: changer le mois affiché
- Animation: slide horizontal (mois suivant entre par la droite)

### Tap sur un jour du calendrier
- Ouvre le drawer bottom sheet avec le détail du jour
- Si le jour n'a pas de séance: drawer minimal "Repos" ou pas de drawer (À trancher)

### Bottom sheet
- Swipe down pour fermer
- En RN: `@gorhom/bottom-sheet` avec snap points (50% et 90%)

### Liste — scroll
- `FlatList` ou `SectionList` (groupé par semaine)
- Scroll vertical natif

## Animations critiques
- Drawer open/close: `@gorhom/bottom-sheet` animation native
- Navigation mois: `withTiming` translateX sur la grille
- En RN: `react-native-reanimated` v3

## Gestion clavier
Pas d'input sur cet écran. Sans objet.

## Safe area
- Top: status bar
- Bottom: tab bar + home indicator (drawer s'étend au-dessus du tab bar)

## Dépendances RN probables
- `@gorhom/bottom-sheet` (drawer détail jour)
- `react-native-reanimated` v3
- `react-native-safe-area-context`
- `@resilio/design-tokens`
- `react-native-svg` (discipline marks si nécessaire)

## États à implémenter

| État | Description |
|---|---|
| Calendrier — jour sans séance | Numéro seul, pas de dots |
| Calendrier — jour avec 1 séance | 1 dot du type de discipline |
| Calendrier — jour avec 2+ séances | 2–3 dots |
| Calendrier — jour sélectionné | Border accent |
| Calendrier — aujourd'hui | Border neutre strong |
| Liste — semaine avec récupération | Row "— Récupération" en textMuted |
| Drawer — 1 séance | 1 card |
| Drawer — 2 séances | 2 cards (cas double séance) |
| Métriques delta positif | ↑ vert |
| Métriques delta négatif | ↓ rouge |

## Edge cases et questions ouvertes
- **Jour sans séance**: tap sur ce jour ouvre-t-il un drawer ? Ou rien ? Screenshots ne montrent pas ce cas. **À trancher.**
- **Navigation mois**: peut-on naviguer dans le futur ? Si oui, les jours futurs ont-ils des dots (séances planifiées) ? **À trancher.**
- **Discipline marks encodage**: le code source documente les types (solid/outline/half) mais pas les tailles exactes en px. **À mesurer sur les screenshots.**
- **Filtre (icône ≡)**: non documenté dans les screenshots. **À trancher pour v2.**

## Anti-patterns à éviter pour cette page
- Pas de couleur sémantique sur les discipline marks — encodage par valeur (filled/outline/half) uniquement
- Pas de fond plein sur les jours du calendrier — border uniquement pour la sélection
- Pas de shadow sur les cards du drawer
