# FRONTEND_AUDIT.md — Resilio+ Frontend Audit

Date: 2026-04-12  
Branch: session/frontend-s0-monorepo-setup  
Source: `frontend/` (before migration to `apps/web/`)

---

## 1. Palette de couleurs

The app is **dark-first** ("Clinical-athlete. Dark by default. Whoop × TrainingPeaks").  
All colors are CSS variables defined in `frontend/src/app/globals.css`.

### Surface hierarchy (dark mode — current default)
| Token | Value | Role |
|---|---|---|
| `--background` | `#08080e` | Page background |
| `--surface-1` | `#0f0f18` | Subtle elevation |
| `--surface-2` | `#14141f` | Cards / panels (main card bg) |
| `--surface-3` | `#1a1a28` | Inputs, secondary surface |
| `--border` | `#22223a` | Default border |
| `--border-subtle` | `#191928` | Subtle border |

### Text
| Token | Value | Role |
|---|---|---|
| `--foreground` | `#eeeef4` | Primary text |
| `--text-muted` | `#5c5c7a` | Muted / labels |
| `--text-secondary` | `#8888a8` | Secondary text |

### Brand accent
| Token | Value | Role |
|---|---|---|
| `--accent` / `--primary` | `#5b5fef` | Primary action, links, active states |
| `--accent-dim` | `rgba(91, 95, 239, 0.15)` | Accent background tint |

### Status zones
| Token | Value | Role |
|---|---|---|
| `--zone-green` | `#10b981` | Good / safe |
| `--zone-green-bg` | `rgba(16, 185, 129, 0.10)` | Green tint background |
| `--zone-yellow` | `#f59e0b` | Caution |
| `--zone-yellow-bg` | `rgba(245, 158, 11, 0.10)` | Yellow tint background |
| `--zone-red` | `#ef4444` | Danger |
| `--zone-red-bg` | `rgba(239, 68, 68, 0.10)` | Red tint background |

### Cycle phase colors
| Token | Value | Role |
|---|---|---|
| `--phase-menstrual` | `#ef4444` | Menstrual phase |
| `--phase-follicular` | `#10b981` | Follicular phase |
| `--phase-ovulation` | `#f59e0b` | Ovulation phase |
| `--phase-luteal` | `#818cf8` | Luteal phase |

### Shadcn semantic tokens (also present)
`--card: #14141f`, `--muted: #1a1a28`, `--secondary: #1a1a28`, `--input: #1a1a28`, `--ring: #5b5fef`, `--destructive: #ef4444`

> **Note:** The app is currently dark-mode only. Light mode CSS variables are NOT defined. The `next-themes` library is installed and `useTheme` is already used in `TopNav`, but only the dark palette exists. Light mode tokens must be added in `design-tokens`.

---

## 2. Police actuelle

| Police | Source | Usage |
|---|---|---|
| **Space Grotesk** (wt 300–700) | Google Fonts (import in globals.css) | Body, headings, nav — `--font-sans` |
| **Space Mono** (wt 400, 700) | Google Fonts (import in globals.css) | Metric numbers — `--font-mono`, `.metric-number` class |

Import URL: `https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap`

---

## 3. Bibliothèques UI utilisées

| Lib | Version | Usage |
|---|---|---|
| **Tailwind CSS v4** | `^4` | Utility classes — configured entirely via CSS (`@import "tailwindcss"`, `@theme inline`) — NO tailwind.config.ts |
| **shadcn/ui** (manual) | — | Button, Card, Badge, Input, Label, Progress — in `src/components/ui/` |
| **Radix UI** | `@radix-ui/react-label ^2`, `@radix-ui/react-progress ^1`, `@radix-ui/react-slot ^1` | Backing shadcn components |
| **lucide-react** | `^1.8.0` | `Moon`, `Sun` only (in `top-nav.tsx`) |
| **next-themes** | `^0.4.6` | Theme toggle (already wired in TopNav) |
| **recharts** | `^3.8.1` | Analytics charts (LineChart, etc.) |
| **class-variance-authority** | `^0.7.1` | shadcn CVA |
| **clsx + tailwind-merge** | `^2 / ^3` | Class merging utilities |

> **Tailwind v4 note:** No `tailwind.config.ts`. Everything configured via `@theme inline` in `globals.css`. `darkMode: 'class'` NOT explicitly configured — in v4 this is handled differently via `dark:` variant.

---

## 4. Liste des écrans existants (page.tsx)

