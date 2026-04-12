/**
 * @resilio/ui-mobile — Icon abstraction layer (React Native / Expo)
 *
 * RULE: Never import lucide-react-native directly in apps/mobile.
 * Always import from @resilio/ui-mobile instead.
 *
 * Mirror of @resilio/ui-web/src/icons.ts — same semantic names, different source.
 * Populated in Vague 1 Session M (Expo setup).
 */

// Placeholder: lucide-react-native is not installed yet (Vague 1).
// This file establishes the contract. Uncomment when Expo is scaffolded.

// import {
//   Moon, Sun, Trash2, Plus, ...
// } from 'lucide-react-native';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IconComponent = any;

export const Icon: Record<string, IconComponent> = {
  // Populated in Vague 1 — Expo scaffold session
  // Same semantic keys as @resilio/ui-web/src/icons.ts
};

export type IconName = keyof typeof Icon;
