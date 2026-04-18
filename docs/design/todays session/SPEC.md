# Séance du Jour — Spec d'implémentation

## Source de vérité
- `screenshots/todays session - mode A prescription.png` — Mode A (avant démarrage) × Course + Muscu × Light + Dark
- `screenshots/todays session - mode B execution.png` — Mode B (pendant) × Course + Muscu × Light + Dark
- `lib/tokens.jsx` — tokens complets avec dual-accent system
- `lib/prescription.jsx` — code Mode A
- `lib/execution.jsx` — code Mode B

## Aperçu visuel
2 modes distincts partagent la même header. **Mode A (Prescription)**: lecture de la séance + justification coach avant démarrage. **Mode B (Exécution)**: une info principale, une action, zéro chrome pendant la séance.

> **Accent unique**: amber (`#B8552E` light / `#D97A52` dark) pour tous les CTA, y compris "Démarrer" et "Set terminé". Pas de lime.

## Structure

### Header commun (Mode A et B)
- Date (SAM. 18 AVR.) — 11px small-caps, textMuted
- Titre "Séance" — centré, 17px, 600
- Bouton retour `<` gauche, bouton `...` options droite
- Type séance (SÉANCE COURSE · Z2) — 11px small-caps, accent

### Mode A — Prescription

1. **Titre séance** — 28px, 700, pleine largeur ("Endurance fondamentale Z2" / "Force — haut du corps A")
2. **Métriques header** — 3 colonnes: Durée / Charge / Intensité — 11px small-caps + valeur 17px tabular
3. **Bloc "Pourquoi cette séance"** — card fond surfaceAlt, texte 14px, 400 — justification coach
4. **Section PRESCRIPTION** + compteur phases/exercices aligné droite (textMuted)
5. **Liste des phases** (course) ou **liste des exercices** (muscu):
   - Course: row avec label phase (WARM-UP/MAIN/COOL-DOWN), allure cible, durée
   - Muscu: row numéroté, nom exercice, sets × reps @ RPE, note technique
6. **PROFIL DE ZONE** (course uniquement) — barre + durée
7. **CTA "▶ Démarrer"** — pleine largeur, 56px, radius 14–18px, fond **amber** (accent), texte onAccent

### Mode B — Exécution (Course)

1. **Header compact**: titre séance + chrono + bouton pause
2. **Phase et progression** — "MAIN — Z2 · 2/3" (accent vert small-caps)
3. **ALLURE CIBLE** — label small-caps
4. **Hero number**: pace "5:42" — ~80px, 700, tabular, tracking -3
5. **Unité "/km"** — 24px, 400
6. **Fenêtre** — "Fenêtre 5:32 – 5:52" — 13px, textMuted
7. **Projection** — textFaint, 12px
8. **Métriques live** (2 colonnes): Allure live + FC live avec indicateur couleur sémantique
9. **BLOC COURANT** tab + RESTANT — texte small-caps, valeur tabular
10. **Suivant** — preview phase suivante en surface
11. **"Terminer la séance"** — ghost button + bouton pause

### Mode B — Exécution (Muscu)

1. **Header compact** + progression "EXERCICE 02 / 05"
2. **Nom exercice** — 28px, 700
3. **Détail**: sets × reps @ RPE, tempo
4. **SET COURANT** — selector visual: cercle check (fait), pill actif (accent sombre), pills inactifs
5. **CHARGE** + **RÉPÉTITIONS** — hero numbers, tabular
6. **RPE DU SET PRÉCÉDENT** — selector 1–10 horizontal, valeur sélectionnée pill sombre
7. **REPOS** — compteur "01:47 / 02:30" + badge "AUTO"
8. **"✓ Set terminé"** — pleine largeur, fond **amber** (accent), texte onAccent + bouton "Skip" à droite
9. **TERMINER LA SÉANCE** — small-caps centré, texte textMuted

## Palette observée (depuis screenshots + tokens.jsx)

### Light mode
```
bg:          #F5F3EE    // off-white warm
bgElev:      #FFFFFF    // cards
bgElev2:     #EDEAE2    // inset / surface alt
hairline:    rgba(26,22,16,0.08)
ink:         #181613
inkMuted:    rgba(24,22,19,0.62)
inkDim:      rgba(24,22,19,0.42)
inkFaint:    rgba(24,22,19,0.22)
// DUAL ACCENT:
accentUI:    oklch(amber)     // #B8552E — tous les CTA, navigation, états actifs
// physio
green:       #3F8A4A
yellow:      #B88A16
red:         #B64536
```

### Dark mode
```
bg:          #141311    // warm charcoal, NOT #08080e
bgElev:      #1C1B18
bgElev2:     #242320
hairline:    rgba(255,248,230,0.08)
hairlineStr: rgba(255,248,230,0.14)
ink:         #F3EFE6
inkMuted:    rgba(243,239,230,0.62)
accentCTA:   #D97A52    // amber dark mode
green:       #8FCB82
yellow:      #E8C86A
red:         #E27A6F
```


