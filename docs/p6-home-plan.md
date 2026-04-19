# P6 — Home Dashboard Rewrite Plan
_Branche: `chore/downgrade-sdk54` | Source: `docs/design/homedashboard/`_

---

## Ordre des commits (final)

```
Commit 0 — design-tokens: accentText + accentTextDark
Commit 1 — mock home-dashboard-mock.ts
Commit 2 — index.tsx rewrite complet
git push origin chore/downgrade-sdk54
```

---

## Précisions préliminaires

### Tab bar — déjà correct, ne pas toucher
`apps/mobile/app/(tabs)/_layout.tsx` a **4 onglets V1**: Accueil | Entraînement | Coach | Profil.
Les screenshots du design montrent 5 onglets (avec Métriques) mais le SPEC dit "Métriques = V2"
et la décision session-log confirme le rejet du 5e tab pour V1.
**Aucune modification de `_layout.tsx` ou du tab bar.**

### Composants partagés ui-mobile — candidats à la suppression future
Ces composants ne seront plus importés par home après P6.
**NE PAS les supprimer maintenant** — ils pourraient servir dans Metric Detail ou Today's Session (passe future).
Les marquer ici pour décision après test Expo Go de P6:
- `MetricRow.tsx` — candidat suppression
- `SessionCard.tsx` — candidat suppression
- `CognitiveLoadDial.tsx` — candidat suppression
- `ReadinessStatusBadge.tsx` — candidat suppression

### Toggle 3 états — tap sur avatar "SR"
Tap sur le cercle avatar "SR" dans le header → cycle entre les 3 états mock:
`'normal'` (78) → `'ideal'` (92) → `'recovery'` (45) → `'normal'`
State local `useState` dans le composant — pas de rebuild requis.

