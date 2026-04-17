/**
 * @resilio/ui-mobile — Icon abstraction layer (React Native / Expo)
 *
 * RULE: Never import lucide-react-native directly in apps/mobile or any other file.
 * This is the SOLE authorized importer of lucide-react-native.
 *
 * Two usage patterns:
 *   1. Object pattern: <Icon.Heart size={20} color={...} /> (backward compat)
 *   2. Name pattern:   <IconComponent name="Heart" size={20} color={...} />
 *
 * Mirror of @resilio/ui-web/src/icons.ts — same semantic names, RN source.
 */
import React from 'react';
import {
  Moon, Sun, Trash2, Plus, Minus, Calendar, ChevronRight, ChevronLeft,
  ChevronDown, ChevronUp, Check, X, AlertTriangle, AlertCircle, Info,
  Settings, User, LogOut, LogIn, Activity, BarChart2, TrendingUp, TrendingDown,
  Clock, Zap, Heart, Target, Award, Dumbbell, Bike, Waves,
  Upload, Download, RefreshCw, Edit2, Save, Link2, ExternalLink,
  MessageCircle, Home, type LucideProps,
} from 'lucide-react-native';

// ── Object pattern (backward compat with existing screens) ───────────────────
export const Icon = {
  DarkMode: Moon, LightMode: Sun,
  Add: Plus, Remove: Minus, Delete: Trash2, Edit: Edit2, Save: Save,
  Upload: Upload, Download: Download, Refresh: RefreshCw, Link: Link2, ExternalLink: ExternalLink,
  ChevronRight, ChevronLeft, ChevronDown, ChevronUp,
  Check, Close: X, Warning: AlertTriangle, Error: AlertCircle, Info,
  Calendar, Settings, User, LogOut, LogIn, Home,
  Activity, Analytics: BarChart2, TrendingUp, TrendingDown, Clock,
  Energy: Zap, Heart, Target, Award, Lifting: Dumbbell, Biking: Bike, Swimming: Waves,
  Chat: MessageCircle,
} as const;

export type IconName = keyof typeof Icon;

// ── Single-component pattern (named prop API) ────────────────────────────────
export interface IconComponentProps {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
}

/**
 * <IconComponent name="Heart" size={20} color={colors.zoneGreen} />
 * Alternative to the object pattern when icon name is dynamic.
 */
export function IconComponent({ name, size = 20, color, strokeWidth }: IconComponentProps): React.JSX.Element {
  const Component = Icon[name] as React.ComponentType<LucideProps>;
  return <Component size={size} color={color} strokeWidth={strokeWidth} />;
}
