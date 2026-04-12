/**
 * @resilio/shared-logic — Validators
 * Pure business logic validation — no UI dependencies.
 */

/** RPE (Rate of Perceived Exertion) must be between 1 and 10 */
export function isValidRpe(rpe: number): boolean {
  return Number.isInteger(rpe) && rpe >= 1 && rpe <= 10;
}

/** ACWR safe zone: 0.8–1.3 */
export function isAcwrSafe(acwr: number): boolean {
  return acwr >= 0.8 && acwr <= 1.3;
}

/** ACWR caution zone: 1.3–1.5 */
export function isAcwrCaution(acwr: number): boolean {
  return acwr > 1.3 && acwr <= 1.5;
}

/** ACWR danger zone: > 1.5 */
export function isAcwrDanger(acwr: number): boolean {
  return acwr > 1.5;
}

/** Volume increase must not exceed 10% per week */
export function isVolumeIncreaseValid(previousVolume: number, newVolume: number): boolean {
  if (previousVolume === 0) return true;
  return (newVolume - previousVolume) / previousVolume <= 0.1;
}

/** Valid sport values */
export const VALID_SPORTS = ['running', 'lifting', 'swimming', 'biking'] as const;
export type Sport = (typeof VALID_SPORTS)[number];

export function isValidSport(sport: string): sport is Sport {
  return (VALID_SPORTS as readonly string[]).includes(sport);
}

/** Allostatic score zone */
export type AllostaticZone = 'green' | 'yellow' | 'red' | 'critical';

export function allostaticZone(score: number): AllostaticZone {
  if (score <= 40) return 'green';
  if (score <= 60) return 'yellow';
  if (score <= 80) return 'red';
  return 'critical';
}
