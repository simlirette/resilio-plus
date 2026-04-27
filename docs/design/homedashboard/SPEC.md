# Home Dashboard — Spec d'implémentation

## Source de vérité
- `screenshots/homedashboard - light.png` — 3 états Readiness × light (Normal 78, Journée idéale 92, Récupération obligatoire 45)
- `screenshots/homedashboard - dark.png` — 3 états × dark
- `dashboard.jsx` — code source complet avec tokens

> **Note:** `ui archive/home/` est une archive historique (version 0). Ne jamais utiliser comme référence. Seul `homedashboard/` est valide.

## Aperçu visuel
Écran principal de l'app. Priorité absolue à la Readiness ring centrée (chiffre hero + anneau sémantique). En dessous: 3 métriques compactes (Nutrition, Strain, Sommeil), puis la Séance du jour (ou Récupération si readiness basse). Tab bar 5 onglets en bas.

## Structure (du haut vers le bas)

1. **Status bar** iOS natif
2. **Header**: "Bonjour [Prénom]" (28px, 700) + date sous (13px, textMuted, uppercase small-caps) + avatar initiales (36px, circle, surface)
3. **Readiness ring** — centré, ~160px diamètre, anneau 10–12px épaisseur
   - Chiffre hero au centre: ~72px, 500, tabular
   - Label "READINESS" sous: 11px, small-caps, textMuted
   - Delta "+X vs hier": 13px, 500, couleur sémantique
4. **Metrics row** — 3 colonnes égales, séparateur hairline vertical
   - Nutrition: X / Y kcal + barre progression
   - Strain: chiffre (couleur sémantique) + "Fatigue musculaire"
   - Sommeil: "Xh XX" + "Score XX"
5. **Séance du jour** (ou Récupération) — card pleine largeur
   - Label "SÉANCE DU JOUR" + heure à droite (ou "RÉCUPÉRATION")
   - Titre séance: 22px, 700
   - Durée: 22px, 400 aligné droite
   - Description: 14px, 400, textMuted, 2 lignes max
   - Métriques secondaires (3 colonnes): Allure/Puissance, FC cible/NP, TSS
   - CTA "Démarrer la séance →" — pleine largeur, fond accent
6. **Tab bar** — 4 onglets V1: Accueil | Entraînement | Coach | Profil (Métriques = V2)

## Palette observée (depuis screenshots)

### Light mode
```
bg:          #F5F5F2    // "Fond off-white #F5F5F2"
surface:     #FAFAF7
surfaceAlt:  #EFEEE9
text:        #1A1815
textMuted:   #6B655D
textFaint:   #9A958C
accent:      oklch(0.62 0.14 55)   // warm amber (tab actif, CTA, liens)
accentText:  #FAFAF7
```

### Dark mode
```
bg:          #161412    // "Fond charbon chaud #161412"
surface:     #1F1D1A
surfaceAlt:  #282622
text:        #EDEAE3
textMuted:   #9A948A
textFaint:   #5E584F
accent:      oklch(0.72 0.14 65)
accentText:  #161412
```

### Sémantique physiologique
```
// Readiness ring + chiffres Strain/Sommeil — UNIQUEMENT
Green (≥85):   light #3F8A4A  /  dark #8FCB82
Yellow (70–84): utilise la couleur accent (amber)
Red (<70):     light #B64536  /  dark #E27A6F
```

## Typographie
- Famille: Space Grotesk
- Salutation: 28px, 700, tracking -0.5
- Date: 13px, 500, uppercase, tracking +0.12em
- Hero number (Readiness): ~72px, 500, tabular, tracking -2px
- Label "READINESS": 11px, 500, uppercase, tracking +0.14em
- Delta "+X vs hier": 13px, 500, tabular
- Metric labels (NUTRITION, STRAIN, SOMMEIL): 11px, 500, uppercase, tracking +0.14em
- Metric values: 17px, 500 (ou 600), tabular
- Session title: 22px, 700, tracking -0.3
- Session duration: 22px, 400, tabular
- Session description: 14px, 400
- Metric secondaires (ALLURE, FC CIBLE, TSS): label 10px small-caps / valeur 15px, 600, tabular

