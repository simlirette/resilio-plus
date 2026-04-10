# S12 — Frontend: Dashboard + Calendar + Chat — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap Next.js 15 frontend with auth flow, dashboard, weekly calendar (calls real plan API), and chat UI shell.

**Architecture:** App Router (`src/app/`), TypeScript, Tailwind CSS v3, `lib/api.ts` typed fetch wrapper, JWT in localStorage.

**Tech Stack:** Next.js 15, React 19, TypeScript 5, Tailwind CSS 3, ESLint

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/` directory | Create (npm init) | Next.js 15 project root |
| `frontend/src/lib/api.ts` | Create | Typed fetch wrapper, auth header |
| `frontend/src/components/navbar.tsx` | Create | Top nav with links + logout |
| `frontend/src/app/layout.tsx` | Create | Root layout, globals import |
| `frontend/src/app/globals.css` | Create | Tailwind directives + dark base |
| `frontend/src/app/page.tsx` | Create | Root redirect |
| `frontend/src/app/login/page.tsx` | Create | Login form → POST /auth/login |
| `frontend/src/app/register/page.tsx` | Create | Register form → POST /auth/register |
| `frontend/src/app/dashboard/layout.tsx` | Create | Protected layout + Navbar |
| `frontend/src/app/dashboard/page.tsx` | Create | Dashboard → GET /athletes/me |
| `frontend/src/app/dashboard/calendar/page.tsx` | Create | Calendar → POST /plan/running + /plan/lifting |
| `frontend/src/app/dashboard/chat/page.tsx` | Create | Chat UI shell |
| `CLAUDE.md` | Modify | Mark S12 ✅ FAIT |

---

### Task 1: Bootstrap Next.js 15 project

**Files:**
- Create: all `frontend/` scaffold files

- [ ] **Step 1: Scaffold Next.js 15 project non-interactively**

```bash
cd /c/resilio-plus
npx --yes create-next-app@15 frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --no-import-alias \
  --use-npm \
  --empty
```

Note: `--empty` creates a minimal project. If `--empty` flag is not supported, just run without it — the default template is fine.

- [ ] **Step 2: Verify the project builds**

```bash
cd /c/resilio-plus/frontend
npm run build 2>&1 | tail -10
```

Expected: build succeeds (exit 0)

- [ ] **Step 3: Check generated files exist**

Verify these files exist:
- `frontend/package.json`
- `frontend/next.config.ts` (or `.js`)
- `frontend/tailwind.config.ts`
- `frontend/tsconfig.json`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/globals.css`

- [ ] **Step 4: Update `tailwind.config.ts` to enable dark mode class**

Read `frontend/tailwind.config.ts`. Add `darkMode: "class"` if not present:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 5: Update `src/app/globals.css` with dark base styles**

Replace entire `src/app/globals.css` content:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html {
  @apply bg-slate-950 text-slate-100;
}
```

- [ ] **Step 6: Commit**

```bash
cd /c/resilio-plus
git add frontend/
git commit -m "feat: bootstrap Next.js 15 frontend (TypeScript + Tailwind)"
```

---

### Task 2: `src/lib/api.ts` — typed fetch wrapper

**Files:**
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create `frontend/src/lib/` directory and `api.ts`**

Create `frontend/src/lib/api.ts`:

```typescript
/**
 * API client for Resilio+ backend (localhost:8000)
 * JWT token stored in localStorage under "resilio_token"
 */

const API_BASE = "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("resilio_token");
}

export function setToken(token: string, firstName: string): void {
  localStorage.setItem("resilio_token", token);
  localStorage.setItem("resilio_first_name", firstName);
}

export function clearToken(): void {
  localStorage.removeItem("resilio_token");
  localStorage.removeItem("resilio_first_name");
}

export function getFirstName(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("resilio_first_name") ?? "";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const error = new Error(String(err.detail ?? "Request failed")) as Error & { status: number };
    error.status = res.status;
    throw error;
  }

  return res.json() as Promise<T>;
}

