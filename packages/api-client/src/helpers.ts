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

export class ApiClientError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiClientError';
  }
}

/**
 * createClient — factory with dynamic token getter (callback style).
 * Preferred over createApiClient for React context integration.
 */
export function createClient(baseURL: string, getToken: () => string | null) {
  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${baseURL}${path}`, { ...options, headers });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message = (body as { detail?: string }).detail ?? `Request failed`;
      throw new ApiClientError(response.status, message);
    }

    return response.json() as Promise<T>;
  }

  async function rawRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${baseURL}${path}`, { ...options, headers });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message = (body as { detail?: string }).detail ?? `Request failed`;
      throw new ApiClientError(response.status, message);
    }

    return response.json() as Promise<T>;
  }

  return { request, rawRequest };
}

/**
 * createApiClient — legacy factory with static/stored token.
 * Use createClient for new code.
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
      throw new ApiClientError(response.status, response.statusText);
    }

    return response.json() as Promise<T>;
  }

  return { request };
}
