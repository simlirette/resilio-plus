/**
 * Chat API client — Phase D (D13)
 * POST /chat/message  — send a message
 * GET  /chat/history  — get recent chat history
 */

export interface ChatMessageRequest {
  athlete_id: string;
  user_message: string;
  last_3_intents?: string[];
  last_user_message?: string;
}

export interface ChatMessageResponse {
  final_response: string;
  intent_decision: string;
  specialists_consulted: string[];
  clarification_axes: string[] | null;
  thread_id: string | null;
}

export interface ChatHistoryMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent_decision: string | null;
  specialists_consulted: string[] | null;
  created_at: string;
}

export interface ChatHistoryResponse {
  athlete_id: string;
  messages: ChatHistoryMessage[];
}

export function createChatClient(baseUrl: string, getToken: () => string | null) {
  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${baseUrl}${path}`, { ...options, headers });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? `HTTP ${response.status}`);
    }
    return response.json() as Promise<T>;
  }

  return {
    sendMessage(body: ChatMessageRequest): Promise<ChatMessageResponse> {
      return request<ChatMessageResponse>('/chat/message', {
        method: 'POST',
        body: JSON.stringify(body),
      });
    },

    getHistory(athleteId: string, limit = 20): Promise<ChatHistoryResponse> {
      return request<ChatHistoryResponse>(
        `/chat/history/${encodeURIComponent(athleteId)}?limit=${limit}`,
      );
    },
  };
}