export const api = {
  post: <T>(path: string, body: unknown): Promise<T> =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  get: <T>(path: string): Promise<T> => request<T>(path),
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /c/resilio-plus/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd /c/resilio-plus
git add frontend/src/lib/api.ts
git commit -m "feat: add frontend API client with JWT auth header"
```

---

### Task 3: Navbar component + root layout

**Files:**
- Create: `frontend/src/components/navbar.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/navbar.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { clearToken, getFirstName } from "@/lib/api";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const firstName = getFirstName();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  const linkClass = (href: string) =>
    `px-3 py-1 rounded text-sm transition-colors ${
      pathname.startsWith(href)
        ? "bg-violet-600 text-white"
        : "text-slate-400 hover:text-slate-100"
    }`;

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-14 px-6 bg-slate-900 border-b border-slate-800">
      <span className="font-bold text-violet-400 tracking-tight">Resilio+</span>

      <div className="flex items-center gap-2">
        <Link href="/dashboard" className={linkClass("/dashboard") + (pathname === "/dashboard" ? "" : "")}>
          Dashboard
        </Link>
        <Link href="/dashboard/calendar" className={linkClass("/dashboard/calendar")}>
          Calendrier
        </Link>
        <Link href="/dashboard/chat" className={linkClass("/dashboard/chat")}>
          Chat
        </Link>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-400">{firstName}</span>
        <button
          onClick={handleLogout}
          className="px-3 py-1 text-sm rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
        >
          Déconnexion
        </button>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Update `frontend/src/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Resilio+",
  description: "Coaching multi-sport — Head Coach IA",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Update `frontend/src/app/page.tsx`**

```tsx
import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/dashboard");
}
```

- [ ] **Step 4: TypeScript check**

```bash
cd /c/resilio-plus/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
cd /c/resilio-plus
git add frontend/src/components/navbar.tsx frontend/src/app/layout.tsx frontend/src/app/page.tsx
git commit -m "feat: add Navbar component, root layout, and root redirect"
```

---

### Task 4: Login and Register pages

**Files:**
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/register/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/login/page.tsx`**

```tsx
"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post<LoginResponse>("/auth/login", { email, password });
      // Fetch first name
      setToken(data.access_token, "");
      const me = await api.get<{ first_name: string }>("/athletes/me");
      setToken(data.access_token, me.first_name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-violet-400 mb-2">Resilio+</h1>
        <p className="text-slate-400 text-sm mb-8">Connexion à votre espace athlète</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500"
              placeholder="simon@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-400 text-center">
          Pas encore de compte ?{" "}
          <Link href="/register" className="text-violet-400 hover:underline">
            Créer un compte
          </Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/register/page.tsx`**

```tsx
"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

interface RegisterResponse {
  id: string;
  email: string;
  first_name: string;
  access_token: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    age: "",
    sex: "M",
    weight_kg: "",
    height_cm: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post<RegisterResponse>("/auth/register", {
        ...form,
        age: parseInt(form.age, 10),
        weight_kg: parseFloat(form.weight_kg),
        height_cm: parseFloat(form.height_cm),
      });
      setToken(data.access_token, data.first_name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur d'inscription");
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500";
  const labelClass = "block text-sm text-slate-400 mb-1";

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-10">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-violet-400 mb-2">Resilio+</h1>
        <p className="text-slate-400 text-sm mb-8">Créer votre profil athlète</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Prénom</label>
            <input type="text" value={form.first_name} onChange={(e) => update("first_name", e.target.value)} required className={inputClass} placeholder="Simon" />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required className={inputClass} placeholder="simon@example.com" />
          </div>
          <div>
            <label className={labelClass}>Mot de passe</label>
            <input type="password" value={form.password} onChange={(e) => update("password", e.target.value)} required className={inputClass} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Âge</label>
              <input type="number" value={form.age} onChange={(e) => update("age", e.target.value)} required min="16" max="80" className={inputClass} placeholder="32" />
            </div>
            <div>
              <label className={labelClass}>Sexe</label>
              <select value={form.sex} onChange={(e) => update("sex", e.target.value)} className={inputClass}>
                <option value="M">Homme</option>
                <option value="F">Femme</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Poids (kg)</label>
              <input type="number" value={form.weight_kg} onChange={(e) => update("weight_kg", e.target.value)} required step="0.1" className={inputClass} placeholder="78.5" />
            </div>
            <div>
              <label className={labelClass}>Taille (cm)</label>
              <input type="number" value={form.height_cm} onChange={(e) => update("height_cm", e.target.value)} required className={inputClass} placeholder="178" />
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {loading ? "Création..." : "Créer mon compte"}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-400 text-center">
          Déjà un compte ?{" "}
          <Link href="/login" className="text-violet-400 hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd /c/resilio-plus/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd /c/resilio-plus
git add frontend/src/app/login/ frontend/src/app/register/
git commit -m "feat: add login and register pages with real API calls"
```

