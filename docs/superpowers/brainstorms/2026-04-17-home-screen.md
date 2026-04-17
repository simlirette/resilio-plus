# Brainstorm — Home Screen (FE-MOBILE-2)

**Date:** 2026-04-17  
**Session:** FE-MOBILE-2 (not started)  
**Author:** Claude Sonnet 4.6 (autonomous, FE-MOBILE-1B)

---

## Objectif

Implémenter l'écran Accueil complet de Resilio+. L'écran présente la forme du jour de l'athlète via un dashboard clinique : un grand cercle de readiness, 3 petits cercles pour les sous-métriques (Nutrition, Strain, Sommeil), une carte "Cognitive Load", et la prochaine séance.

**Aucun endpoint réel n'est disponible pour FE-MOBILE-2.** Tout le rendu se base sur `athlete-home-stub.ts` (données mockées typées).

---

## Composants existants utilisables

| Composant | Usage Home |
|---|---|
| `<Circle>` | Readiness principal (size=160) + 3 petits cercles (size=80) |
| `<Card>` | Carte "Prochaine séance" + carte "Cognitive Load" |
| `<Text>` | Tous les labels et valeurs |
| `<Screen scroll padded>` | Wrapper écran |
| `<Button>` | CTA "Check-in quotidien" |
| `Icon.*` | Icônes dans les cartes |

---

## Composants manquants à créer en FE-MOBILE-2

| Composant | Description | Priorité |
|---|---|---|
| `<CognitiveLoadDial>` | Semi-arc jauge 0-100 (différent du SVG ring de Circle) | Haute |
| `<SessionCard>` | Carte "Prochaine séance" enrichie (titre, durée, sport, zone, badge jour) | Haute |
| `<MetricRow>` | Rangée de 3 petits cercles (Nutrition / Strain / Sommeil) | Haute |
| `<ReadinessStatusBadge>` | Texte état (Optimal / Prudent / Repos recommandé) + couleur | Moyenne |

Note : `SessionCard` peut être un simple composite de `Card + Text + Icon` sans nouveau composant primitif.

---

## Données nécessaires (AthleteState backend)

Source: `backend/app/models/athlete_state.py` + `backend/app/schemas/connector.py`

```ts
// Tous les champs mappés depuis les schemas Python
{
  // AthleteMetrics
  readiness_score: number;      // AthleteMetrics.readiness_score (0–100)
  acwr_status: 'safe' | 'caution' | 'danger';
  muscle_strain: {              // MuscleStrainScore (index agrégé 0–100)
    overall: number;
  };
  sleep_hours: number | null;   // AthleteMetrics.sleep_hours
  hrv_rmssd: number | null;     // AthleteMetrics.hrv_rmssd (ms)

  // Nutrition (calculé par NutritionCoach — pas encore d'endpoint)
  nutrition_adherence: number;  // 0–100, % plan hebdo suivi

  // Cognitive Load (calculé par EnergyCoach via allostatic score)
  allostatic_score: number;     // AllostaticSummary.avg_score_7d (0–100)

  // Plan du jour
  today_sessions: WorkoutSlot[];  // PlanSnapshot.today
}
```

**Endpoint actuel :** `GET /athletes/{id}/readiness` → `ReadinessResponse`  
**Endpoint manquant :** Un endpoint unifié `GET /athletes/{id}/home-summary` serait idéal pour FE-MOBILE-2. Alternative: appels parallèles `/readiness` + `/plans/current` + `/metrics/latest`.

---

## Questions ouvertes (à résoudre avant FE-MOBILE-2)

1. **Endpoint home :** Faut-il créer `GET /athletes/{id}/home-summary` côté backend ou faire des appels parallèles multiples depuis le frontend ?
2. **Nutrition score :** La valeur `nutrition_adherence` n'existe pas encore dans les schemas backend. Calculée comment ? % de macros dans la cible ? Sera-t-elle dispo en FE-MOBILE-2 ou mockée plus longtemps ?
3. **Cognitive Load vs Allostatic :** L'UI-RULES-MOBILE dit "Cognitive Load dial". Le backend a `allostatic_score`. Sont-ils synonymes ? L'allostatic score est-il safe à afficher directement comme "charge cognitive" ?
4. **Sleep : score ou heures ?** L'UI montre un cercle 0-100 pour Sommeil, mais le backend stocke `sleep_hours` (float). Faut-il convertir `sleep_hours → sleep_score` (ex: 8h → 100, 5h → 50) ? Ou attendre que Terra fournisse `terra_sleep_score` ?
5. **Muscle Strain agrégé :** `MuscleStrainScore` a 10 axes par muscle group. Pour l'affichage Home, faut-il utiliser `max()` de tous les axes ? Ou une moyenne pondérée ? Ou un champ `overall` à ajouter ?
6. **Repos recommandé :** Si `readiness_score < 50`, l'écran affiche-t-il un message de repos au lieu de la prochaine séance ? Ou les deux ?
7. **Auth réelle :** FE-MOBILE-2 utilise encore le mock d'auth (800ms delay) ou implémente expo-secure-store + JWT ? Impact sur l'`athlete_id` pour les appels API.
8. **Pull-to-refresh :** Doit-on prévoir dès FE-MOBILE-2 ou différer à FE-MOBILE-BACKEND-WIRING ?

---

## Skeleton arborescence fichiers FE-MOBILE-2

```
apps/mobile/
├── app/(tabs)/
│   └── index.tsx              ← Réécriture complète (remplace placeholder actuel)
├── src/
│   ├── mocks/
│   │   └── athlete-home-stub.ts  ← Déjà créé en FE-MOBILE-1B
│   ├── hooks/
│   │   └── useHomeData.ts        ← Hook qui retourne mockHomeData (FE-MOBILE-2)
│   └── types/
│       └── home.ts               ← Types HomeData, MetricState, SessionData (FE-MOBILE-2)
packages/ui-mobile/
└── src/components/
    ├── CognitiveLoadDial.tsx     ← Semi-arc SVG, value 0-100 (FE-MOBILE-2)
    └── SessionCard.tsx           ← Carte séance avec sport/zone/durée (FE-MOBILE-2)
```

---

*Créé par FE-MOBILE-1B. À compléter en FE-MOBILE-2 une fois les questions ouvertes résolues avec Simon-Olivier.*
