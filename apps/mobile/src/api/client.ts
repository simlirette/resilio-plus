export const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export class MobileApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'MobileApiError';
  }
}

export interface MobileApiRequestOptions extends RequestInit {
  token?: string | null;
  timeoutMs?: number;
}

export function getApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL?.trim();
  return (fromEnv || DEFAULT_API_BASE_URL).replace(/\/+$/, '');
}

function normalizeHeaders(headers?: HeadersInit): Record<string, string> {
  if (!headers) return {};
  if (Array.isArray(headers)) return Object.fromEntries(headers);
  if ('entries' in headers && typeof headers.entries === 'function') {
    return Object.fromEntries(headers.entries());
  }
  return { ...(headers as Record<string, string>) };
}

function getErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
}

export async function mobileApiRequest<T>(
  baseUrl: string,
  path: string,
  options: MobileApiRequestOptions = {}
): Promise<T> {
  const { token, timeoutMs = 15000, ...requestOptions } = options;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...normalizeHeaders(requestOptions.headers),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...requestOptions,
      headers,
      signal: controller.signal,
    });

    const text = await response.text();
    const body = text ? JSON.parse(text) : null;

    if (!response.ok) {
      throw new MobileApiError(
        response.status,
        getErrorMessage(body, `Request failed with status ${response.status}`),
        body
      );
    }

    return body as T;
  } catch (error) {
    if (error instanceof MobileApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new MobileApiError(0, 'Request timed out');
    }
    throw new MobileApiError(0, error instanceof Error ? error.message : 'Network request failed');
  } finally {
    clearTimeout(timeout);
  }
}
