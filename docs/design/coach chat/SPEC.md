# Coach Chat — Spec d'implémentation

## Source de vérité
- `screenshots/coach chat - conversation.png` — conversation light + HITL sheet dark
- `screenshots/coach chat - multichoice question.png` — sheet multi-choix light + dark
- `screenshots/coach chat - options question.png` — sheet choix unique light + dark (avec option sélectionnée)
- `screenshots/coach chat - order question.png` — sheet réordonnage light + dark
- `coach-chat.jsx` — code source conversation + bubble styles
- `hitl-sheet.jsx` — code source HITL bottom sheet

> **REFERENCES externes (uploads/):** Les images dans `uploads/` montrent un pattern HITL d'un autre projet (projet "Jules", "Claude Code agent", etc.). **Ignorer le contenu textuel.** Seul le pattern visuel (question + options numérotées + Passer / → ) est de l'inspiration structurelle. La cible est le comportement des screenshots `coach chat - *.png`.

> **NOTE**: les screenshots de la conversation sont blurés en dark (effet intentionnel — le chat est flou derrière la sheet active). Le détail exact de la bulle chat dark n'est pas visible. Inférences basées sur le code source.

## Aperçu visuel
Écran chat avec le Head Coach IA. Conversation classique (bulles coach + bulles utilisateur). Quand le coach pose une question structurée (HITL), un bottom sheet s'ouvre par-dessus le chat avec les options. 3 types de questions: choix unique, multi-choix, réordonnage.

## Structure

### Conversation
1. **Status bar** iOS
2. **Navigation bar**: `<` retour gauche, "Head Coach" centré (17px, 600), `...` menu droite
3. **Date separator**: "AUJOURD'HUI" — small-caps, 11px, textDim, centré
4. **Bulles coach (HC)**:
   - Fond surfaceMuted, radius 18px (coin bas-gauche 4px)
   - Avatar "HC" petit cercle à gauche (26px, textSec, surfaceSubtle)
   - Texte 15px, 400, ink
   - Timestamp en bas: 12px, textDim
