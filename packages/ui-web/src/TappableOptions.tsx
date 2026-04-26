'use client';

import { useState } from 'react';

/**
 * TappableOptions — Phase D (D13)
 * Displays tappable clarification axes. Disappears after one selection.
 */

interface TappableOptionsProps {
  axes: string[];
  onSelect: (selected: string) => void;
}

export function TappableOptions({ axes, onSelect }: TappableOptionsProps) {
  const [selected, setSelected] = useState<string | null>(null);

  if (selected !== null) return null; // disappear after tap

  return (
    <div className="flex flex-wrap gap-2 my-2">
      {axes.map((axis) => (
        <button
          key={axis}
          type="button"
          onClick={() => {
            setSelected(axis);
            onSelect(axis);
          }}
          className={[
            'rounded-full border border-border px-3 py-1 text-sm',
            'bg-card text-card-foreground',
            'hover:bg-accent hover:text-accent-foreground',
            'dark:hover:bg-accent dark:hover:text-accent-foreground',
            'transition-colors cursor-pointer',
          ].join(' ')}
        >
          {axis}
        </button>
      ))}
    </div>
  );
}
