/**
 * @resilio/shared-logic — Formatters
 * Pure formatting utilities — no UI dependencies.
 */

/** Format duration in minutes → "1h30" or "45'" */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}'`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h${String(m).padStart(2, '0')}` : `${h}h`;
}

/** Format distance in meters → "5.2 km" or "800 m" */
export function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${meters} m`;
}

/** Format running pace in seconds/km → "4'32\"" */
export function formatPace(secondsPerKm: number): string {
  const min = Math.floor(secondsPerKm / 60);
  const sec = Math.round(secondsPerKm % 60);
  return `${min}'${String(sec).padStart(2, '0')}"`;
}

/** Format a date string (ISO) → "lun. 14 avril" (fr-FR) */
export function formatDate(isoDate: string, locale = 'fr-FR'): string {
  return new Date(isoDate).toLocaleDateString(locale, {
    weekday: 'short',
    day: 'numeric',
    month: 'long',
  });
}

/** Format a percentage → "87%" */
export function formatPercent(value: number, decimals = 0): string {
  return `${value.toFixed(decimals)}%`;
}

/** Format ACWR ratio → "1.12" or "—" for null */
export function formatAcwr(value: number | null): string {
  if (value === null) return '—';
  return value.toFixed(2);
}