### Animations — contrainte Expo Go SDK 54
Pas de `react-native-reanimated`. L'anneau Readiness **ne s'anime pas au montage** (skip l'animation stroke-dashoffset). Rendu immédiat à la valeur finale. Acceptable pour Expo Go.

---

## Commit 0 — design-tokens accent text

**Fichier cible:** `packages/design-tokens/src/colors.ts`

Ajouter dans `export const colors`:
```ts
accentText: '#FAFAF7',      // texte sur fond accent (light + dark)
accentTextDark: '#161412',  // texte sur fond accent dark (fond sombre = texte sombre)
```

Usage dans HomeSessionCard CTA:
```ts
const ctaTextColor = colorMode === 'dark' ? colors.accentTextDark : colors.accentText;
```

Checklist:
- [ ] `pnpm --filter @resilio/design-tokens build` (ou typecheck) passe
- [ ] `git grep "accentText"` retourne les 2 nouvelles lignes

---

## Commit 1 — Mock data

**Fichier cible:** `apps/mobile/src/mocks/home-dashboard-mock.ts` (nouveau)

Ne pas modifier `athlete-home-stub.ts` ni `types/home.ts` — ils peuvent servir ailleurs.

### Type `HomeDashData`

```ts
interface SessionTarget { label: string; value: string; }

interface HomeDashSession {
  type: 'run' | 'bike' | 'lift' | 'swim' | 'recovery';
  label: 'SÉANCE DU JOUR' | 'RÉCUPÉRATION';
  time: string;           // "09:00" ou "Aujourd'hui"
  discipline: string;     // "Course" | "Vélo" | "Récupération active"
  duration: string;       // "52 min" | "2h10" | "20–30 min"
  brief: string;
  targets: SessionTarget[]; // vide pour recovery
}

interface HomeDashData {
  firstName: string;
  dateLabel: string;          // "SAM. 18 AVR."
  readiness: {
    value: number;            // 0-100
    delta: number;            // +4 / -18
  };
  nutrition: {
    kcal: number;             // 2140
    target: number;           // 2600
  };
  strain: {
    displayValue: string;     // "14.2"
    semanticValue: number;    // pour calcul couleur (≥18=red, ≥14=yellow, sinon green)
  };
  sleep: {
    duration: string;         // "7h32"
    score: number;            // 82
  };
  cognitiveLoad: {
    value: number;            // 0-100
    label: string;            // "Modérée"
    context: string;          // "62 / 100"
  };
  session: HomeDashSession;
}
```

### 3 états mock

Données identiques à `dashboard.jsx` `DATA.normal / DATA.ideal / DATA.recovery`.

```ts
export type DashState = 'normal' | 'ideal' | 'recovery';

export const DASH_MOCK: Record<DashState, HomeDashData> = {
  normal: { /* readiness 78, +4, Course, Allure/FC/TSS */ },
  ideal:  { /* readiness 92, +7, Vélo,   Puissance/NP/TSS */ },
  recovery: { /* readiness 45, -18, Récupération active */ },
};
```

### Checklist commit 1
- [ ] Compile sans erreur TypeScript (`pnpm --filter @resilio/mobile typecheck`)
- [ ] Aucun hex en dur (tous via valeurs littérales dans le mock, pas dans les composants)
- [ ] `athlete-home-stub.ts` non modifié (git diff doit montrer seulement le nouveau fichier)

---

## Commit 2 — index.tsx rewrite

**Fichier cible:** `apps/mobile/app/(tabs)/index.tsx`
**Backup:** `apps/mobile/app/(tabs)/index.tsx.backup-p6` créé avant modification.

### Imports supprimés
```ts
// Supprimer ces imports de ui-mobile:
MetricRow, CognitiveLoadDial, ReadinessStatusBadge, SessionCard
// Supprimer:
import type { WorkoutSlotForCard } from '@resilio/ui-mobile';
import type { WorkoutSlotStub } from '../../src/types/home';
import { useHomeData } from '../../src/hooks/useHomeData';
```

### Imports ajoutés
```ts
import { useState } from 'react';
import Svg, { Circle as SvgCircle } from 'react-native-svg';
import { DASH_MOCK } from '../../src/mocks/home-dashboard-mock';
import type { DashState } from '../../src/mocks/home-dashboard-mock';
```

### Composants inline (dans index.tsx, pas exportés)

#### `ReadinessRingHome`
```
Props: value, delta, colorMode
Logique couleur (ringColor):
  value >= 80 → colors.physio.green[colorMode]
  value >= 60 → colors.physio.yellow[colorMode]
  < 60        → colors.physio.red[colorMode]
deltaColor = ringColor  (même couleur sémantique, pas de règle pos/neg)
deltaStr = `${delta > 0 ? '+' : ''}${delta} vs hier`

Géométrie: size=160, strokeWidth=10, rotation=-90
Centre: value (72px, 500, tabular-nums, letterSpacing -3.5)
Dessous value: "READINESS" (11px, 500, uppercase, textMuted, letterSpacing 1.8)
Dessous label: deltaStr (12px, 500, tabular, deltaColor)
```

#### `MetricsStrip`
```
Props: nutrition, strain, sleep, colorMode
Layout: View row, 3 cols flex:1, hairline dividers (backgroundColor: themeColors.border)
Col 1 — NUTRITION:
  Label: "NUTRITION" (10px, 600, uppercase, letterSpacing 1.4, textMuted)
  Value: kcal + " / " + target (kcal en text, target en textFaint)
  Sub: "kcal" (11px, textMuted)
  Progress bar: height 3, bg themeColors.track, fill text×0.85, width=(kcal/target)%
Col 2 — STRAIN:
  Label: "STRAIN" (10px, 600, uppercase)
  Value: displayValue (17px, 500, strainColor, tabular)
    strainColor: semanticValue >= 18 → red, >= 14 → yellow, sinon → green
  Sub: "Fatigue musculaire" (11px, textMuted, 2 lignes)
Col 3 — SOMMEIL:
  Label: "SOMMEIL" (10px, 600, uppercase)
  Value: duration (17px, 500, text)
  Sub: "Score " + score (score en sleepColor, tabular)
    sleepColor: score >= 80 → green, >= 65 → yellow, sinon → red
```

#### `HomeSessionCard`
```
Props: session, colorMode, onStart
isRecovery = session.type === 'recovery'

Header row: label (10px, 600, uppercase, textMuted) + time (11px, textFaint, tabular)
Title row: discipline (22px, 500, text, letterSpacing -0.5) + duration (15px, 500, textMuted, tabular)
Brief: (14px, textMuted, lineHeight 1.5)

Si !isRecovery → targets row:
  borderTop hairline, flexDirection: row, gap 12
  Pour chaque target:
    label (10px, 500, uppercase, textFaint, letterSpacing 1.2)
    value (14px, 500, text, tabular, letterSpacing -0.2)

Footer CTA (pleine largeur, attaché au bas de la card):
  borderTop hairline (si !isRecovery) ou borderTop surfaceAlt (si isRecovery)
  paddingVertical 16, paddingHorizontal 18
  flexDirection row, alignItems center, justifyContent center, gap 6
  bg: isRecovery → themeColors.surface2 (ghost) | accent (start session)
  color: isRecovery → text | accentText (#FAFAF7 light / #161412 dark)
  text: "Voir le protocole" ou "Démarrer la séance"
  flèche → (SVG 14×14)
  borderRadius: bottom 13px seulement (borderBottomLeftRadius + borderBottomRightRadius)
  onPress: onStart
    isRecovery → Haptics.impactAsync(ImpactFeedbackStyle.Light) + // TODO router.push('/protocol/recovery')
    else       → Haptics.impactAsync(ImpactFeedbackStyle.Medium) + // TODO router.push('/session/live')
```

#### `CognitiveLoadBar`
```
Props: value, label, context
24 segments, hauteur 28, gap 2
Segment i:
  bg: i < filled → couleur sémantique (value >= 70 → red, >= 45 → yellow, sinon → green)
     opacity: 0.35 + (i / 24) * 0.65
  bg: i >= filled → themeColors.track
  flex:1, borderRadius 1
  
Header: "CHARGE COGNITIVE" (10px, 600, uppercase, textMuted, letterSpacing 1.4)
         + "7j" (11px, textFaint) — justifyContent: space-between
Sub: "Charge allostatique" (13px, textFaint, marginBottom 14)
Footer: label (18px, 500, text, tabular) + context (13px, textMuted, tabular)
```

### Écran principal `HomeScreen`

```
State: dashState: DashState = 'normal'
  toggleState: () => cycle normal→ideal→recovery→normal
Data: DASH_MOCK[dashState]

Layout:
<Screen>
  <ScrollView contentContainerStyle={{ paddingBottom: 48 }}>
    {/* Header */}
    View flexDirection:row, justifyContent:space-between, alignItems:center
    px 20, pt 14, pb 24
      Left: "Bonjour {data.firstName}" (22px, 500, text, letterSpacing -0.6)
             "{data.dateLabel}" (11px, 600, uppercase, textMuted, letterSpacing 1.5, tabular)
      Right: TouchableOpacity onPress={toggleState}
             Cercle 36px, bg surfaceAlt, border border, alignCenter
             Text "SR" (13px, 500, text, letterSpacing 0.4)

    {/* Readiness ring — centré */}
    View alignItems:center, px 20, pb 28
      <ReadinessRingHome value={data.readiness.value} delta={data.readiness.delta} colorMode={colorMode} />

    {/* Metrics strip */}
    View px 20, mb 16
      <Card style={{ overflow:'hidden' }}>
        <MetricsStrip nutrition={data.nutrition} strain={data.strain} sleep={data.sleep} colorMode={colorMode} />
      </Card>

    {/* Session / Recovery card */}
    View px 20, mb 16
      <Card style={{ padding:0, overflow:'hidden' }}>
        <HomeSessionCard session={data.session} colorMode={colorMode} onStart={handleStart} />
      </Card>

    {/* Cognitive load bar */}
    View px 20, mb 20
      <Card style={{ padding:18 }}>
        <CognitiveLoadBar {...data.cognitiveLoad} />
      </Card>
  </ScrollView>
</Screen>

handleStart: Haptics.impactAsync(ImpactFeedbackStyle.Medium) puis no-op (route Today's Session = future)
```

### Couleurs accent par mode
```ts
const accentColor = colorMode === 'dark' ? colors.accentDark : colors.accent;
const accentTextColor = colorMode === 'dark' ? colors.accentTextDark : colors.accentText;
// → 0 hex en dur dans index.tsx (grep retourne 0)
```

### Checklist commit 2
- [ ] Compile sans warning TypeScript
- [ ] `git grep "#[0-9a-fA-F]" apps/mobile/app/\(tabs\)/index.tsx` → 0 résultats (accentText tokens en Commit 0 évitent les hex inline)
- [ ] Light comparé screenshot: ring taille, couleur amber pour normal=78
- [ ] Dark comparé screenshot: fond #161412, même structure
- [ ] Tap avatar "SR" → cycle 3 états visuels sur iPhone
- [ ] État recovery: card "RÉCUPÉRATION" + CTA ghost (pas d'accent)
- [ ] `ReadinessStatusBadge`, `MetricRow`, `SessionCard`, `CognitiveLoadDial` — absents des imports
- [ ] Aucun import direct `lucide-react-native` hors `packages/ui-mobile`

---

## Post-exécution

```bash
git push origin chore/downgrade-sdk54
```

---

## Composants candidats suppression — décision après test Expo Go P6

| Composant | Fichier | Usages post-P6 connus |
|---|---|---|
| `MetricRow` | `packages/ui-mobile/src/components/MetricRow.tsx` | Aucun (potentiel: Metric Detail V2) |
| `SessionCard` | `packages/ui-mobile/src/components/SessionCard.tsx` | Aucun (potentiel: Today's Session) |
| `CognitiveLoadDial` | `packages/ui-mobile/src/components/CognitiveLoadDial.tsx` | Aucun (potentiel: Metric Detail V2) |
| `ReadinessStatusBadge` | `packages/ui-mobile/src/components/ReadinessStatusBadge.tsx` | Aucun connu |

**Action:** revalider après tests Expo Go. Si confirmé inutilisé, supprimer dans un commit `chore(ui-mobile): remove obsolete components`.
