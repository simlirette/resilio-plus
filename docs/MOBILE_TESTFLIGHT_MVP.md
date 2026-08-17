# Resilio+ Mobile TestFlight MVP

Date: 2026-04-26

This document is the short source of truth for turning the Expo scaffold into a
private TestFlight app backed by the real API.

## Target

Ship an iOS TestFlight build that lets a private tester complete this loop:

1. Log in with a real backend account.
2. Land on a home screen populated by backend data.
3. Submit the daily check-in.
4. See today's planned workout and log a minimal result.
5. Log simple nutrition for the day.
6. See profile/session/connectors state without placeholder claims.

## Current State

Done in Phase 0:

- Expo SDK 55 package contract is locked in `package.json` and `pnpm-lock.yaml`.
- Local `node_modules` can be realigned with `corepack pnpm install --frozen-lockfile`.
- Expo icon, splash, and adaptive icon assets exist under `apps/mobile/assets`.
- Mobile README now describes the scaffold truth instead of calling it production-ready.

Done in Phase 1:

- Login calls `POST /auth/login` instead of accepting local mock credentials.
- Access and refresh tokens are stored in `expo-secure-store`.
- App bootstrap refreshes the session and loads `GET /auth/me`.
- Auth and tab route groups redirect based on real session state.
- Profile shows session basics and can call backend logout.

Done in Phase 2 partial:

- Backend exposes `GET /mobile/home` for the authenticated athlete.
- Mobile home uses the backend aggregate instead of `mockHomeData`.
- Missing readiness, strain, sleep, or connector data is shown as unavailable instead of fabricated.
- Check-in mobile submits backend `CheckInInput` to `POST /athletes/{athlete_id}/checkin`.

Still not functional:

- `apps/mobile/app/(tabs)/chat.tsx` is a placeholder.
- Nutrition is still target-only; there is no food journal/adherence loop yet.
- Workout detail/logging mobile screens are not implemented yet.

## Mobile API Contract For First Functional Loop

Use existing backend routes first:

| Flow | Endpoint | Mobile use |
|---|---|---|
| Login | `POST /auth/login` | Get `access_token`, `refresh_token`, `athlete_id`. |
| Refresh | `POST /auth/refresh` | Rotate tokens after 401/expiry. |
| Logout | `POST /auth/logout` | Revoke refresh token. |
| Session bootstrap | `GET /auth/me` | Restore user and athlete id on app launch. |
| Daily check-in | `POST /{athlete_id}/checkin` | Submit `work_intensity`, `stress_level`, `legs_feeling`, `energy_global`. |
| Readiness | `GET /{athlete_id}/readiness` | Feed home readiness after check-in. |
| Today's workout | `GET /{athlete_id}/today` | Feed home workout card and workout detail screen. |
| Nutrition today | `GET /{athlete_id}/nutrition-today` | Feed home nutrition summary until food journal exists. |
| Connectors | `GET /{athlete_id}/connectors` | Feed profile/connectors status. |

Add one backend endpoint in Phase 2:

| Flow | Endpoint | Mobile use |
|---|---|---|
| Home aggregate | `GET /mobile/home` or `GET /{athlete_id}/mobile/home` | Return the complete home payload with safe empty states. |

The aggregate endpoint should not invent data. It must distinguish measured,
estimated, and unavailable values once data-quality flags are added.

## Session Gates

Every Claude Code session must include:

- Scope: exact phase/session from the implementation plan.
- Constraint: no unrelated refactors and no silent mock replacements.
- Tests: at least one backend or mobile check relevant to the session.
- Done criteria: app still typechecks and the changed user flow can be described in one sentence.

Every Codex review after a phase must check:

- P0/P1 regressions before architecture polish.
- Whether the mobile UI tells the truth about backend data availability.
- Whether tokens, secrets, and user data are stored or logged safely.
- Whether tests cover the critical branch introduced by the phase.

## Promotion Rules

Do not start a new phase until:

- All P0/P1 findings from the previous Codex review are fixed.
- P2 findings are either fixed or explicitly moved to the backlog.
- `corepack pnpm typecheck:mobile` passes.
- Backend targeted tests for the touched area pass.