## Spacing et rythme
- Padding horizontal: 20px
- Header → ring: 20px
- Ring → metrics row: 24px
- Metrics row → card séance: 16px
- Padding interne card: 16px
- Gap entre sections dans la card: 12px

## Radii
- Card séance: 16px
- Card métriques: 14px
- Avatar initiales: 50% (cercle)
- Tab bar: 0 (pleine largeur)

## Ombres et élévations
Aucune ombre portée. Différenciation light/dark par la couleur de fond surface uniquement.

## Comportements interactifs

### Readiness ring
- Animée au montage: arc dessine de 0 à la valeur finale (600ms ease-out)
- En RN: `react-native-svg` + Animated ou `react-native-reanimated` pour le stroke-dashoffset
- Couleur de l'arc déterminée par le score: <70 rouge, 70–84 amber, ≥85 vert

### CTA "Démarrer la séance"
- Tap → navigate vers `todays-session` en passant les données de la séance
- Haptic: `ImpactFeedbackStyle.Medium` au tap

### Tab bar
- Icône + label, onglet actif: accent (icône + label)
- NativeTabs Expo (existant dans le projet)

### Récupération obligatoire (Readiness <70)
- Card remplace la Séance du jour
- CTA "Voir le protocole →" (ghost button, fond surfaceAlt)
- Pas de CTA accent → pas de session à démarrer

## Animations critiques
- Ring draw au montage: 600ms ease-out via stroke-dashoffset
- Metric values: counter animation 400ms si les données arrivent async
- En RN: `react-native-reanimated` withTiming

## Gestion clavier
Pas d'input sur cet écran. Sans objet.

## Safe area
- Top: status bar
- Bottom: tab bar (géré par NativeTabs) + home indicator

## Dépendances RN probables
- `react-native-svg` (anneau Readiness)
- `react-native-reanimated` v3 (animations ring et counters)
- `expo-haptics` (CTA tap)
- `@resilio/design-tokens`

## États à implémenter

| État | Déclencheur | Différences visuelles |
|---|---|---|
| Normal (Readiness 70–84) | Readiness dans la zone | Ring amber, Strain/Sommeil neutral |
| Journée idéale (≥85) | Readiness ≥ 85 | Ring vert, chiffres Strain en vert |
| Récupération obligatoire (<70) | Readiness < 70 | Ring rouge, card Récupération (pas de séance), CTA ghost |
| Loading | Données en cours | Skeleton screens sur ring + metrics |
| Séance de vélo | sport = cycling | Métriques Puissance / NP / TSS (vs Allure / FC / TSS course) |
| Séance lifting | sport = lift | Métriques Vol. / RPE / (pas de TSS) |

## Edge cases et questions ouvertes
- **Scroll**: la page défile-t-elle ? Le bas de la card séance montre un CTA "Démarrer la séance →" partiellement rogné, suggérant qu'il y a du contenu sous la fold. **À trancher: ScrollView ou hauteur fixe ?**
- **CHARGE COGNITIVE** (visible en bas): il y a un indicateur en bas des screenshots. Semble être une barre de progression. Non documenté dans le code disponible. **À clarifier.**
- **5e onglet Profile**: visible dans les screenshots comme icône personne mais sans label "Profile". Confirmer si c'est une modale ou un écran tab.

## Anti-patterns à éviter pour cette page
- Pas de gradient sur la readiness ring
- Couleurs sémantiques (green/yellow/red) uniquement sur Readiness ring + Strain + Sommeil — jamais sur l'UI chrome
- Le fond dark est #161412, PAS #08080e (trop clinique)
- Pas de ombre sur les cards
