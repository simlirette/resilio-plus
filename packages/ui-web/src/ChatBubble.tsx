'use client';

/**
 * ChatBubble — Phase D (D13)
 * Renders a single chat message bubble for the Head Coach or the user.
 */

interface ChatBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  /** ISO 8601 timestamp string */
  timestamp?: string;
  /** Coaches consulted (shown under assistant messages) */
  specialistsConsulted?: string[];
}

function formatTime(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export function ChatBubble({
  role,
  content,
  timestamp,
  specialistsConsulted,
}: ChatBubbleProps) {
  const isUser = role === 'user';

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
    >
      <div
        className={[
          'max-w-[80%] rounded-2xl px-4 py-2 text-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-card text-card-foreground border border-border',
        ].join(' ')}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{content}</p>

        <div className="mt-1 flex items-center justify-between gap-2">
          {!isUser && specialistsConsulted && specialistsConsulted.length > 0 && (
            <span className="text-xs text-muted-foreground">
              via {specialistsConsulted.join(', ')}
            </span>
          )}
          {timestamp && (
            <span className="ml-auto text-xs text-muted-foreground opacity-70">
              {formatTime(timestamp)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
