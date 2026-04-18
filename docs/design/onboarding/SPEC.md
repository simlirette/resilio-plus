# Onboarding — Spec d'implémentation

## Source de vérité
- `screenshots/onboarding - light.png` — 5 étapes light (BG #F5F5F2, Surface #FFFFFF)
- `screenshots/onboarding - dark and notes.png` — 5 étapes dark (BG #17161A, Surface #201E23) + notes auteur
- `onboarding/tokens.js` — tokens complets light/dark
- `onboarding/steps.jsx` — logique des 5 étapes

## Aperçu visuel
Flux post-signup en 5 étapes séquentielles: Profil → Sports → Niveau → Objectif → Connecteurs. Progress segmenté en haut, CTA "Suivant" / "Terminer" pleine largeur en bas. Accent amber unique sur CTA, état sélectionné, et checkmarks. Sémantique physiologique absente.

## Structure

### Layout commun à toutes les étapes
1. **Status bar** iOS natif
2. **Header** (row): lien "← Retour" (désactivé étape 1) | progress segments (5) | bouton "Passer" (visible étape 5 connecteurs uniquement)
3. **Label étape** — "ÉTAPE 0X · NOM" — small-caps, 11px, textMuted
4. **Titre** — 26–28px, 700, tracking serré
5. **Sous-titre** — 15px, 400, textSub
6. **Contenu étape** (variable — voir détail)
7. **CTA** — "Suivant" / "Terminer" — pleine largeur, 54px, radius 12, accent

### Étape 01 — Profil
Formulaire scrollable: Prénom (input text), Date de naissance (input date `JJ/MM/AAAA`), Genre biologique (segmented control Femme/Homme), note explicative, Taille (input numérique cm/ft-in), Poids (input numérique kg/lbs).

### Étape 02 — Sports
Liste de 4 disciplines avec icône monoline + label + sous-label. Toggle checkbox sur chaque ligne. Compteur "X sélectionné(s) — minimum 1" sous la liste.
Disciplines: Course (Running-Trail), Musculation (Force-Hypertrophie), Vélo (Route-Gravel-Home trainer), Natation (Piscine-Eau libre).

### Étape 03 — Niveau
Par discipline sélectionnée: row avec icône + nom discipline, puis segmented control 4 niveaux (Débutant / Inter. / Avancé / Élite). Input optionnel "Années de pratique" sous chaque discipline.

### Étape 04 — Objectif
Liste radio: Performance compétitive, Hypertrophie et force, Endurance et VO2max, Santé et longévité, Composition corporelle. Un seul choix. L'option sélectionnée a fond accent soft + radio accent plein.

### Étape 05 — Connecteurs
Liste: Apple Health (connecté par défaut), Strava, Hevy. Chaque row: icône + nom + statut (• Connecté / • Non connecté) + bouton "Connecter" / "Déconnecter". Note explicative sous la liste. Bouton CTA devient "Terminer".

## Palette observée (depuis screenshots)

### Light mode
```
bg:         #F5F5F2
surface:    #FFFFFF
surfaceAlt: #FAFAF7
text:       #1A1A18
textSub:    oklch(0.42 0.006 80)  // ≈ #5A5650
textMuted:  oklch(0.56 0.006 80)  // ≈ #8A8680
border:     oklch(0.88 0.004 80)  // ≈ #E2E0DB
borderFocus:accent
accent:     oklch(0.64 0.14 45)   // warm amber ~#C06840
accentText: #FFFFFF
accentSoft: oklch(0.94 0.03 45)   // fond sélection douce
overlay:    rgba(0,0,0,0.04)
```

### Dark mode
```
bg:         #17161A
surface:    #201E23
surfaceAlt: #26232A
text:       #F0EEEA
textSub:    oklch(0.76 0.008 80)
textMuted:  oklch(0.58 0.008 80)
border:     oklch(0.28 0.005 60)
borderFocus:accent
accent:     oklch(0.72 0.14 45)   // same hue, lighter for dark
accentText: #17161A
accentSoft: oklch(0.30 0.06 45)
overlay:    rgba(255,255,255,0.04)
```

## Typographie
- Famille: Space Grotesk
- Titre étape: 26–28px, 700, tracking -0.5
- Sous-titre: 15px, 400
- Label étape (small-caps): 11px, 500, uppercase, tracking +0.14em
- Label champ formulaire (small-caps): 11px, 500, uppercase, tracking +0.14em
- Input value: 16px, 400 (ou 500)
- Item liste (discipline / objectif): 16px, 600 titre / 13px, 400 sous-label
- Compteur sélection: 13px, 400, textMuted
- Note légale: 12px, 400, textMuted
- CTA: 16px, 600

## Spacing et rythme
- Padding horizontal: 20px
- Gap entre le header et le label étape: 24px
- Gap label → titre: 6px
- Gap titre → sous-titre: 8px
- Gap sous-titre → contenu: 24px
- Hauteur item liste discipline: 64px (icône 40px + padding)
- Gap entre items: 0 (séparateur hairline 1px entre rows)
- CTA fixé en bas avec padding-bottom safe area + 16px

## Radii
- Cards / rows sélectionnés: 12px
- Inputs: 10px
- CTA: 12px
- Segmented control: 8px

## Ombres et élévations
Aucune ombre. Différenciation par border hairline uniquement.

## Comportements interactifs

### Progress bar
- 5 segments fins (pas de points ronds, pas de dots)
- Segment actif: accent
- Segments complétés: accent (plein)
- Segments futurs: border (neutral)
- Pas de transition animée entre segments — swap instantané

### Retour
- Désactivé étape 1 (opacity 0 ou caché)
- Actif étapes 2–5

### Passer
- Visible uniquement étape 5 Connecteurs
- Caché toutes les autres étapes

### Disciplines (étape 02)
- Tap sur une row: toggle sélection
- Sélectionné: fond accentSoft, icône stroke accent, checkmark accent en coin droit
- Icônes sport: monoline, 1.5px stroke, couleur accent quand sélectionné, textMuted sinon
- CTA disabled si 0 sélectionné

### Segmented control niveau (étape 03)
- 4 segments equal width
- Actif: fond accent, texte accentText
- Inactif: fond surface, texte text

### Radio objectif (étape 04)
- Tap: sélection unique
- Sélectionné: fond accentSoft sur toute la row, radio bullet plein accent
- Non sélectionné: radio circle outline, fond transparent

### Connecteurs (étape 05)
- Row avec état visuel (point vert ou neutre)
- Bouton "Connecter" → lancement OAuth externe (hors scope onboarding)
- Bouton "Déconnecter" → confirmation via Alert natif iOS (pas de modal custom)

## Animations critiques
- Transition entre étapes: slide horizontal (translateX) — étape suivante entre par la droite, étape précédente sort par la droite
- En RN: `react-native-reanimated` withTiming ou `SharedTransition`

## Gestion clavier
- Étape 01 (formulaire): `KeyboardAvoidingView` behavior `padding`
- Champs scrollables: `ScrollView` + `KeyboardPersistTaps="handled"`
- CTA doit rester visible au-dessus du clavier

## Safe area
- Top: status bar
- Bottom: CTA fixé au-dessus du home indicator (padding-bottom = safeAreaInsets.bottom + 16px)

## Dépendances RN probables
- `react-native-reanimated` v3 (transition étapes)
- `react-native-safe-area-context`
- `@resilio/design-tokens`
- Pas de lib externe pour les checkboxes/radios — composants custom simples

## États à implémenter

| Étape | États |
|---|---|
| 01 Profil | empty, partiellement rempli, complet (CTA actif) |
| 02 Sports | 0 sélectionné (CTA disabled), 1+, max 4 |
| 03 Niveau | niveau sélectionné par discipline, années optionnel |
| 04 Objectif | aucun (CTA disabled), 1 sélectionné |
| 05 Connecteurs | Apple connecté / non connecté, Strava non connecté, Hevy non connecté |

## Edge cases et questions ouvertes
- **Validation étape 01**: les champs taille/poids sont-ils obligatoires ou optionnels ? Screenshots montrent des valeurs mais pas d'état erreur. **À trancher.**
- **Genre biologique note**: "Utilisé pour calibrer les calculs énergétiques (DEJ, EA, seuils)." — confirmer wording final.
- **Transition animation**: slide ou fade ? Screenshots ne montrent pas de transition. **À trancher.**
- **Apple Health**: sur iOS simulateur, AppleHealth n'est pas dispo. Placeholder requis pour dev.

## Anti-patterns à éviter pour cette page
- Pas d'emoji dans les items de liste (note auteur: "Pas d'emoji")
- Pas de couleur sémantique (green/yellow/red) sur cet écran
- Pas de progress dots ronds — segments fins uniquement
- Pas de CTA désactivé avec opacité 20% — utiliser 40% minimum pour lisibilité
