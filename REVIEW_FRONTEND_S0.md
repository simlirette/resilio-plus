# REVIEW — Frontend Session 0 : Monorepo Setup + Design System Foundations

**Date :** 2026-04-12  
**Branche :** session/frontend-s0-monorepo-setup  
**Reviewer :** Automated (Claude Code)  
**Commit reviewed :** 031d385

---

## Verdict : FIX REQUIRED

La session a correctement posé les fondations structurelles, mais elle comporte **2 violations des règles absolues qu'elle a elle-même introduites.** Ces violations sont bloquantes car elles invalident la promesse du scaffolding (les règles énoncées dans `frontend-master-v1.md` et `CLAUDE.md` ne sont pas respectées dans le code livré).

---

## Résumé des vérifications

### Structure monorepo

| Check | Résultat |
|---|---|
| `pnpm-workspace.yaml` avec `apps/*` + `packages/*` | ✅ |
| `apps/web/` contient le code migré depuis `frontend/` | ✅ |
| `frontend/` supprimé (git mv préservant l'historique) | ✅ |
| `apps/desktop/` et `apps/mobile/` — placeholders uniquement | ✅ README + package.json minimal, pas de framework installé |
| 6 packages présents : design-tokens, ui-web, ui-mobile, api-client, shared-logic, brand | ✅ |
| Chaque package a son `package.json` avec `@resilio/xxx` | ✅ |

### Design tokens

| Check | Résultat | Note |
|---|---|---|
| `colors.ts` — couleurs dark ET light | ✅ | dark: `#08080e`, `#14141f`, `#5b5fef` — exact match audit |
| `colors.ts` — light cohérent avec l'audit | ✅ | Proposition logique inversée |
| `typography.ts` — Space Grotesk + Space Mono | ✅ |  |
| `spacing.ts`, `radius.ts`, `shadows.ts`, `animation.ts` présents | ✅ |  |
| Tous exports accessibles depuis `index.ts` | ✅ |  |

**Note qualité tokens :** Nomenclature exemplaire. Séparation surface hierarchy / brand / zones / shadcn-semantic est propre. La duplication `shadcn.dark` / top-level `dark` est de la dette technique acceptable (réf. section dette).

### Couche d'abstraction icônes

| Check | Résultat | Note |
|---|---|---|
| `packages/ui-web/src/icons.ts` existe avec mapping sémantique | ✅ | 29 icônes, nommage sémantique correct |
| Pas d'import direct `lucide-react` dans `apps/web/src/` | ❌ | **VIOLATION** — `top-nav.tsx:9` importe `Moon, Sun` directement |
| Toggle Moon/Sun via `Icon.DarkMode` / `Icon.LightMode` | ❌ | **VIOLATION** — `top-nav.tsx` n'utilise pas `Icon` du tout |
| `apps/web/package.json` dépend de `@resilio/ui-web` | ❌ | Pas de dépendance workspace déclarée — `@resilio/ui-web` est disponible mais jamais wired |

### Dark mode

| Check | Résultat | Note |
|---|---|---|
| Toggle fonctionnel (ThemeProvider configuré) | ✅ | `layout.tsx` configure `next-themes` avec `attribute="class"`, `enableSystem`, `storageKey` |
| Bloc `.light` dans `globals.css` avec overrides CSS vars | ✅ | 13 tokens light mode |
| Pass dark mode sur les 5 écrans critiques (CSS vars remplacent hex) | ✅ (partiel) | Majorité des hex remplacés |
| Zéro hex hardcodé dans les `style={{}}` des 5 écrans | ❌ (partiel) | Résidus hardcodés dans check-in et energy — **dette notable, pas bloquant** |
| `ThemeProvider` de `@resilio/ui-web` utilisé dans `layout.tsx` | ❌ | `layout.tsx` importe `ThemeProvider` depuis `next-themes` directement — le wrapper `@resilio/ui-web/ThemeProvider` est dead code |

**Détail résidus hex (check-in)** — lignes 48, 88, 140, 256 :
```
style={{ color: selected ? '#818cf880' : '#5c5c7a' }}
style={{ width: 72, height: 72, background: '#10b98118', border: '2px solid #10b981' }}
style={{ borderTop: '1px solid #22223a' }}
style={{ background: '#5b5fef15', color: '#818cf8', border: '1px solid #5b5fef30' }}
```

**Détail résidus hex (energy)** — lignes 104, 107, 112, 152, 155, 166, 181 : couleurs de zone (green/yellow/red) + opacity variants. Partiellement excusables (exception autorisée Règle #3 pour zones statiques), mais les opacités alpha (`#10b98188`, `#ef444415`) n'ont pas d'équivalent CSS var.

### Couche API client

| Check | Résultat |
|---|---|
| `packages/api-client/` avec setup codegen | ✅ |
| Script `pnpm generate` défini | ✅ — `openapi-typescript http://localhost:8000/openapi.json -o src/generated/api.ts` |
| Client NON régénéré (backend pas running) | ✅ — `.gitkeep` dans `src/generated/` |

### Documentation

| Check | Résultat |
|---|---|
| `frontend-master-v1.md` créé | ✅ — structure calquée sur `resilio-master-v3.md`, complet et actionnable |
| `CLAUDE.md` enrichi (PAS réécrit) avec 8 règles + monorepo | ✅ — sections ajoutées en fin de fichier |
| `resilio-master-v3.md` non modifié | ✅ — `git diff main -- resilio-master-v3.md` vide |

### Tests de non-régression

| Check | Résultat |
|---|---|
| `pnpm install` réussit | ✅ — `Done in 1s` (lockfile stable) |
| `pnpm --filter @resilio/web typecheck` passe | ✅ — silencieux, 0 erreurs |
| `pnpm --filter @resilio/web build` réussit | ✅ — 17 routes statiques + 2 dynamiques |
| Backend non modifié | ✅ — `git diff main -- backend/ tests/` vide |

**Backend E2E skippé** — non testable dans ce contexte (base de données non disponible en review). Non bloquant vu l'absence de modifications backend.

---

## Fixes requis (bloquants)

### Fix 1 — `top-nav.tsx` : migrer vers `Icon` de `@resilio/ui-web`

**Fichier :** `apps/web/src/components/top-nav.tsx`

```diff
- import { Moon, Sun } from 'lucide-react'
+ import { Icon } from '@resilio/ui-web'
```

Et dans le JSX :
```diff
- <Sun className="..." />
- <Moon className="..." />
+ <Icon.LightMode className="..." />
+ <Icon.DarkMode className="..." />
```

**Préalable obligatoire :** ajouter `@resilio/ui-web` comme dépendance workspace dans `apps/web/package.json` :
```json
"dependencies": {
  "@resilio/ui-web": "workspace:*",
  ...
}
```

### Fix 2 — `layout.tsx` : utiliser le ThemeProvider de `@resilio/ui-web`

**Fichier :** `apps/web/src/app/layout.tsx`

```diff
- import { ThemeProvider } from 'next-themes'
+ import { ThemeProvider } from '@resilio/ui-web'
```

Supprimer les props redondantes (elles sont encapsulées dans `@resilio/ui-web/ThemeProvider`) :
```diff
- <ThemeProvider attribute="class" defaultTheme="dark" enableSystem storageKey="resilio-theme">
+ <ThemeProvider>
```

**Note :** ce fix rend le `ThemeProvider` dans `packages/ui-web/src/theme/ThemeProvider.tsx` fonctionnel au lieu d'être dead code.

---

## Dette technique notée

| Item | Sévérité | Description |
|---|---|---|
| Résidus hex check-in + energy | ⚠️ Moyen | ~15 occurrences d'hex alpha semi-transparents sans équivalent CSS var. Prévu Session F4. |
| `design-tokens` — duplication shadcn vs raw | ℹ️ Faible | `colors.shadcn.dark` et `colors.dark` ont des valeurs redondantes. Une future refacto pourrait éliminer la duplication. |
| `apps/web/src/lib/api.ts` custom | ℹ️ Faible | Client API manuel non migré vers `@resilio/api-client`. Prévu Session F1. |
| Pas de dépendances workspace dans `apps/web` | ⚠️ Moyen | `@resilio/ui-web`, `@resilio/design-tokens`, `@resilio/shared-logic` ne sont pas déclarés dans `apps/web/package.json`. La règle d'abstraction ne peut pas être enforced (pas de résolution de module). À corriger avec Fix 1. |
| Pas de règles ESLint custom | ℹ️ Faible | Règles 1-3 (lucide, couleurs) non enforced automatiquement. Prévu Session F3. |
| `ui-mobile` skeleton | ℹ️ Info | Attendu — sera rempli en Session M. |
| `api-client/src/generated/` vide | ℹ️ Info | Attendu — générer avec backend running. |

---

## Confiance dans le scaffolding pour lancer Vague 1 parallèle

**Non** — tant que Fix 1 et Fix 2 ne sont pas appliqués.

**Raison :** Si la branche est mergée dans l'état actuel, la session qui suivra (F1, F2, ou Session T) démarrera avec une règle inscrite dans `CLAUDE.md` et `frontend-master-v1.md` mais violée dans le code livré par cette même session. Cela crée un double standard : les règles existent sur papier mais ne sont pas enforced dans la pratique. La prochaine session pourra légitimement copier ce pattern (importer lucide-react directement) en l'observant dans `top-nav.tsx`.

**Après les 2 fixes :** confiance élevée. Le scaffolding est solide :
- Monorepo pnpm fonctionnel, build vert, typecheck propre.
- Tokens complets et cohérents avec l'audit.
- Mapping icônes sémantique clair et extensible (29 icônes, noms bien choisis).
- Dark/light CSS vars infrastructure propre.
- `frontend-master-v1.md` est une référence de qualité, calquée sur `resilio-master-v3.md`.
- Backlog Vague 1 (F1–F6 + T + M) actionnable.

---

## Recommandations pour le backlog Vague 1

1. **Priorité absolue Session F1** — migrer `api.ts` vers `@resilio/api-client` et brancher les dépendances workspace dans tous les `apps/`. Sans cette étape, l'isolation des packages est cosmétique.

2. **Session F3 (ESLint)** — ajouter `eslint-plugin-no-restricted-imports` avec règles :
   - `no-direct-lucide` : interdit `import from 'lucide-react'` hors `packages/ui-web/`
   - `no-hardcoded-colors` : interdit les hex dans `style={{}}` (regex `#[0-9a-fA-F]{3,8}`)
   Ces règles auraient détecté les violations de cette session automatiquement.

3. **Session F4** — compléter la migration hex → CSS vars avec un focus sur les couleurs alpha (ex: `#ef444415` → `rgba(var(--zone-red-rgb), 0.08)`). Cela nécessite d'ajouter des tokens RGB séparés dans `design-tokens/colors.ts`.

4. **Sessions T et M** — démarrer seulement après F1 (dépendances workspace stables) et F3 (linting enforced). Ces sessions importeront `@resilio/ui-web` ou `@resilio/ui-mobile` — il faut que la résolution de modules workspace soit prouvée dans `apps/web` d'abord.

5. **Session F2 (tests)** — `shared-logic` contient des formatters et validators non testés. Priorité avant Session M (qui consommera `@resilio/shared-logic`).
