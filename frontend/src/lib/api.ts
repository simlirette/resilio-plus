/**
 * API client for Resilio+ backend (localhost:8000)
 * JWT token stored in localStorage under "resilio_token"
 */

const API_BASE = "http://localhost:8000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("resilio_token");
}

export function setToken(token: string, firstName: string): void {
  localStorage.setItem("resilio_token", token);
  localStorage.setItem("resilio_first_name", firstName);
}

export function clearToken(): void {
  localStorage.removeItem("resilio_token");
  localStorage.removeItem("resilio_first_name");
}

export function getFirstName(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("resilio_first_name") ?? "";
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
    const error = Object.assign(new Error(String(err.detail ?? "Request failed")), {
      status: res.status,
    });
    throw error;
  }

  return res.json() as Promise<T>;
}

export const api = {
  post: <T>(path: string, body: unknown): Promise<T> =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  get: <T>(path: string): Promise<T> => request<T>(path),
};
