/**
 * Onboarding API client — Phase D (D14)
 *
 * Wraps POST /onboarding/start and POST /onboarding/respond.
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export interface OnboardingStartRequest {
  athlete_id: string;
}

export interface OnboardingRespondRequest {
  thread_id: string;
  user_response: string;
}

export interface OnboardingBlockResponse {
  thread_id: string;
  current_block: number;
  question: string | null;
  status: 'in_progress' | 'completed' | 'suspended';
  collected_data?: Record<string, string> | null;
  journey_phase?: string;
}

// ── Client ────────────────────────────────────────────────────────────────────

export function createOnboardingClient(
  baseUrl: string,
  getToken: () => string | null,
) {
  function authHeaders(): Record<string, string> {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
  }

  return {
    start(athleteId: string): Promise<OnboardingBlockResponse> {
      return post<OnboardingBlockResponse>('/onboarding/start', {
        athlete_id: athleteId,
      });
    },

    respond(
      threadId: string,
      userResponse: string,
    ): Promise<OnboardingBlockResponse> {
      return post<OnboardingBlockResponse>('/onboarding/respond', {
        thread_id: threadId,
        user_response: userResponse,
      });
    },
  };
}
