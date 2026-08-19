# FROZEN — apps/web (Next.js)

**Frozen:** 2026-08-19, for Resilio V4 (see `docs/GOAL-V4-TEXT-COACH.md`).

## Why

V4 makes Resilio a coach that texts the athlete on Telegram and writes the
approved week into Google Calendar. The backend was already finished; the
clients were not. Rather than carry three half-built surfaces, all of them are
paused so the one surface that ships gets finished.

Freezing is not deletion. The Phase D chat and onboarding UI (D13/D14) is the reference implementation for any future web surface, and the fastest way to see what the conversational layer is supposed to feel like.

## What still works

- The app builds and runs as it did on 2026-08-19.
- It talks to the same backend; nothing was removed from the API.
- `packages/api-client` and `packages/shared-logic` stay maintained, so the parts a future surface needs do not rot.

## What changed

- Removed from the default `build` / `dev` / `typecheck` scripts at the repo root.
- Still reachable explicitly: `pnpm build:web`, `pnpm dev:web`, `pnpm typecheck:web`, `pnpm lint:web`.
- Still in `pnpm-workspace.yaml` — removing it would break `pnpm install`.
- No source was deleted, no dependency was removed.

## To unfreeze

1. Put the app back into the root `build` / `dev` / `typecheck` scripts.
2. Run `pnpm install` and the explicit commands above; fix whatever drifted.
3. Re-point it at the current backend contract — see `docs/backend/API-CONTRACT.md`.
4. Delete this file in the same commit that re-enables the app, so the freeze
   status is never ambiguous.
