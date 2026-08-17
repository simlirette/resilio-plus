import { mobileApiRequest } from './client';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  athlete_id: string;
}

export interface MeResponse {
  athlete_id: string;
  email: string;
  created_at: string;
  is_active: boolean;
}

export function loginRequest(baseUrl: string, payload: LoginRequest): Promise<TokenResponse> {
  return mobileApiRequest<TokenResponse>(baseUrl, '/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function refreshRequest(baseUrl: string, refreshToken: string): Promise<TokenResponse> {
  return mobileApiRequest<TokenResponse>(baseUrl, '/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function logoutRequest(
  baseUrl: string,
  accessToken: string,
  refreshToken: string
): Promise<{ message: string }> {
  return mobileApiRequest<{ message: string }>(baseUrl, '/auth/logout', {
    method: 'POST',
    token: accessToken,
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function meRequest(baseUrl: string, accessToken: string): Promise<MeResponse> {
  return mobileApiRequest<MeResponse>(baseUrl, '/auth/me', {
    method: 'GET',
    token: accessToken,
  });
}

