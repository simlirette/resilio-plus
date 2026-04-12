/**
 * @resilio/api-client — Auth helpers and base client factory
 */

export type ApiToken = string | null;

const TOKEN_KEY = 'resilio_token';

export function getAuthToken(): ApiToken {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface ApiClientConfig {
  baseUrl: string;
  token?: ApiToken;
}

/**
 * Minimal fetch wrapper — will be replaced by generated client (pnpm generate).
 * Provides JWT Authorization header injection.
 */
export function createApiClient(config: ApiClientConfig) {
  const { baseUrl, token } = config;

  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const resolvedToken = token ?? getAuthToken();
    if (resolvedToken) {
      headers['Authorization'] = `Bearer ${resolvedToken}`;
    }

    const response = await fetch(`${baseUrl}${path}`, { ...options, headers });

    if (!response.ok) {
      throw new Error(`API error ${response.status}: ${response.statusText}`);
    }

    return response.json() as Promise<T>;
  }

  return { request };
}