## Typographie
- Famille: Space Grotesk + `fontVariantNumeric: 'tabular-nums'` partout où il y a des chiffres
- Titre séance (Mode A): 28px, 700, tracking -0.5
- Hero pace (Mode B course): ~80px, 700, tracking -3
- Hero exercice (Mode B muscu): 28px, 700
- Hero chiffres (charge: 72kg / reps: 6): 40px, 700, tabular
- Labels small-caps: 11px, 500, uppercase, tracking +0.14em
- Valeurs métriques header: 17px, 500, tabular
- Corps texte justification coach: 14px, 400
- Phase liste: 15px, 600 (nom) + 13px, 400 (détail)

## Spacing et rythme
- Padding horizontal: 20px
- Header height: 44px (sans status bar)
- Gap entre sections Mode A: 20px
- Padding interne cards: 14–16px
- Hauteur CTA: 56px
- Padding-bottom CTA: safe area + 16px

## Radii
- Cards Mode A: 14–18px (note auteur: "Radius 14-18px sur cards")
- Inputs / selectors: 10px (note auteur: "10px sur inputs, jamais pill 50%")
- CTA "Démarrer" / "Set terminé": 14px
- Pills set selector: 10px

## Ombres et élévations
Aucune ombre. Dark utilise hairlines warm-tinted pour séparer les surfaces.

## Comportements interactifs

### CTA "Démarrer"
- Tap → transition vers Mode B
- Haptic: `ImpactFeedbackStyle.Heavy` (action primaire de la journée)
- Animation: pas de slide — remplacement de vue (ou navigation)

### Mode B — Compteur pause
- Bouton pause: suspend le chrono, affiche overlay minimal (pas modal)
- Resume: reprend là où arrêté

### Mode B — Set terminé (muscu)
- Tap → marque set comme fait, lance countdown repos, passe au set suivant
- Le cercle check (✓) apparaît sur le set précédent
- Countdown repos visible et décompte en temps réel

### Mode B — RPE selector
- Tap sur un chiffre: sélection immédiate, valeur précédente mise à jour
- Pas de confirmation requise

### Skip (muscu)
- Passe à l'exercice suivant sans marquer comme terminé
- Pas de haptic (action secondaire)

## Animations critiques
- **Mode A → Mode B**: transition de vue. Recommandé: `SharedTransition` sur le titre de séance (ancre visuelle commune). À trancher.
- **Countdown repos**: chiffres décomptent en temps réel — `setInterval` ou `reanimated` clock
- **Pace live**: mise à jour chaque seconde sans flash — `withTiming` 200ms ou directement

## Gestion clavier
Mode A: pas d'input. Mode B: pas d'input (RPE par tap, pas clavier). Sans objet.

## Safe area
- Top: status bar
- Bottom: CTA fixé — `insets.bottom + 16px`

## Dépendances RN probables
- `react-native-reanimated` v3 (animations, countdown)
- `react-native-svg` (profil de zone course, si applicable)
- `expo-haptics`
- `react-native-safe-area-context`
- `@resilio/design-tokens`

## États à implémenter

### Mode A
| État | Description |
|---|---|
| Course - Light/Dark | Phases warm-up / main / cool-down + profil de zone |
| Muscu - Light/Dark | Liste exercices numérotés + notes technique |

### Mode B — Course
| État | Description |
|---|---|
| Dans la cible | Allure live vert + "dans la cible" |
| Hors cible (trop vite/lent) | Allure live rouge/jaune + message |
| Phase transition | Overlay bref annonçant la phase suivante |
| Pause | Chrono gelé, bouton resume |

### Mode B — Muscu
| État | Description |
|---|---|
| Set en cours | Countdown repos caché ou à 0 |
| Repos | Countdown visible et décompte |
| Dernier set d'exercice | CTA "Set terminé" → passe à exercice suivant |
| Dernier exercice | CTA → "Terminer la séance" |

## Edge cases et questions ouvertes
- **Transition Mode A → B**: navigation RN ou remplacement de composant ? Shared element transition entre les deux modes ? **À trancher.**
- **Persistance session**: si l'app passe en background pendant Mode B, le chrono doit-il continuer ? Nécessite background task. **À trancher.**
- **Sets vs phases**: comment la navigation fonctionne-t-elle quand il y a plusieurs exercices et plusieurs sets ? L'écran montre toujours l'exercice courant. Swipe ou navigation automatique ? **À trancher.**

## Anti-patterns à éviter pour cette page
- CTA amber = action primaire — jamais décoratif, jamais sur l'UI chrome non-interactif
- Pas d'icône décorative — glyphes sport monoline, 1.5px stroke uniquement (note auteur)
- Sémantique green/yellow/red uniquement pour FC live / allure vs cible (note auteur)
- Le fond dark est #141311, PAS #08080e
- Jamais pill 50% sur les radii
