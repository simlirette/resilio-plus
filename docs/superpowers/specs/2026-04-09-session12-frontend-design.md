# Session 12 — Frontend: Dashboard + Calendar + Chat

## Goal

Bootstrap the Next.js 15 frontend and implement three core screens: authentication flow (login/register), a dashboard showing the authenticated athlete's profile, a weekly training calendar that calls the plan API, and a chat UI shell. The frontend connects to the FastAPI backend running on `localhost:8000`.

---

## Architecture

```
frontend/src/app/
  page.tsx                   ← root redirect → /dashboard or /login
  layout.tsx                 ← root layout (fonts, globals.css)
  login/page.tsx             ← POST /api/v1/auth/login → store token
  register/page.tsx          ← POST /api/v1/auth/register → store token
  dashboard/
    layout.tsx               ← protected layout (redirect if no token) + Navbar
    page.tsx                 ← GET /api/v1/athletes/me → profile card
    calendar/page.tsx        ← calls /plan/running + /plan/lifting → weekly grid
    chat/page.tsx            ← UI shell (chat endpoint not yet implemented)

frontend/src/lib/
  api.ts                     ← typed fetch wrapper (base URL, auth header, error handling)

frontend/src/components/
  navbar.tsx                 ← nav links: Dashboard | Calendar | Chat | Logout
```

**Auth token**: stored in `localStorage` under key `resilio_token`. The `api.ts` wrapper reads it and adds `Authorization: Bearer <token>` to every request. Redirect to `/login` if token is absent on any protected page.

**Backend URL**: `http://localhost:8000` — hardcoded for dev in `lib/api.ts`. Will move to env var in S14.

---

## Tech Stack

- **Next.js 15** — App Router, TypeScript, `src/` directory
- **Tailwind CSS v3** — utility-first styling, minimal custom CSS
- **No UI component library** — Tailwind is sufficient for V1 (YAGNI)
- **No global state manager** — React useState + localStorage (YAGNI)

---

## `frontend/src/lib/api.ts`

```typescript
const API_BASE = "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("resilio_token");
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
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  get: <T>(path: string) => request<T>(path),
};
```

---

## Pages

### Login (`/login`)

Form with `email` and `password` fields. On submit:
- `POST /auth/login` → store `access_token` in localStorage → redirect to `/dashboard`
- Error: display `detail` message below form

### Register (`/register`)

Form with `email`, `password`, `first_name`, `age`, `sex`, `weight_kg`, `height_cm`. On submit:
- `POST /auth/register` → store `access_token` → redirect to `/dashboard`
- Error: display `detail` message

### Dashboard (`/dashboard`)

On mount: `GET /athletes/me` → display profile card with `first_name`, `age`, `weight_kg`, `height_cm`. Loading spinner while fetching. 401 → redirect to `/login`.

```
┌─────────────────────────┐
│  Bonjour, Simon         │
│  32 ans — 78.5 kg       │
│  Athlète Resilio+       │
└─────────────────────────┘
```

### Calendar (`/dashboard/calendar`)

Two sections: Running Plan and Lifting Plan. A "Charger mon plan" button triggers calls to:
- `POST /plan/running` with the Simon demo athlete state
- `POST /plan/lifting` with the Simon demo athlete state

Results displayed as weekly cards (one per session, grouped by day of week):

```
Lundi      Mardi      Mercredi    Jeudi     Vendredi   Samedi     Dimanche
[Run: easy][Lift: UB] [Run: tempo][Lift: LB][  REST  ] [Run: long][  REST  ]
```

The Simon demo athlete state is a hardcoded constant in the page (matches `tests/conftest.py` Simon profile). This is explicit: the button label says "Charger plan démo (Simon)".

### Chat (`/dashboard/chat`)

A chat-style UI: message bubble list + text input at the bottom. Since `POST /chat/message` doesn't exist yet, submitting shows a system message:

> "Le mode chat avec le Head Coach sera disponible dans la prochaine version. En attendant, utilisez les pages Plan et Calendrier."

The form submission is handled client-side only — no API call.

---

## Navbar

Fixed top bar:
- Left: "Resilio+" logo/wordmark
- Center links: Dashboard | Calendrier | Chat
- Right: `first_name` from localStorage (stored at login) + Logout button (clears token, redirects to `/login`)

---

## Styling Guide

- Background: `slate-950` (dark) — dark theme only for V1
- Cards: `slate-900` rounded border `slate-800`
- Accent: `violet-500` (primary buttons, active nav link)
- Text primary: `slate-100`, secondary: `slate-400`
- Font: Inter (Next.js default)

Dark theme only — no light/dark toggle (YAGNI).

---

## Files Summary

| File | Action |
|------|--------|
| `frontend/package.json` | Create — Next.js 15 + TypeScript + Tailwind |
| `frontend/next.config.ts` | Create |
| `frontend/tailwind.config.ts` | Create |
| `frontend/postcss.config.mjs` | Create |
| `frontend/tsconfig.json` | Create |
| `frontend/src/app/globals.css` | Create |
| `frontend/src/app/layout.tsx` | Create |
| `frontend/src/app/page.tsx` | Create — redirect |
| `frontend/src/app/login/page.tsx` | Create |
| `frontend/src/app/register/page.tsx` | Create |
| `frontend/src/app/dashboard/layout.tsx` | Create |
| `frontend/src/app/dashboard/page.tsx` | Create |
| `frontend/src/app/dashboard/calendar/page.tsx` | Create |
| `frontend/src/app/dashboard/chat/page.tsx` | Create |
| `frontend/src/lib/api.ts` | Create |
| `frontend/src/components/navbar.tsx` | Create |
| `CLAUDE.md` | Modify — S12 ✅ FAIT |

---

## Invariants post-S12

- `npm run build` in `frontend/` succeeds with 0 TypeScript errors
- `npm run lint` passes with 0 ESLint errors
- Login → Dashboard flow works end-to-end with the real backend (requires backend running on :8000)
- Logout clears token and redirects to `/login`
- 401 from any protected page redirects to `/login`
- Calendar demo loads a real plan from the backend
- No backend calls from the chat page