---

### Task 5: Dashboard layout (protected) + Dashboard page

**Files:**
- Create: `frontend/src/app/dashboard/layout.tsx`
- Create: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Create `frontend/src/app/dashboard/layout.tsx`**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/navbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("resilio_token");
    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950">
      <Navbar />
      <main className="pt-14 px-6 py-8 max-w-5xl mx-auto">
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/dashboard/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface AthleteProfile {
  id: string;
  email: string;
  first_name: string;
  age: number;
  sex: string;
  weight_kg: number;
  height_cm: number;
  body_fat_percent: number | null;
  resting_hr: number | null;
  max_hr_measured: number | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<AthleteProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<AthleteProfile>("/athletes/me")
      .then(setProfile)
      .catch((err) => {
        if (err?.status === 401) {
          router.replace("/login");
        } else {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 text-sm">Chargement...</div>
      </div>
    );
  }

  if (error) {
    return <p className="text-red-400 text-sm">{error}</p>;
  }

  if (!profile) return null;

  const sexLabel = profile.sex === "M" ? "Homme" : "Femme";

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-100">
        Bonjour, {profile.first_name}
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Profil
          </h3>
          <div className="space-y-2">
            <Row label="Email" value={profile.email} />
            <Row label="Âge" value={`${profile.age} ans`} />
            <Row label="Sexe" value={sexLabel} />
          </div>
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Mesures
          </h3>
          <div className="space-y-2">
            <Row label="Poids" value={`${profile.weight_kg} kg`} />
            <Row label="Taille" value={`${profile.height_cm} cm`} />
            {profile.body_fat_percent != null && (
              <Row label="Masse grasse" value={`${profile.body_fat_percent}%`} />
            )}
            {profile.resting_hr != null && (
              <Row label="FC repos" value={`${profile.resting_hr} bpm`} />
            )}
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
          Navigation rapide
        </h3>
        <div className="flex gap-3">
          <a
            href="/dashboard/calendar"
            className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors"
          >
            Voir mon calendrier
          </a>
          <a
            href="/dashboard/chat"
            className="px-4 py-2 text-sm rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            Chat Head Coach
          </a>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-100">{value}</span>
    </div>
  );
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd /c/resilio-plus/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd /c/resilio-plus
git add frontend/src/app/dashboard/
git commit -m "feat: add protected dashboard layout and profile page"
```

---

### Task 6: Calendar page

**Files:**
- Create: `frontend/src/app/dashboard/calendar/page.tsx`

The calendar calls the real plan API with Simon's demo athlete state. The state object is hardcoded from `tests/conftest.py` Simon profile.

- [ ] **Step 1: Create `frontend/src/app/dashboard/calendar/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { api } from "@/lib/api";

// Simon demo athlete state — matches tests/conftest.py
const SIMON_ATHLETE_STATE = {
  athlete_id: "00000000-0000-0000-0000-000000000001",
  updated_at: new Date().toISOString(),
  profile: {
    first_name: "Simon",
    age: 32,
    sex: "M",
    weight_kg: 78.5,
    height_cm: 178,
    body_fat_percent: 16.5,
    resting_hr: 58,
    max_hr_measured: 188,
    active_sports: ["running", "lifting"],
    available_days: {
      monday:    { available: true,  max_hours: 1.5, preferred_time: "morning" },
      tuesday:   { available: true,  max_hours: 1.5, preferred_time: "evening" },
      wednesday: { available: true,  max_hours: 1.0, preferred_time: "morning" },
      thursday:  { available: true,  max_hours: 1.5, preferred_time: "evening" },
      friday:    { available: false, max_hours: 0,   preferred_time: null },
      saturday:  { available: true,  max_hours: 2.5, preferred_time: "morning" },
      sunday:    { available: true,  max_hours: 2.0, preferred_time: "morning" },
    },
    training_history: {
      total_years_training: 5,
      years_running: 2,
      years_lifting: 4,
      years_swimming: 0.5,
      current_weekly_volume_hours: 7,
      longest_run_ever_km: 15,
      current_5k_time_min: 28.5,
      current_10k_time_min: null,
      current_half_marathon_min: null,
      estimated_1rm: { squat: 120, bench_press: 85, deadlift: 140, overhead_press: 55 },
    },
    injuries_history: [],
    lifestyle: {
      work_type: "desk_sedentary",
      work_hours_per_day: 8,
      commute_active: false,
      sleep_avg_hours: 7.2,
      stress_level: "moderate",
      alcohol_per_week: 2,
      smoking: false,
    },
    goals: {
      primary: "run_sub_25_5k",
      secondary: "maintain_muscle_mass",
      tertiary: "improve_swimming_technique",
      timeline_weeks: 16,
      priority_hierarchy: ["running_5k", "hypertrophy_maintenance", "swimming_technique"],
    },
    equipment: {
      gym_access: true,
      gym_equipment: ["barbell", "dumbbells", "cables", "machines", "pull_up_bar"],
      pool_access: true,
      pool_type: "25m_indoor",
      outdoor_running: true,
      treadmill: false,
      heart_rate_monitor: true,
      gps_watch: "garmin_forerunner_265",
      power_meter_bike: false,
    },
  },
  current_phase: {
    macrocycle: "base_building",
    mesocycle_week: 3,
    mesocycle_length: 4,
  },
  running_profile: {
    vdot: 38.2,
    training_paces: {
      easy_min_per_km: "6:24",
      easy_max_per_km: "7:06",
      marathon_pace_per_km: "5:42",
      threshold_pace_per_km: "5:18",
      interval_pace_per_km: "4:48",
      repetition_pace_per_km: "4:24",
      long_run_pace_per_km: "6:36",
    },
    weekly_km_current: 22,
    weekly_km_target: 35,
    max_long_run_km: 12,
    cadence_avg: 168,
    preferred_terrain: "road",
  },
  lifting_profile: {
    training_split: "upper_lower",
    sessions_per_week: 3,
    current_volume_per_muscle: {
      quadriceps: 8, hamstrings: 6, chest: 10,
      back: 12, shoulders: 8, biceps: 6,
      triceps: 6, calves: 4,
    },
    volume_landmarks: {
      quadriceps: { mev: 6, mav: 10, mrv_hybrid: 12 },
      hamstrings:  { mev: 4, mav: 8,  mrv_hybrid: 10 },
      chest:       { mev: 6, mav: 14, mrv_hybrid: 18 },
      back:        { mev: 6, mav: 14, mrv_hybrid: 20 },
      shoulders:   { mev: 6, mav: 12, mrv_hybrid: 16 },
      biceps:      { mev: 4, mav: 10, mrv_hybrid: 14 },
      triceps:     { mev: 4, mav: 8,  mrv_hybrid: 12 },
      calves:      { mev: 4, mav: 8,  mrv_hybrid: 6  },
    },
    progression_model: "double_progression",
    rir_target_range: [1, 3],
  },
  nutrition_profile: {
    tdee_estimated: 2800,
    macros_target: { protein_g: 160, carbs_g: 300, fat_g: 80 },
    supplements_current: ["creatine_5g"],
    dietary_restrictions: [],
    allergies: [],
  },
};

interface Session {
  day?: string;
  date?: string;
  type?: string;
  sport?: string;
  description?: string;
  [key: string]: unknown;
}

interface PlanResult {
  sessions?: Session[];
  [key: string]: unknown;
}

const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

function sessionBadgeColor(sport: string): string {
  if (sport === "running") return "bg-emerald-900 border-emerald-700 text-emerald-200";
  if (sport === "lifting") return "bg-blue-900 border-blue-700 text-blue-200";
  return "bg-slate-800 border-slate-700 text-slate-300";
}

export default function CalendarPage() {
  const [runPlan, setRunPlan] = useState<PlanResult | null>(null);
  const [liftPlan, setLiftPlan] = useState<PlanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadPlan() {
    setLoading(true);
    setError("");
    try {
      const [run, lift] = await Promise.all([
        api.post<PlanResult>("/plan/running", { athlete_state: SIMON_ATHLETE_STATE }),
        api.post<PlanResult>("/plan/lifting", { athlete_state: SIMON_ATHLETE_STATE }),
      ]);
      setRunPlan(run);
      setLiftPlan(lift);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement du plan");
    } finally {
      setLoading(false);
    }
  }

  // Combine sessions from both plans into a day-indexed map
  const byDay: Record<string, Array<{ sport: string; session: Session }>> = {};
  DAYS.forEach((d) => (byDay[d] = []));

  const dayMap: Record<string, string> = {
    monday: "Lundi",
    tuesday: "Mardi",
    wednesday: "Mercredi",
    thursday: "Jeudi",
    friday: "Vendredi",
    saturday: "Samedi",
    sunday: "Dimanche",
  };

  function addSessions(plan: PlanResult | null, sport: string) {
    if (!plan?.sessions) return;
    plan.sessions.forEach((s) => {
      const dayKey = s.day?.toLowerCase() ?? "";
      const frDay = dayMap[dayKey];
      if (frDay) {
        byDay[frDay].push({ sport, session: s });
      }
    });
  }

  addSessions(runPlan, "running");
  addSessions(liftPlan, "lifting");

  const hasPlan = runPlan !== null || liftPlan !== null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-100">Calendrier hebdomadaire</h2>
        <button
          onClick={loadPlan}
          disabled={loading}
          className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white transition-colors"
        >
          {loading ? "Chargement..." : "Charger plan démo (Simon)"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {!hasPlan && !loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-8 text-center">
          <p className="text-slate-400 text-sm">
            Cliquez sur &quot;Charger plan démo&quot; pour générer un plan hebdomadaire via le Head Coach.
          </p>
        </div>
      )}

      {hasPlan && (
        <div className="grid grid-cols-7 gap-2">
          {DAYS.map((day) => (
            <div key={day} className="space-y-2">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider text-center pb-1 border-b border-slate-800">
                {day.slice(0, 3)}
              </div>
              {byDay[day].length === 0 ? (
                <div className="h-16 rounded border border-dashed border-slate-800 flex items-center justify-center">
                  <span className="text-xs text-slate-600">Repos</span>
                </div>
              ) : (
                byDay[day].map((item, i) => (
                  <div
                    key={i}
                    className={`rounded border p-2 text-xs ${sessionBadgeColor(item.sport)}`}
                  >
                    <div className="font-semibold capitalize mb-1">
                      {item.sport === "running" ? "Course" : "Muscu"}
                    </div>
                    <div className="truncate opacity-80">
                      {String(item.session.type ?? item.session.description ?? item.session.sport ?? "Séance")}
                    </div>
                  </div>
                ))
              )}
            </div>
          ))}
        </div>
      )}

      {hasPlan && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <PlanDetail title="Plan course" plan={runPlan} sport="running" />
          <PlanDetail title="Plan musculation" plan={liftPlan} sport="lifting" />
        </div>
      )}
    </div>
  );
}

