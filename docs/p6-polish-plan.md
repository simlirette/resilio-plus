# P6 Polish — Plan Phase 2
_Branche: `chore/downgrade-sdk54` | 2026-04-19_
_Diagnostic: `docs/p6-polish-diagnostic.md` (v2, validé)_

---

## Ordre des commits

```
Commit 1 — bug 3 (CognitiveLoadBar header)             index.tsx
Commit 2 — bug 1 (ring number 52px)                    index.tsx
Commit 3 — bug 2 (Fatigue musculaire wrap)             index.tsx
Commit 4 — bug 4 (week headers 2 lignes)               training.tsx
Commit 5 — bug 6 (NativeTabs + hex cleanup)            (tabs)/_layout.tsx
Commit 6 — bug 5 (rank PanResponder drag)              chat.tsx
Push après chaque commit.
```

---

## Commit 1 — Bug 3 : CognitiveLoadBar header

**Fichier :** `apps/mobile/app/(tabs)/index.tsx`

### Changements

Dans `CognitiveLoadBar` (ligne ~312 dans le fichier actuel) :

**Supprimer** le bloc header entier :
```tsx
<View style={s.cogHeader}>
  <Text variant="label" color={themeColors.textMuted} style={s.cogTitle}>
    CHARGE COGNITIVE
  </Text>
  <Text variant="label" color={themeColors.textMuted} style={[s.tabular, { fontSize: 11 }]}>
    7j
  </Text>
</View>
```

**Modifier** la ligne "Charge allostatique" (juste après) — passer de `textMuted` à `foreground` :
```tsx
// AVANT
<Text variant="label" color={themeColors.textMuted} style={s.cogSub}>
  Charge allostatique
</Text>

// APRÈS
<Text variant="label" color={themeColors.foreground} style={s.cogSub}>
  Charge allostatique
</Text>
```

