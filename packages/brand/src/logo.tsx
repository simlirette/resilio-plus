import React from 'react';

type LogoSize = 'sm' | 'md' | 'lg';

interface LogoProps {
  size?: LogoSize;
  /** Override the color mode. Defaults to 'dark'. */
  mode?: 'dark' | 'light';
  className?: string;
}

const sizeMap: Record<LogoSize, { fontSize: string; lineHeight: string }> = {
  sm: { fontSize: '0.875rem', lineHeight: '1.25rem' },  // text-sm
  md: { fontSize: '1rem', lineHeight: '1.5rem' },        // text-base
  lg: { fontSize: '1.25rem', lineHeight: '1.75rem' },    // text-xl
};

const PRIMARY = '#5b5fef';
const WORDMARK_DARK = '#eeeef4';
const WORDMARK_LIGHT = '#0f0f18';

/**
 * Resilio+ wordmark component (React / web).
 * "RESILIO" in foreground color, "+" in primary accent (#5b5fef).
 */
export function Logo({ size = 'md', mode = 'dark', className }: LogoProps) {
  const { fontSize, lineHeight } = sizeMap[size];
  const wordmarkColor = mode === 'dark' ? WORDMARK_DARK : WORDMARK_LIGHT;

  return (
    <span
      className={className}
      style={{
        fontFamily: "'Space Grotesk', system-ui, sans-serif",
        fontWeight: 700,
        letterSpacing: '0.1em',
        fontSize,
        lineHeight,
        color: wordmarkColor,
        userSelect: 'none',
      }}
    >
      RESILIO<span style={{ color: PRIMARY }}>+</span>
    </span>
  );
}
