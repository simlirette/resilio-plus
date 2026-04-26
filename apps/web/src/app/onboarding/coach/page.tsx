'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { ProtectedRoute } from '@/components/protected-route';
import { createOnboardingClient } from '@resilio/api-client';
import type { OnboardingBlockResponse } from '@resilio/api-client';

// ── Constants ─────────────────────────────────────────────────────────────────

const BLOCK_LABELS: Record<number, string> = {
  1: 'Accueil',
  2: 'Profil',
  3: 'Objectif',
  4: 'Historique',
  5: 'Préférences',
  6: 'Confirmation',
};
const TOTAL_BLOCKS = 6;
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: 'coach' | 'athlete';
  text: string;
}

// ── Stepper ───────────────────────────────────────────────────────────────────

function Stepper({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-1 py-3 px-4 border-b border-border overflow-x-auto">
      {Array.from({ length: TOTAL_BLOCKS }, (_, i) => {
        const block = i + 1;
        const done = block < current;
        const active = block === current;
        return (
          <div key={block} className="flex items-center gap-1 shrink-0">
            <div
              className={[
                'flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
                done
                  ? 'bg-primary/40 text-primary-foreground'
                  : active
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground',
              ].join(' ')}
            >
              {done ? '✓' : block}
            </div>
            <span
              className={[
                'text-xs hidden sm:inline',
                active ? 'text-foreground font-medium' : 'text-muted-foreground',
              ].join(' ')}
            >
              {BLOCK_LABELS[block]}
            </span>
            {block < TOTAL_BLOCKS && (
              <div className="h-px w-4 bg-border shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Page inner ────────────────────────────────────────────────────────────────

function CoachOnboardingInner() {
  const router = useRouter();
  const { athleteId, token } = useAuth() as {
    athleteId: string | null;
    token: string | null;
  };

  const client = createOnboardingClient(API_BASE, () => token);

  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [currentBlock, setCurrentBlock] = useState(1);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isResumed, setIsResumed] = useState(false);
  const [completed, setCompleted] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Start onboarding on mount
  useEffect(() => {
    if (!athleteId) return;
    setIsLoading(true);
    client
      .start(athleteId)
      .then((resp: OnboardingBlockResponse) => {
        setThreadId(resp.thread_id);
        setCurrentBlock(resp.current_block);
        if (resp.current_block > 1) {
          setIsResumed(true);
        }
        if (resp.question) {
          setMessages([{ id: 'q-1', role: 'coach', text: resp.question }]);
        }
      })
      .catch(() => {
        setMessages([{
          id: 'err-start',
          role: 'coach',
          text: "Impossible de démarrer l'onboarding. Réessaie dans un moment.",
        }]);
      })
      .finally(() => setIsLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [athleteId]);

  const sendResponse = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || !threadId || isLoading || completed) return;

    const athleteMsg: Message = {
      id: `a-${Date.now()}`,
      role: 'athlete',
      text,
    };
    setMessages((prev) => [...prev, athleteMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      const resp: OnboardingBlockResponse = await client.respond(threadId, text);
      setCurrentBlock(resp.current_block);

      if (resp.status === 'completed') {
        setCompleted(true);
        setMessages((prev) => [
          ...prev,
          {
            id: `q-done`,
            role: 'coach',
            text:
              "Parfait ! Ton profil est complet. Je génère ton plan de base — tu seras redirigé vers ton tableau de bord.",
          },
        ]);
        setTimeout(() => router.replace('/dashboard'), 2500);
      } else if (resp.question) {
        const q = resp.question;
        setMessages((prev) => [
          ...prev,
          { id: `q-${resp.current_block}`, role: 'coach', text: q },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'coach',
          text: "Une erreur s'est produite. Réessaie dans un moment.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [client, completed, inputValue, isLoading, router, threadId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendResponse();
    }
  };

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="border-b border-border px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-foreground">
            Configuration du profil
          </h1>
          {isResumed && (
            <p className="text-xs text-muted-foreground">Session reprise</p>
          )}
        </div>
      </header>

      {/* Stepper */}
      <Stepper current={Math.min(currentBlock, TOTAL_BLOCKS)} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && isLoading && (
          <p className="text-center text-sm text-muted-foreground mt-8">
            Démarrage de l'onboarding…
          </p>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={[
              'flex',
              msg.role === 'athlete' ? 'justify-end' : 'justify-start',
            ].join(' ')}
          >
            <div
              className={[
                'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
                msg.role === 'athlete'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card text-card-foreground border border-border',
              ].join(' ')}
            >
              {msg.text}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-card text-card-foreground border border-border rounded-2xl px-4 py-2 text-sm">
              <span className="animate-pulse text-muted-foreground">···</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {!completed && (
        <div className="border-t border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ta réponse…"
              disabled={isLoading || messages.length === 0}
              className={[
                'flex-1 rounded-full border border-border bg-card px-4 py-2 text-sm',
                'text-card-foreground placeholder:text-muted-foreground',
                'focus:outline-none focus:ring-2 focus:ring-primary/50',
                'disabled:opacity-50',
              ].join(' ')}
            />
            <button
              type="button"
              onClick={() => void sendResponse()}
              disabled={isLoading || !inputValue.trim() || messages.length === 0}
              className={[
                'rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground',
                'hover:bg-primary/90 disabled:opacity-50 transition-colors',
              ].join(' ')}
            >
              Envoyer
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CoachOnboardingPage() {
  return (
    <ProtectedRoute>
      <CoachOnboardingInner />
    </ProtectedRoute>
  );
}
