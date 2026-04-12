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
 *   import { createClient } from '@resilio/api-client';
 *   const client = createClient('http://localhost:8000', () => localStorage.getItem('token'));
 */

export type { ApiToken } from './helpers';
export {
  createApiClient,
  createClient,
  setAuthToken,
  getAuthToken,
  clearAuthToken,
  ApiClientError,
} from './helpers';

// Re-export generated OpenAPI types
export type { paths, operations, components } from './generated/api';