**Supprimer** le style `cogHeader` et `cogTitle` dans `StyleSheet.create` (s'ils ne sont plus référencés).

### Checklist commit 1
- [ ] "CHARGE COGNITIVE" absent du rendu
- [ ] "Charge allostatique" visible, couleur `foreground` (blanc/warm charcoal)
- [ ] "7j" absent
- [ ] `git grep "CHARGE COGNITIVE" apps/mobile/app/\(tabs\)/index.tsx` → 0

---

## Commit 2 — Bug 1 : Ring number 52px

**Fichier :** `apps/mobile/app/(tabs)/index.tsx`

**Mesure référence :** design montre "78" à ~75px / ring 155px = 48%. Notre 72px fidèle au design mais trop dominant sur device. Cible : 52px.

> **Note plan :** 52px = première itération. Si jugé inadéquat après test Expo Go (trop petit ou encore trop grand), un sous-commit d'ajustement (cible 52–60px) est autorisé sans nouveau cycle diagnostic/plan.

### Changement

Dans `s.ringValue` (ligne ~530) :
```tsx
// AVANT
ringValue: {
  fontSize: 72,
  fontFamily: 'SpaceGrotesk_500Medium',
  letterSpacing: -3.5,
  lineHeight: 78,
  fontVariant: ['tabular-nums'],
},

// APRÈS
ringValue: {
  fontSize: 52,
  fontFamily: 'SpaceGrotesk_500Medium',
  letterSpacing: -2.5,
  lineHeight: 58,
  fontVariant: ['tabular-nums'],
},
```

(letterSpacing et lineHeight ajustés proportionnellement.)

### Checklist commit 2
- [ ] Chiffre "78" visuellement moins dominant, confortable dans le ring 160px
- [ ] Pas de clip ou overlap avec "READINESS" label en dessous
- [ ] TypeScript clean (aucun changement de type)

---

## Commit 3 — Bug 2 : Fatigue musculaire wrap

**Fichier :** `apps/mobile/app/(tabs)/index.tsx`

**Problème :** `Fatigue\nmusculaire` wrap sur 3 lignes sur certains appareils (orphan "e" en 3e ligne).

**Décision :** `numberOfLines={2}` sans modifier le texte ni `adjustsFontSizeToFit`. Si après ce changement le texte wrap encore mal (orphan persistant), élargir la colonne STRAIN en réduisant `flex` de la colonne NUTRITION (qui a plus de marge textuelle). Cette logique conditionnelle est documentée ici pour éviter un cycle plan.

### Changement principal

Dans `MetricsStrip`, colonne STRAIN (ligne ~168) :
```tsx
// AVANT
<Text variant="label" color={themeColors.textMuted} style={[s.stripSub, { lineHeight: 15 }]}>
  Fatigue{'\n'}musculaire
</Text>

// APRÈS
<Text variant="label" color={themeColors.textMuted} style={[s.stripSub, { lineHeight: 15 }]} numberOfLines={2}>
  Fatigue musculaire
</Text>
```

Changements : suppression du `{'\n'}` explicite (laisser le wrap naturel) + `numberOfLines={2}`.

### Fallback si wrap toujours cassé

Modifier `s.stripCol` pour donner plus de flex à STRAIN :
```tsx
// Version fallback — uniquement si numberOfLines={2} insuffisant
// NUTRITION col: flex: 0.9
// STRAIN col: flex: 1.2
// SOMMEIL col: flex: 0.9
```

Ne pas implémenter le fallback par défaut — tester d'abord.

### Checklist commit 3
- [ ] "Fatigue musculaire" sur exactement 2 lignes max sur iPhone SE et Pro Max
- [ ] Pas de tronquage visible du texte (les 2 lignes s'affichent)
- [ ] Column widths inchangées (fallback non utilisé)

---

## Commit 4 — Bug 4 : Week headers 2 lignes

**Fichier :** `apps/mobile/app/(tabs)/training.tsx`

### Texte verbatim
- **L1 :** `SEMAINE DU 13 AVRIL` (pleine orthographe, uppercase, pas d'abréviation)
- **L2 :** `7 SÉANCES - 7H05 TOT. - 381 CHARGE` (tiret simple ` - `, "TOT." présent, "SÉANCES" et "CHARGE" uppercase)

### Changements

**1. `weekLabel` (ligne ~477) :**
```tsx
// AVANT
const weekLabel = `SEM. DU ${monday.getDate()} ${monday.toLocaleDateString('fr-FR', { month: 'short' }).replace('.', '').toUpperCase()}`;

// APRÈS
const weekLabel = `SEMAINE DU ${monday.getDate()} ${monday.toLocaleDateString('fr-FR', { month: 'long' }).toUpperCase()}`;
```

**2. `summary` (ligne ~478) :**
```tsx
// AVANT
const summary = `${totalSessions} séance${totalSessions !== 1 ? 's' : ''} · ${fmtDur(totalVol)} · ${totalLoad} charge`;

// APRÈS
const summary = `${totalSessions} SÉANCE${totalSessions !== 1 ? 'S' : ''} - ${fmtDur(totalVol).toUpperCase()} TOT. - ${totalLoad} CHARGE`;
```

**3. Layout `weekHeader` (lignes ~482–485) — row → column :**
```tsx
// AVANT
<View style={[styles.weekHeader, isFirst && styles.weekHeaderFirst, { borderBottomColor: themeColors.border }]}>
  <Text variant="label" color={themeColors.textMuted}>{weekLabel}</Text>
  <Text variant="label" color={themeColors.textMuted}>{summary}</Text>
</View>

// APRÈS
<View style={[styles.weekHeader, isFirst && styles.weekHeaderFirst, { borderBottomColor: themeColors.border }]}>
  <Text variant="label" color={themeColors.foreground} style={styles.weekL1}>{weekLabel}</Text>
  <Text variant="label" color={themeColors.textMuted} style={styles.weekL2}>{summary}</Text>
</View>
```

**4. Styles `weekHeader` (ligne ~732) :**
```tsx
// AVANT
weekHeader: {
  flexDirection: 'row',
  justifyContent: 'space-between',
  alignItems: 'center',
  paddingHorizontal: 20,
  paddingTop: 20,
  paddingBottom: 8,
  borderBottomWidth: StyleSheet.hairlineWidth,
},

// APRÈS
weekHeader: {
  flexDirection: 'column',
  alignItems: 'flex-start',
  paddingHorizontal: 20,
  paddingTop: 20,
  paddingBottom: 8,
  borderBottomWidth: StyleSheet.hairlineWidth,
},
weekL1: {
  fontSize: 12,
  fontFamily: 'SpaceGrotesk_600SemiBold',
  letterSpacing: 0.8,
  marginBottom: 2,
},
weekL2: {
  fontSize: 11,
  fontFamily: 'SpaceGrotesk_400Regular',
  letterSpacing: 0.2,
},
```

### Checklist commit 4
- [ ] L1 = "SEMAINE DU 13 AVRIL" (mois complet, pleine orthographe)
- [ ] L2 = "N SÉANCES - Xh0Y TOT. - Z CHARGE"
- [ ] Séparateur ` - ` (tiret simple, espaces)
- [ ] "TOT." présent dans L2
- [ ] Layout 2 lignes empilées (pas side-by-side)
- [ ] TypeScript clean

---

## Commit 5 — Bug 6 : NativeTabs restoration + hex cleanup

**Fichier :** `apps/mobile/app/(tabs)/_layout.tsx`
**Backup avant modification :** `_layout.tsx.backup-polish`

### Contexte
- NativeTabs disponible via `expo-router/unstable-native-tabs` sur SDK 54 ✅
- Commit de référence : `e2d1810` (pattern complet validé)
- Régression : commentaire incorrect "SDK 55 only" dans un commit post-e2d1810

### Routes actuelles (4 tabs)
`index` | `training` | `chat` | `profile`
(PAS `check-in` — différence vs e2d1810)

### SF Symbols adaptés
| Route | SF default | SF selected |
|---|---|---|
| index | `house` | `house.fill` |
| training | `calendar` | `calendar.fill` |
| chat | `message` | `message.fill` |
| profile | `person` | `person.fill` |

### Nouveau `_layout.tsx` complet
```tsx
import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { colors } from '@resilio/design-tokens';

/**
 * Tab bar layout using NativeTabs (expo-router/unstable-native-tabs).
 * iOS: UITabBarController with liquid glass (systemChromeMaterial blur).
 * Android: Material 3 bottom navigation.
 * Web: Radix UI tabs fallback (built into expo-router).
 *
 * SF Symbols: tab bar only (exception to Lucide-only rule — native iOS integration).
 * tintColor: colors.accent (amber #B8552E).
 * Confirmed working on SDK 54 (see commit e2d1810).
 */
export default function TabsLayout() {
  return (
    <NativeTabs
      tintColor={colors.accent}
      blurEffect="systemChromeMaterial"
    >
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Accueil</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'house', selected: 'house.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="training">
        <NativeTabs.Trigger.Label>Entraînement</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'calendar', selected: 'calendar.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="chat">
        <NativeTabs.Trigger.Label>Coach</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'message', selected: 'message.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="profile">
        <NativeTabs.Trigger.Label>Profil</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'person', selected: 'person.fill' }}
        />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
```

### Checklist commit 5
- [ ] Backup `_layout.tsx.backup-polish` créé
- [ ] `git grep "#[0-9a-fA-F]" apps/mobile/app/\(tabs\)/_layout.tsx` → 0
- [ ] `git grep "rgba" apps/mobile/app/\(tabs\)/_layout.tsx` → 0
- [ ] 4 routes correctes : index, training, chat, profile
- [ ] Aucun import `useTheme` ou `Icon` résiduel
- [ ] TypeScript clean (`pnpm --filter @resilio/mobile typecheck`)

---

## Commit 6 — Bug 5 : Rank PanResponder drag

**Fichier :** `apps/mobile/app/(tabs)/chat.tsx`
**Backup avant modification :** `chat.tsx.backup-polish`

### Contexte actuel
- `RankRow` (ligne ~825) utilise ↑↓ `TouchableOpacity` buttons
- Hint : "APPUIE ↑ ↓ POUR RÉORDONNER" (ligne ~593)
- Design cible : drag handle `⋮⋮` à droite, "GLISSE POUR RÉORDONNER"

### Architecture PanResponder — vrai drag-and-drop

**State dans HITLSheet :**
```tsx
const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
const dragY = useRef(new Animated.Value(0)).current;
const ROW_HEIGHT = 52; // px — hauteur d'un slot pour calcul multi-position
```

**Props `RankRow` (remplace onMoveUp/onMoveDown) :**
```tsx
interface RankRowProps {
  t: typeof CHAT_TOKENS.dark;
  index: number;
  label: string;
  isDragging: boolean;
  dragYValue: Animated.Value;       // shared ref depuis le parent
  onDragStart: (index: number) => void;
  onDragMove: (dy: number) => void;
  onDragEnd: (dy: number) => void;
}
```

**PanResponder par row (dans RankRow) :**
```tsx
const panRef = useRef(
  PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onPanResponderGrant: () => {
      onDragStart(index);
      Haptics.impactAsync(ImpactFeedbackStyle.Light); // pickup
    },
    onPanResponderMove: (_, gs) => {
      onDragMove(gs.dy); // parent: dragY.setValue(gs.dy)
    },
    onPanResponderRelease: (_, gs) => {
      onDragEnd(gs.dy); // parent: calcule new index + swap
    },
  })
).current;
```

**Visuel — row suit le doigt en temps réel :**
```tsx
const animatedStyle = isDragging ? {
  transform: [{ translateY: dragYValue }],
  zIndex: 10,
  elevation: 4,
  shadowOpacity: 0.15,
  shadowRadius: 8,
  shadowOffset: { width: 0, height: 2 },
  opacity: 0.95,
} : {};

return (
  <Animated.View style={[s.rankRow, animatedStyle]}>
    <Text style={[s.rankNum, { color: t.textDim }]}>{index + 1}</Text>
    <Text style={[s.rankLabel, { color: t.text }]} numberOfLines={2}>{label}</Text>
    <View {...panRef.panHandlers} style={s.rankHandle}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
      <GripDots color={t.textMuted} />
    </View>
  </Animated.View>
);
```

**Handlers dans HITLSheet :**
```tsx
const handleDragStart = (index: number) => {
  setDraggingIndex(index);
};

const handleDragMove = (dy: number) => {
  dragY.setValue(dy);
};

const handleDragEnd = (dy: number) => {
  const fromIdx = draggingIndex;
  if (fromIdx !== null) {
    const slotsMoved = Math.round(dy / ROW_HEIGHT);
    if (slotsMoved !== 0) {
      const toIdx = Math.max(0, Math.min(rankOrder.length - 1, fromIdx + slotsMoved));
      if (fromIdx !== toIdx) {
        const newRanks = [...rankOrder];
        const [moved] = newRanks.splice(fromIdx, 1);
        newRanks.splice(toIdx, 0, moved);
        setRankOrder(newRanks);
        Haptics.impactAsync(ImpactFeedbackStyle.Medium); // drop réussi uniquement
      }
    }
  }
  // Reset — spring natif
  setDraggingIndex(null);
  Animated.spring(dragY, {
    toValue: 0,
    useNativeDriver: true,
    damping: 20,
    stiffness: 300,
  }).start();
};
```

**`GripDots` component (6 dots 2×3) :**
```tsx
function GripDots({ color }: { color: string }) {
  return (
    <View style={{ flexDirection: 'row', gap: 3 }}>
      {[0, 1].map(col => (
        <View key={col} style={{ gap: 4 }}>
          {[0, 1, 2].map(row => (
            <View key={row} style={{ width: 3, height: 3, borderRadius: 1.5, backgroundColor: color }} />
          ))}
        </View>
      ))}
    </View>
  );
}
```

**Styles :**
```tsx
rankHandle: { width: 24, height: 44, justifyContent: 'center', alignItems: 'center' }
```

**Hint mis à jour :**
```tsx
// AVANT
<Text style={[s.rankHint, { color: t.textDim }]}>APPUIE ↑ ↓ POUR RÉORDONNER</Text>
// APRÈS
<Text style={[s.rankHint, { color: t.textDim }]}>GLISSE POUR RÉORDONNER</Text>
```

**Import :**
```tsx
import { ..., PanResponder, Animated } from 'react-native';
```

### Points critiques
- `useNativeDriver: true` sur le spring reset du dragY (translateY est native-driver compatible)
- Haptics.Light au pickup (onPanResponderGrant), Haptics.Medium au drop réussi (swap effectif), ZÉRO si pas de swap
- Multi-position swap en un seul drag (slotsMoved peut être ±2, ±3…)
- Les autres rows ne s'animent PAS pour faire de la place (simplification V1 — "ghost row qui flotte"). Réorganisation au release.

### Checklist commit 6
- [ ] Backup `chat.tsx.backup-polish` créé
- [ ] Handle `⋮⋮` visible à droite de chaque row (2 colonnes × 3 dots, couleur `textMuted`)
- [ ] Row suit le doigt en temps réel (translateY = gs.dy)
- [ ] Swap multi-position en un seul drag (ex: drag 156px → ±3 slots)
- [ ] Haptics.Light pickup, Haptics.Medium drop, ZÉRO si pas de swap
- [ ] Spring reset dragY → 0 après release
- [ ] Ombre/élévation visible sur la row en cours de drag
- [ ] Hint = "GLISSE POUR RÉORDONNER"
- [ ] Aucun ↑↓ arrow ou mention "APPUIE" dans le fichier
- [ ] TypeScript clean
- [ ] Expo Go SDK 54 safe : aucun import reanimated ni draggable-flatlist

---

## Post-commits

```bash
git push origin chore/downgrade-sdk54
```

Puis : tests Expo Go iPhone sur les 6 bugs corrigés.