| Route | File | Description |
|---|---|---|
| `/` | `src/app/page.tsx` | Landing / redirect |
| `/login` | `src/app/login/page.tsx` | Auth login |
| `/onboarding` | `src/app/onboarding/page.tsx` | Athlete onboarding |
| `/dashboard` | `src/app/dashboard/page.tsx` | Main dashboard (week status, energy card) |
| `/energy` | `src/app/energy/page.tsx` | Energy dashboard (allostatic gauge, charts) |
| `/energy/cycle` | `src/app/energy/cycle/page.tsx` | Energy cycle detail |
| `/check-in` | `src/app/check-in/page.tsx` | Daily check-in wizard (4 questions) |
| `/plan` | `src/app/plan/page.tsx` | Training plan view |
| `/review` | `src/app/review/page.tsx` | Weekly review |
| `/history` | `src/app/history/page.tsx` | Session history |
| `/analytics` | `src/app/analytics/page.tsx` | Analytics (recharts) |
| `/session/[id]` | `src/app/session/[id]/page.tsx` | Session detail |
| `/session/[id]/log` | `src/app/session/[id]/log/page.tsx` | Session log entry |
| `/settings` | `src/app/settings/page.tsx` | Settings |
| `/settings/connectors` | `src/app/settings/connectors/page.tsx` | Connector settings (Strava, Hevy, Terra) |
| `/tracking` | `src/app/tracking/page.tsx` | External plan tracking |
| `/tracking/import` | `src/app/tracking/import/page.tsx` | External plan import wizard |
| `api/config` | `src/app/api/config/route.ts` | Next.js API route (config) |

---

## 5. Liste des composants réutilisables

### Navigation
- `src/components/top-nav.tsx` — TopNav with dark/light toggle (Moon/Sun icons from lucide-react), auth state, coaching mode badge

### Layout
- `src/components/protected-route.tsx` — Auth guard wrapper

### shadcn/ui components (in `src/components/ui/`)
- `button.tsx` — Button with variants (default, outline, ghost, destructive, secondary)
- `card.tsx` — Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter
- `badge.tsx` — Badge with variants (default, secondary, outline, destructive)
- `input.tsx` — Input field
- `label.tsx` — Form label
- `progress.tsx` — Progress bar
- `allostatic-gauge.tsx` — Custom SVG gauge for allostatic score

### Analytics components (in `src/components/analytics/`)
- `AcwrTrendChart.tsx` — ACWR trend line chart
- `PerformanceTrendChart.tsx` — Performance trend chart
- `SportBreakdownChart.tsx` — Sport breakdown chart
- `TrainingLoadChart.tsx` — Training load chart

---

## 6. Patterns récurrents

### TopNav
Sticky header, dark bg with backdrop blur, brand wordmark "RESILIO+", navigation links with active state underline, dark/light toggle button (already functional), logout button.

### Cards
Standard pattern: `<Card><CardHeader><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">...</Card>`. Cards use `--surface-2` (`#14141f`) background.

### Stat blocks
Large number (`text-3xl font-bold`) in Space Mono, with unit suffix in `text-muted-foreground`, label in small uppercase tracking.

### Status badges
Color-coded by zone (green/yellow/red) using inline `style` with hardcoded hex values — **will be replaced by design-tokens in packages**.

### Forms
Multi-step wizards (check-in: 4 questions), option buttons with selected state using inline border/background colors.

### Loading states
`animate-pulse` on text — `text-muted-foreground` color.

### Error states
`text-destructive` class for errors.

---

## 7. État dark mode

The app is **dark-by-default and dark-only**. Key observations:
- `html { color-scheme: dark; }` — forces dark
- `next-themes` already installed and `useTheme` wired in `TopNav` (Moon/Sun toggle exists)
- **Light mode CSS variables are absent** — the `:root` block only defines the dark palette
- Many components use **inline hardcoded hex values** (e.g., `style={{ background: '#14141f' }}`) — these will be addressed via design-tokens
- Tailwind `dark:` variants are not used in most pages (not needed since app was dark-only)

**Light mode variables to add in design-tokens:**
| Token | Light value (proposed) |
|---|---|
| `--background` | `#f8f8fc` |
| `--surface-2` (card) | `#ffffff` |
| `--foreground` | `#0f0f18` |
| `--text-muted` | `#6b6b88` |
| `--border` | `#e2e2ee` |
| `--primary` | `#5b5fef` (same) |

---

## 8. Tests frontend existants

| File | Framework | Scope |
|---|---|---|
| `src/app/dashboard/__tests__/page.test.tsx` | vitest + @testing-library/react | Dashboard rendering |
| `src/app/login/__tests__/page.test.tsx` | vitest | Login page |
| `src/app/onboarding/__tests__/page.test.tsx` | vitest | Onboarding page |
| `src/app/plan/__tests__/page.test.tsx` | vitest | Plan page |
| `src/app/review/__tests__/page.test.tsx` | vitest | Review page |
| `src/components/__tests__/protected-route.test.tsx` | vitest | Protected route |
| `src/lib/__tests__/api.test.ts` | vitest | API client |
| `src/lib/__tests__/auth.test.tsx` | vitest | Auth context |

---

## 9. Configuration spéciale Next.js

- Next.js `16.2.3` — Version récente avec Turbopack activé par défaut en dev
- `tsconfig.json` paths: `@/*` → `./src/*`
- `vitest.config.ts` — configuration vitest (pas Jest)
- `postcss.config.mjs` — `@tailwindcss/postcss`
- `.next/` cache présent (ignoré du repo via `.gitignore`)

---

## 10. Icônes lucide-react utilisées

Uniquement `Moon` et `Sun` dans `top-nav.tsx`.  
Pas d'autres imports directs de lucide-react dans les composants existants (les pages utilisent des emojis et des SVG inline à la place).

---

*Ce document est la référence pour la Session 0 du design system frontend Resilio+.*
