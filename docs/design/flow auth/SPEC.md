# Flow Auth — Spec d'implémentation

## Source de vérité
- `screenshots/flow auth - light-dark.png` — états login light et dark
- `screenshots/flow auth - steps.png` — système de design + états login (empty, filled, keyboard, loading)
- `screenshots/flow auth - account creation.png` — signup light + dark
- `screenshots/flow auth - reset password.png` — forgot password light + dark
- `auth-screens.jsx` — code source complet avec tokens

## Aperçu visuel
3 écrans auth (Login, Signup, Forgot Password) partageant la même palette et structure. Layout centré, aucun fond photo, aucun gradient. Titre h1 aligné gauche, inputs floating-label, CTA pleine largeur.

## Structure

### Login
1. **Status bar** — iOS natif
2. **Wordmark** — "Resilio+" centré, 17px 600, accent sur le "+"
3. **Titre** — "Connexion" — 32px 700, aligné gauche, padding 24px horizontal
4. **Inputs** — Email puis Mot de passe (avec toggle show/hide), floating-label
5. **Lien** — "Mot de passe oublié" aligné droite, couleur accent
6. **CTA primaire** — "Se connecter" — pleine largeur, 54px, radius 12
7. **Séparateur** — "ou" centré
8. **Apple Sign In** — noir/blanc selon mode, 54px, radius 12
9. **Footer** — "Pas de compte ? Créer un compte" — lien accent centré
10. **Home indicator** — iOS natif

### Signup
Identique Login sauf: titre "Créer un compte", 3 inputs (email, mdp, confirmation), texte légal sous CTA, footer "Déjà un compte ?".

### Forgot Password
Titre multiline "Réinitialiser le mot de passe", sous-titre déclaratif, 1 input email, CTA "Envoyer le lien". État post-envoi: bloc confirmation inline (icône enveloppe + "Email envoyé / Expire dans 30 minutes.") + bouton "Renvoyer". Footer "Revenir à la connexion" (accent).

## Palette observée (depuis screenshots)

### Light mode
```
bg:             #F5F5F2    // off-white warm
surface input:  transparent (border visible)
text:           #1A1A17
textSecondary:  #6B6862
textTertiary:   #9A968D
border:         #E3E0D8
borderFocus:    accent
accent:         oklch(0.62 0.14 35)  // ≈ #C06040 warm amber
accentPressed:  oklch(0.56 0.14 35)
onAccent:       #FAFAF7
apple btn:      #000000 bg, #FFFFFF text
divider:        #E8E6E0
```

### Dark mode
```
bg:             #17171A    // warm charcoal, NOT clinical
surface:        #1F1F22
text:           #F0EEE8
textSecondary:  #9E9A90
textTertiary:   #6B6862
border:         #2E2D2A
borderFocus:    accent
accent:         oklch(0.68 0.13 38)  // slightly brighter
accentPressed:  oklch(0.62 0.13 38)
onAccent:       #17171A
apple btn:      #FFFFFF bg, #000000 text
divider:        #262523
```

## Typographie
- Famille: Space Grotesk
- Wordmark: 17px, 600, tracking -0.3 — accent sur "+"
- Titre h1: 32px, 700, tracking ≤ -0.5
- Label floating (small-caps): 11px, 500, uppercase, tracking +0.14em — apparaît quand input rempli/focus
- Placeholder: 15px, 400, textTertiary
- Input value: 15px, 400
- Bouton CTA: 16px, 600
- Liens accent: 14px, 400 (footer) / 14px, 500 (mot de passe oublié)
- Texte légal signup: 12px, 400, textTertiary — liens soulignés

## Spacing et rythme
- Padding horizontal écran: 24px
- Gap entre inputs: 14px
- Gap inputs → lien MDP: 10px
- Gap lien MDP → CTA: 20px
- Gap CTA → séparateur: 20px
- Gap séparateur → Apple btn: 20px
- Footer ancré bas (flex-grow sur espace entre content et footer)

## Radii
- Inputs: 10px
- CTA primaire: 12px
- Apple btn: 12px
- Bloc confirmation ("Email envoyé"): 12px

## Ombres et élévations
Aucune ombre sur les éléments auth. Surface flat.

## Comportements interactifs

### Inputs
- Floating label: placeholder devient label small-caps en haut de l'input au focus ou quand rempli
- Border: 1px neutral → 1.5px accent au focus (compensation margin -0.5px pour éviter le layout shift)
- Transition border: 120ms ease
- Password: icône œil toggle show/hide

### CTA
- Loading state: spinner centré sur fond accent (icône ↻, pas de texte)
- Désactivé si champs vides: opacité réduite (À trancher: 50% ou 40%)

### Apple Sign In
- Couleur inverse au changement de mode (noir en light, blanc en dark)

### Forgot Password — post-submit
- Input email disparaît
- Apparition inline du bloc confirmation (pas de modal)
- Bouton "Renvoyer" (ghost, pleine largeur, radius 12)

## Animations critiques
- Float label: translateY + scale sur le label, 150ms ease-out
- En RN: `react-native-reanimated` withTiming sur translateY et fontSize

## Gestion clavier
- `KeyboardAvoidingView` behavior `padding` sur iOS
- Footer "Pas de compte" sort du scroll quand clavier ouvert — l'input actif doit rester visible
- Login: focus auto sur email au montage

## Safe area
- Top: status bar natif iOS
- Bottom: home indicator — bouton Apple et footer doivent être au-dessus

## Dépendances RN probables
- `expo-apple-authentication` (Apple Sign In)
- `react-native-reanimated` v3 (floating label animation)
- `react-native-safe-area-context`
- `@resilio/design-tokens` (palette)

## États à implémenter

| Écran | États |
|---|---|
| Login | empty, filled, focus email, focus password (keyboard visible), loading, error (À trancher: inline ou toast) |
| Signup | empty, filled partiel, filled complet, erreur confirmation mdp |
| Forgot Password | initial, loading, sent (bloc confirmation), renvoyer |

## Edge cases et questions ouvertes
- **Erreur auth**: position du message d'erreur non montrée dans les screenshots. Inline sous l'input fautif ou toast en bas ? **À trancher avec l'auteur.**
- **Validation temps réel**: signup — valider la confirmation mdp au blur ou au submit ? Screenshots ne montrent pas l'état erreur.
- **Accessibilité**: contraste du label floating en état par défaut (textTertiary) doit être vérifié AA.

## Anti-patterns à éviter pour cette page
- Pas de fond coloré / gradient derrière les inputs
- Pas de modal pour la confirmation "email envoyé" — réponse inline uniquement
- Pas de border-radius pill (50%) sur les boutons
- Apple Sign In couleur DOIT s'inverser selon le mode — jamais toujours noir
