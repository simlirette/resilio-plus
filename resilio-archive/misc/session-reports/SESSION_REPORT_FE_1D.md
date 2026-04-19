# Session FE-1D: API Client Generation & Migration

**Date:** 2026-04-12  
**Branch:** `session/fe-1d-api-client`  
**Status:** ✅ Complete

---

## What was done

### 1. OpenAPI Client Generation
- `pnpm --filter @resilio/api-client generate` → `packages/api-client/src/generated/api.ts`
- Tool: `openapi-typescript@7.13.0` from `http://localhost:8000/openapi.json`
- Generated: TypeScript path/operation/component types for all 40+ backend endpoints

### 2. Auth Wrapper (`packages/api-client/src/helpers.ts`)
- Added `ApiClientError` class with `.status` property
- Added `createClient(baseURL, getToken)` factory with:
  - Dynamic token getter (callback, not static)
  - `request<T>()`: adds `Content-Type: application/json` + `Authorization: Bearer`
  - `rawRequest<T>()`: no Content-Type (multipart/file uploads)
  - Both throw `ApiClientError` with HTTP status + FastAPI `detail` message
- Preserved `createApiClient` (legacy static-token factory) for backward compat

### 3. Re-exports (`packages/api-client/src/index.ts`)
```typescript
export { createClient, createApiClient, setAuthToken, clearAuthToken, getAuthToken, ApiClientError }
export type { paths, operations, components }  // from generated/api.ts
```

### 4. Vitest Tests (`packages/api-client/src/__tests__/client.test.ts`)
6 tests, all passing:
- createClient with static token
- Authorization header injected from getToken callback
- No Authorization header when getToken returns null
- ApiClientError thrown with correct status on non-ok response
- clearAuthToken removes from localStorage
- setAuthToken stores in localStorage

### 5. Migration: `apps/web/src/lib/api.ts`
- Imported `createClient`, `ApiClientError` from `@resilio/api-client`
- Internal `request()` now delegates to `_client.request()` (wraps `ApiClientError` → `ApiError`)
- Internal `_reqRaw()` delegates to `_client.rawRequest()` for file uploads
- `ApiError` class preserved with same signature (re-export compatible)
- Token key `'token'` in localStorage unchanged (zero consumer changes)
- `importExternalPlan` kept as raw fetch (multipart with custom error handling)

### 6. Test fix (`apps/web/src/app/dashboard/__tests__/page.test.tsx`)
- Added `getReadiness: vi.fn().mockResolvedValue(null)` to mock (dashboard calls this)

---

## Verification Results

| Check | Status |
|---|---|
| `pnpm --filter @resilio/api-client test` | ✅ 6/6 pass |
| `pnpm --filter @resilio/web test` | ✅ 26/26 pass |
| `pnpm --filter @resilio/web typecheck` | ✅ 0 errors |
| `pnpm --filter @resilio/web build` | ✅ Success |

---

## Endpoint Coverage

All endpoints in `apps/web/src/lib/api.ts` are covered by the OpenAPI spec.

### Endpoints in OpenAPI but NOT yet in api.ts (documented gaps)

| Endpoint | Method | Notes |
|---|---|---|
| `/athletes/` | GET/POST | Internal admin, not needed by web |
| `/athletes/{id}` | PUT/DELETE | Profile updates not in web yet |
| `/athletes/{id}/plans` | GET | All plans list (web uses /plan) |
| `/athletes/{id}/plan/review/start` | POST | LangGraph coaching workflow |
| `/athletes/{id}/plan/review/confirm` | POST | LangGraph coaching workflow |
| `/athletes/{id}/workflow/*` | GET/POST | Full coaching workflow (V3-D) |
| `/athletes/{id}/mode` | PATCH | coaching_mode switch (V3-B) |
| `/athletes/{id}/recovery-status` | GET | Recovery Coach endpoint |
| `/athletes/{id}/nutrition-directives` | GET | Nutrition Coach endpoint |
| `/athletes/{id}/hormonal-profile` | GET/POST | Hormonal/cycle data |
| `/athletes/{id}/food/search` | GET | Food search (out of scope) |
| `/athletes/{id}/food/barcode/{barcode}` | GET | Barcode scan (out of scope) |
| `/athletes/{id}/food/search/fcen` | GET | FCEN food DB (out of scope) |
| `/athletes/{id}/connectors/strava/callback` | GET | Strava OAuth callback (redirect) |

These gaps are expected. The web app implements the V3-H feature set which is complete.

---

## Infrastructure fix (pre-existing)
- `apps/mobile/package.json`: `@types/react-native@~0.76.0` → `~0.73.0` (non-existent version)
- `apps/mobile/package.json`: `react@18.3.2` → `18.3.1` (non-existent version)
- These were blocking `pnpm install` workspace-wide