5. **Bulles utilisateur** (non visible dans les screenshots mais en code):
   - Fond userBubble (#3A3530 dark / surface light)
   - Alignées à droite, radius 18px (coin bas-droit 4px)
6. **Bouton "Reprendre les questions"** (état: sheet fermée, questions en cours):
   - Fond accent, texte white, 44px, radius 22px, auto-width, centré
7. **Barre quick-replies** (chips): "Adapte ma semaine", "Pourquoi cette séance ?", "Je m[oins]..."
   - Chips ghost border, 34px, radius 17px, 13px
8. **Input "Écris au coach..."**:
   - Fond surfaceMuted, radius 22px, 44px height
   - Placeholder 14px, textDim
   - Bouton send ↑ à droite: cercle 30px, fond accent, arrow-up icon

### HITL Bottom Sheet

Overlay: chat derrière = flou (`BlurView` expo-blur) + dim overlay (rgba dark ~0.5)

**Header du sheet**:
- Question: 18px, 700, tracking -0.3 (2 lignes max)
- Compteur: "< X / Y >" — flèches navigation + compteur centré — textMuted, 14px
- Bouton fermer `×` aligné droite — 28px, textMuted

**Corps selon le type**:

#### Type 1 — Choix unique
- Liste de rows numérotés (1, 2, 3, 4...)
- Numéro: pill 28px, fond surfaceSubtle, texte 13px
- Label: 15px, 400
- Flèche `→` à droite sur la row hovered/sélectionnée
- État sélectionné: row avec fond surfaceSubtle, numéro pill sombre, label bold, `→` apparent
- Ligne "Autre chose" en bas: icône crayon, placeholder textDim, 14px

#### Type 2 — Multi-choix
- Rows avec checkbox à gauche
- Checkbox: 22px, border 1.5px, radius 6px
- Cochée: fond accent, check blanc
- Label: 15px, 400
- Compteur "X sélectionné(s)" en bas à gauche — 13px, textMuted

#### Type 3 — Réordonnage
- Rows avec numéro fixe à gauche (position courante) et handle `⋮⋮` à droite
- "GLISSE POUR RÉORDONNER" — small-caps, textFaint, 11px, en bas de la liste
- Drag: react-native-draggable-flatlist

**Footer du sheet**:
- Gauche: bouton "Passer" — ghost, fond transparent, 40px, 14px, 500
- Droite: bouton `→` — cercle 44px, fond accent (actif) ou surfaceSubtle (inactif), arrow-right icon

## Palette observée (depuis screenshots + code source)

### Light mode
```
bg:            #F5F5F2
bgElev:        #FBFBF9
surface:       #FFFFFF       // sheet fond
surfaceMuted:  #EDEBE5       // bulles coach, input
surfaceSubtle: #E8E5DE       // numéro pills, row hover
text:          #1A1612
textMuted:     #6B645A
textDim:       #9B948A
accent:        #B8552E       // bouton send, bouton →, chips actifs
accentSoft:    rgba(184,85,46,0.08)
accentBorder:  rgba(184,85,46,0.28)
online:        #3C9A5F       // indicateur Head Coach en ligne
```

### Dark mode
```
bg:            #1A1715
bgElev:        #211E1B
surface:       #26231F       // sheet fond
surfaceMuted:  #2C2824       // bulles coach
surfaceSubtle: #332E29       // numéro pills
text:          #F2EFE9
textMuted:     #A39B90
textDim:       #6B645A
accent:        #D97A52
accentSoft:    rgba(217,122,82,0.12)
accentBorder:  rgba(217,122,82,0.32)
online:        #4FB874
userBubble:    #3A3530
```

## Typographie
- Famille: Space Grotesk
- Titre question: 18px, 700, tracking -0.3
- Label option: 15px, 400
- Numéro option: 13px, 600
- Input placeholder: 14px, 400
- Chips: 13px, 400 ou 500
- Compteur selection: 13px, 400, textMuted
- Timestamp bulles: 12px, 400, textDim
- Label compteur "X / Y": 14px, 400, textMuted

## Spacing et rythme
- Padding horizontal sheet: 20px
- Gap entre rows options: 0 (séparateur hairline 1px)
- Hauteur row option: 52–56px
- Gap header question → première option: 16px
- Padding footer: 16px horizontal, 12px vertical
- Padding-bottom footer: safe area

## Radii
- Bottom sheet: 20px top corners
- Checkbox: 6px
- Numéro pill: 14px (cercle ou arrondi)
- Bouton → footer: 50% (cercle)
- Bouton send input: 50% (cercle)
- Input chat: 22px
- Bulles coach: 18px, coin bas-gauche 4px
- Bulles user: 18px, coin bas-droit 4px

## Ombres et élévations
- Sheet: pas d'ombre portée — délimitation par le contraste de fond
- Overlay dim derrière la sheet: rgba dark, opacité ~0.5

## Comportements interactifs

### Ouverture HITL sheet
- Le coach envoie ses messages, puis le sheet s'ouvre automatiquement (push depuis le serveur ou après délai)
- Bouton "Reprendre les questions" si l'utilisateur a fermé le sheet sans répondre

### Navigation entre questions
- `<` et `>` permettent de naviguer entre les questions de la séquence
- L'état sélectionné est mémorisé si l'on revient en arrière

### Fermeture du sheet
- `×` ou swipe down
- Ne valide pas les réponses — "Passer" est l'action de passage

### Validation (bouton →)
- Actif: quand au moins 1 choix fait (type 1 et 2) ou toujours actif (type 3)
- Inactif: fond surfaceSubtle (pas de opacity — cf. code source)
- Tap → envoie la réponse, passe à la question suivante ou ferme si dernière

### Choix unique — tap sur row
- Sélection immédiate, `→` apparaît
- Tap sur une autre row: désélectionne la précédente

### Multi-choix — tap sur row
- Toggle checkbox
- Compteur mis à jour

### Réordonnage — drag
- `react-native-draggable-flatlist` — longPress pour activer le drag
- Handle `⋮⋮` à droite visible en permanence (pas de swipe)

## Animations critiques
- Sheet open: slide-up 300ms spring (react-native-reanimated)
- BlurView: apparaît avec le sheet
- Checkbox check: scale bounce 200ms (reanimated)
- Transition entre questions du sheet: slide horizontal (X+1 entre par la droite)

## Gestion clavier
- Input chat: `KeyboardAvoidingView` behavior `padding` sur iOS
- Quand sheet est ouverte: input chat caché (sheet prend tout l'espace)

## Safe area
- Top: status bar
- Bottom: input chat + home indicator; footer sheet + home indicator

## Dépendances RN probables
- `@gorhom/bottom-sheet` (HITL sheet, snap points 50% et 95%)
- `expo-blur` `BlurView` (fond flou derrière sheet)
- `react-native-draggable-flatlist` (type ordre)
- `react-native-reanimated` v3
- `expo-haptics` (tap option, drag)
- `react-native-safe-area-context`
- `@resilio/design-tokens`

## États à implémenter

| État | Description |
|---|---|
| Conversation seule | Pas de sheet, chat scrollable, quick-replies visibles |
| Sheet ouvert — type 1 | 4 options, aucune sélectionnée |
| Sheet ouvert — type 1 | Option sélectionnée, bouton → actif |
| Sheet ouvert — type 2 | Checkboxes, 0 coché (→ inactif) |
| Sheet ouvert — type 2 | 1+ coché, compteur "X sélectionné(s)" |
| Sheet ouvert — type 3 | Liste draggable, drag en cours |
| Questions en cours mais sheet fermé | Bouton "Reprendre les questions" visible |
| Dernière question validée | Sheet se ferme, coach envoie réponse |
| Saisie libre | Input actif, bouton send actif |

## Edge cases et questions ouvertes
- **Sheet partiellement ouvert**: @gorhom permet snap à 50% ou 95%. Les screenshots montrent le sheet à ~60% de hauteur. Valeur exacte ? **À mesurer.**
- **Scroll dans le sheet**: si plus de 5 options, la liste scrolle-t-elle ? Comportement du footer (sticky ?) **À trancher.**
- **Chat blurriness**: le chat est intentionnellement flou derrière la sheet. Intensité du blur ? `intensity={20}` sur expo-blur ? **À trancher.**
- **Sheet depuis serveur**: comment le backend push-t-il la question ? WebSocket ou polling ? Hors scope de ce SPEC (backend concern).

## Anti-patterns à éviter pour cette page
- Pas de Modal transparent seul pour la sheet — utiliser @gorhom/bottom-sheet (voir session log: HITLSheet Modal RN seul ne fonctionne pas avec onRequestClose)
- Pas de "Envoyer" ou "Valider" comme label — uniquement flèche `→`
- Pas de fond accent derrière les numéros de choix à l'état par défaut — surfaceSubtle seulement
- Pas d'animation cosmétique sur les bulles chat existantes quand le sheet s'ouvre
