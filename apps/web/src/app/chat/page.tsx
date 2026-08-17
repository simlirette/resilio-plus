'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { ProtectedRoute } from '@/components/protected-route';
import { ChatBubble, TappableOptions } from '@resilio/ui-web';
import { createChatClient } from '@resilio/api-client';
import type {
  ChatHistoryMessage,
  ChatHistoryResponse,
  ChatMessageResponse,
} from '@resilio/api-client';

// ── Types ─────────────────────────────────────────────────────────────────

interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  specialists?: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────

function historyToDisplay(msgs: ChatHistoryMessage[]): DisplayMessage[] {
  return msgs.map((m) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: m.created_at,
    specialists: m.specialists_consulted ?? undefined,
  }));
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── Page ──────────────────────────────────────────────────────────────────

function ChatPageInner() {
  const { athleteId, token } = useAuth() as {
    athleteId: string | null;
    token: string | null;
    logout: () => void;
  };

  const chatClient = createChatClient(API_BASE, () => token);

  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [clarificationAxes, setClarificationAxes] = useState<string[] | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastIntents, setLastIntents] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load history on mount
  useEffect(() => {
    if (!athleteId) return;
    chatClient
      .getHistory(athleteId)
      .then((h: ChatHistoryResponse) => setMessages(historyToDisplay(h.messages)))
      .catch(() => {/* ignore — no history yet */});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [athleteId]);

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!athleteId || !text.trim() || isLoading) return;

      const userMsg: DisplayMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInputValue('');
      setClarificationAxes(null);
      setIsLoading(true);

      try {
        const resp: ChatMessageResponse = await chatClient.sendMessage({
          athlete_id: athleteId,
          user_message: text,
          last_3_intents: lastIntents,
        });

        const assistantMsg: DisplayMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: resp.final_response,
          timestamp: new Date().toISOString(),
          specialists: resp.specialists_consulted.length > 0
            ? resp.specialists_consulted
            : undefined,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Update last 3 intents
        setLastIntents((prev) => [...prev, resp.intent_decision].slice(-3));

        // Show tappable axes for CLARIFICATION_NEEDED
        if (resp.clarification_axes && resp.clarification_axes.length > 0) {
          setClarificationAxes(resp.clarification_axes);
        }
      } catch {
        const errorMsg: DisplayMessage = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: "Une erreur s'est produite. Réessaie dans un moment.",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [athleteId, chatClient, isLoading, lastIntents],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(inputValue);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border px-4 py-3">
        <h1 className="text-base font-semibold text-foreground">Head Coach</h1>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && !isLoading && (
          <p className="text-center text-sm text-muted-foreground mt-8">
            Pose une question à ton Head Coach.
          </p>
        )}

        {messages.map((msg) => (
          <ChatBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp}
            specialistsConsulted={msg.specialists}
          />
        ))}

        {/* Typing indicator during loading */}
        {isLoading && (
          <div className="flex justify-start mb-3">
            <div className="bg-card text-card-foreground border border-border rounded-2xl px-4 py-2 text-sm">
              <span className="animate-pulse text-muted-foreground">···</span>
            </div>
          </div>
        )}

        {/* Clarification tappable options */}
        {clarificationAxes && (
          <TappableOptions
            axes={clarificationAxes}
            onSelect={(axis) => void sendMessage(axis)}
          />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message…"
            disabled={isLoading}
            className={[
              'flex-1 rounded-full border border-border bg-card px-4 py-2 text-sm',
              'text-card-foreground placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-primary/50',
              'disabled:opacity-50',
            ].join(' ')}
          />
          <button
            type="button"
            onClick={() => void sendMessage(inputValue)}
            disabled={isLoading || !inputValue.trim()}
            className={[
              'rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
              'hover:bg-primary/90 disabled:opacity-50 transition-colors',
            ].join(' ')}
          >
            Envoyer
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatPageInner />
    </ProtectedRoute>
  );
}
