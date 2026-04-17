# iOS Widget — Resilio+ Readiness

Scaffold pour implémentation future via `expo-widgets` + `@expo/ui`.

**Session cible :** `FE-MOBILE-WIDGET`

---

## But

Widget iOS home screen affichant le score de Forme du jour (Readiness) de l'athlète :
- Score 0–100
- Couleur physiologique : vert (≥70) / jaune (50–69) / rouge (<50)
- Mise à jour automatique via WidgetKit timeline

---

## Dépendances à installer en FE-MOBILE-WIDGET

```bash
npx expo install @expo/ui expo-widgets
```

> `expo-widgets` est en alpha dans SDK 55. API sujette à breaking changes.

---

## Contraintes

- **iOS 17+ requis** — WidgetKit avec SwiftUI interop
- **Xcode 26+ requis** pour build (via EAS Build cloud depuis Windows)
- **Pas de simulateur iOS local** depuis Windows — build via `eas build --platform ios`
- expo-widgets alpha = API non stable, ne pas utiliser en production

---

## Source de données

- Endpoint : `GET /api/v1/athletes/{id}/readiness/current`
- Auth : JWT Bearer (expo-secure-store)
- Fréquence refresh : 30 minutes (WidgetKit timeline configurable)
- Schema de réponse :
  ```json
  {
    "readiness_score": 75,
    "computed_at": "2026-04-16T08:00:00Z",
    "components": { "hrv": 72, "sleep": 80, "muscle_strain": 62 }
  }
  ```

---

## Architecture cible

```
ios-widget/
├── README.md         ← ce fichier
├── Widget.tsx        ← composant React Native (expo-widgets)
├── WidgetProvider.ts ← timeline provider + data fetching
└── widget.config.ts  ← widget metadata (name, description, sizes)
```

---

## Commandes EAS Build

```bash
# Preview (TestFlight interne)
cd apps/mobile && eas build --platform ios --profile preview

# Production (App Store)
cd apps/mobile && eas build --platform ios --profile production
```

---

*Scaffold créé en Session FE-MOBILE-1 (2026-04-16). Implémenter en Session FE-MOBILE-WIDGET.*
