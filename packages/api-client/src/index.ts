/**
 * @resilio/api-client
 *
 * Generated TypeScript client for the Resilio+ FastAPI backend.
 * Uses openapi-typescript for type generation.
 *
 * SETUP:
 *   Run `pnpm generate` with the backend running at http://localhost:8000
 *   to regenerate src/generated/api.ts from the OpenAPI spec.
 *
 * USAGE (after generation):
 *   import { createApiClient } from '@resilio/api-client';
 *   const client = createApiClient({ baseUrl: 'http://localhost:8000', token });
 */

export type { ApiToken } from './helpers';
export { createApiClient, setAuthToken, getAuthToken, clearAuthToken } from './helpers';
