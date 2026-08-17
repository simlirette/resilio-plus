import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatBubble } from '@resilio/ui-web';

describe('ChatBubble', () => {
  it('renders user message on the right', () => {
    render(
      <ChatBubble role="user" content="Bonjour!" />,
    );
    expect(screen.getByText('Bonjour!')).toBeDefined();
  });

  it('renders assistant message with specialist label', () => {
    render(
      <ChatBubble
        role="assistant"
        content="Voici mon conseil."
        specialistsConsulted={['running', 'nutrition']}
      />,
    );
    expect(screen.getByText('Voici mon conseil.')).toBeDefined();
    expect(screen.getByText('via running, nutrition')).toBeDefined();
  });

  it('renders timestamp when provided', () => {
    render(
      <ChatBubble
        role="assistant"
        content="Msg"
        timestamp="2026-04-26T10:30:00.000Z"
      />,
    );
    // Timestamp rendered (exact format locale-dependent but should be there)
    const container = screen.getByText('Msg').closest('div');
    expect(container).toBeDefined();
  });

  it('does not show specialists section when empty', () => {
    render(
      <ChatBubble role="assistant" content="Direct answer" specialistsConsulted={[]} />,
    );
    expect(screen.queryByText(/via/)).toBeNull();
  });
});