function PlanDetail({ title, plan, sport }: { title: string; plan: PlanResult | null; sport: string }) {
  if (!plan) return null;
  const sessions = plan.sessions ?? [];
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3">
      <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      <div className="space-y-2">
        {sessions.map((s, i) => (
          <div key={i} className={`rounded border p-2 text-xs ${sessionBadgeColor(sport)}`}>
            <span className="font-medium capitalize">{String(s.day ?? s.date ?? `Séance ${i + 1}`)}</span>
            {" — "}
            <span className="opacity-80">{String(s.type ?? s.description ?? s.sport ?? "")}</span>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="text-xs text-slate-500">Aucune séance retournée par l&apos;API.</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /c/resilio-plus/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or fix any type errors before proceeding)

- [ ] **Step 3: Commit**

```bash
cd /c/resilio-plus
git add frontend/src/app/dashboard/calendar/
git commit -m "feat: add calendar page with real plan API integration (Simon demo)"
```

---

### Task 7: Chat page

**Files:**
- Create: `frontend/src/app/dashboard/chat/page.tsx`

No backend call — chat endpoint doesn't exist yet.

- [ ] **Step 1: Create `frontend/src/app/dashboard/chat/page.tsx`**

```tsx
"use client";

import { useState, FormEvent, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SYSTEM_MESSAGE: Message = {
  role: "assistant",
  content:
    "Bonjour. Je suis le Head Coach Resilio+. Le mode chat interactif sera disponible dans la prochaine version. " +
    "En attendant, utilisez les pages Plan et Calendrier pour générer vos séances hebdomadaires.",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([SYSTEM_MESSAGE]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    const botReply: Message = {
      role: "assistant",
      content:
        "Le mode chat sera disponible dans la prochaine version. Consultez la page Calendrier pour votre plan de la semaine.",
    };
    setMessages((prev) => [...prev, userMessage, botReply]);
    setInput("");
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <h2 className="text-xl font-semibold text-slate-100 mb-4">Chat — Head Coach</h2>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-1">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-lg px-4 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-violet-700 text-white"
                  : "bg-slate-800 text-slate-200 border border-slate-700"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Écrivez votre message..."
          className="flex-1 px-3 py-2 text-sm rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500"
        />
        <button
          type="submit"
          className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd /c/resilio-plus/frontend
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors

- [ ] **Step 3: Final build check**

```bash
cd /c/resilio-plus/frontend
npm run build 2>&1 | tail -20
```

Expected: successful build (exit 0, 0 TypeScript errors)

- [ ] **Step 4: ESLint check**

```bash
cd /c/resilio-plus/frontend
npm run lint 2>&1 | tail -20
```

Expected: no errors (fix any ESLint issues before committing)

- [ ] **Step 5: Commit**

```bash
cd /c/resilio-plus
git add frontend/src/app/dashboard/chat/
git commit -m "feat: add chat UI shell (Head Coach interface stub)"
```

---

### Task 8: Update CLAUDE.md for S12

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Mark S12 as done in the session table**

Change:
```
| **S12** | Frontend | Next.js — Dashboard + calendrier + chat | ⬜ À FAIRE |
```
to:
```
| **S12** | Frontend | Next.js — Dashboard + calendrier + chat | ✅ FAIT |
```

- [ ] **Step 2: Update file tree for frontend section**

Replace:
```
└── frontend/                          ← ⬜ S12-S13
```
with:
```
├── frontend/                          ← ✅ S12 — Next.js 15 (TypeScript + Tailwind)
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             ← Root layout (Inter font, dark bg)
│   │   │   ├── page.tsx               ← Redirect → /dashboard
│   │   │   ├── login/page.tsx         ← Login form → POST /auth/login
│   │   │   ├── register/page.tsx      ← Register form → POST /auth/register
│   │   │   └── dashboard/
│   │   │       ├── layout.tsx         ← Protected layout + Navbar
│   │   │       ├── page.tsx           ← Profile card (GET /athletes/me)
│   │   │       ├── calendar/page.tsx  ← Weekly grid (POST /plan/running + /lifting)
│   │   │       └── chat/page.tsx      ← Chat UI shell (stub)
│   │   ├── lib/api.ts                 ← Typed fetch wrapper + JWT localStorage
│   │   └── components/navbar.tsx      ← Top nav (links + logout)
```

- [ ] **Step 3: Final full build verification**

```bash
cd /c/resilio-plus/frontend
npm run build 2>&1 | tail -5
```

Expected: build succeeds

- [ ] **Step 4: Commit CLAUDE.md**

```bash
cd /c/resilio-plus
git add CLAUDE.md
git commit -m "chore: mark S12 done in CLAUDE.md — Next.js frontend"
```

- [ ] **Step 5: Push to origin**

```bash
git push origin master
```
