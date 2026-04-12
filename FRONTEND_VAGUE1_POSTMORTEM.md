# FRONTEND_VAGUE1_POSTMORTEM.md — Vague 1 Frontend Post-Mortem

**Date:** 2026-04-12  
**Branches impliquées:** session/fe-1a, session/fe-1b-expo-mobile, session/fe-1c, session/fe-1d-api-client  
**Merges sur main:** ac2cba5 (fe-1d), d4e1ac5 (fe-1b)  
**Tag de backup:** backup-before-fe-vague1-merge-2026-04-12

---

## Contexte

La Vague 1 Frontend visait à livrer 4 blocs de travail en parallèle :

| Session | Mission |
|---|---|
| FE-1A | Tauri desktop scaffold |
| FE-1B | Expo mobile scaffold + ui-mobile components |
| FE-1C | ESLint rules + hex cleanup (CSS vars migration) |
| FE-1D | API client generation + migration apps/web |

4 sessions ont été lancées simultanément dans le **même working tree** (répertoire local unique).

---

## Problème rencontré — Collisions Git

Chaque session commençait par `git checkout -b session/fe-1X`. Lancées en parallèle dans le même dossier, les sessions se marchaient dessus : un `git checkout` d'une session écrasait le checkout d'une autre. Résultat : du travail atterrissait sur la mauvaise branche, les sessions perdaient leur isolation.

**Symptôme concret :** les commits de FE-1A (Tauri) et FE-1C (ESLint/hex) se sont retrouvés sur la branche `session/fe-1d-api-client` plutôt que sur leurs branches dédiées.

---

## Conséquence

- Branches fe-1a et fe-1c : incomplètes ou vides après collision.
- Branches fe-1b et fe-1d : ont absorbé le travail des 4 sessions.
- 2 merges au lieu de 4 pour clore la Vague 1.

---

## Résolution appliquée

Consolidation en 2 merges :

1. **ac2cba5** — `Merge branch 'session/fe-1d-api-client'` → absorbe FE-1A + FE-1C + FE-1D
2. **d4e1ac5** — `Merge branch 'session/fe-1b-expo-mobile'` → absorbe FE-1B

---

## Travail effectivement livré

Malgré la collision, tout le scope prévu a été livré :

| Livrable | Branche d'atterrissage |
|---|---|
| Tauri desktop scaffold (`apps/desktop/`) | fe-1d |
| Expo mobile scaffold (`apps/mobile/`) | fe-1b |
| ESLint rules + no-hardcoded-colors | fe-1d |
| Migration hex → CSS vars (check-in, energy) | fe-1d |
| Génération `@resilio/api-client` depuis OpenAPI | fe-1d |
| Migration `apps/web/src/lib/api.ts` → api-client | fe-1d |
| Composants `@resilio/ui-mobile` (base) | fe-1b |

---

## Branches abandonnées

- `session/fe-1a` — conservée sur remote pour traçabilité, non mergée
- `session/fe-1c` — conservée sur remote pour traçabilité, non mergée

Le travail de ces deux sessions est bien présent dans main via fe-1d.

---

## Leçon méthodologique

**Ne jamais lancer 2+ sessions parallèles dans le même dossier local.**

Pour toute future vague multi-sessions parallèles, utiliser `git worktree add` :

```bash
# Créer un worktree isolé par session
git worktree add ../resilio-plus-fe-1a session/fe-1a
git worktree add ../resilio-plus-fe-1b session/fe-1b
git worktree add ../resilio-plus-fe-1c session/fe-1c
git worktree add ../resilio-plus-fe-1d session/fe-1d

# Chaque session travaille dans son propre dossier — zéro collision
```

Chaque worktree a son propre HEAD et index. Les sessions peuvent s'exécuter simultanément sans interférence.

---

*Voir `frontend-master-v1.md` section "État d'implémentation Vague 1" pour le statut final de chaque session.*
