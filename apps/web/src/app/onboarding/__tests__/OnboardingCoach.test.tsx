import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createOnboardingClient } from '@resilio/api-client';

// ── createOnboardingClient unit tests ─────────────────────────────────────────

describe('createOnboardingClient', () => {
  const BASE = 'http://localhost:8000';

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('start() calls POST /onboarding/start with athlete_id', async () => {
    const mockResp = {
      thread_id: 'a1:onboarding:uuid',
      current_block: 1,
      question: 'Bonjour, présente-toi.',
      status: 'in_progress',
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResp),
    });

    const client = createOnboardingClient(BASE, () => 'tok');
    const result = await client.start('athlete-1');

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/onboarding/start',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ athlete_id: 'athlete-1' }),
      }),
    );
    expect(result.thread_id).toBe('a1:onboarding:uuid');
    expect(result.question).toBe('Bonjour, présente-toi.');
  });

  it('respond() calls POST /onboarding/respond with thread_id + user_response', async () => {
    const mockResp = {
      thread_id: 'a1:onboarding:uuid',
      current_block: 2,
      question: "Quel est ton âge ?",
      status: 'in_progress',
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResp),
    });

    const client = createOnboardingClient(BASE, () => 'tok');
    const result = await client.respond('a1:onboarding:uuid', 'Je cours depuis 2 ans.');

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/onboarding/respond',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          thread_id: 'a1:onboarding:uuid',
          user_response: 'Je cours depuis 2 ans.',
        }),
      }),
    );
    expect(result.current_block).toBe(2);
  });

  it('start() sends Authorization header when token provided', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ thread_id: 't', current_block: 1, question: 'Q', status: 'in_progress' }),
    });

    const client = createOnboardingClient(BASE, () => 'my-token');
    await client.start('a1');

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    expect((callArgs[1].headers as Record<string, string>)['Authorization']).toBe('Bearer my-token');
  });

  it('start() throws on non-ok response', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: () => Promise.resolve('Athlete not found'),
    });

    const client = createOnboardingClient(BASE, () => null);
    await expect(client.start('bad-id')).rejects.toThrow('404');
  });

  it('completed status has no question', async () => {
    const mockResp = {
      thread_id: 'a1:onboarding:uuid',
      current_block: 7,
      question: null,
      status: 'completed',
      journey_phase: 'baseline_pending_confirmation',
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResp),
    });

    const client = createOnboardingClient(BASE, () => 'tok');
    const result = await client.respond('a1:onboarding:uuid', 'Oui, je confirme.');
    expect(result.status).toBe('completed');
    expect(result.question).toBeNull();
    expect(result.journey_phase).toBe('baseline_pending_confirmation');
  });
});
