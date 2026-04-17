/**
 * Mock for lucide-react-native.
 * Returns a minimal React component for each icon.
 * Avoids importing the real library which requires native modules.
 */
import React from 'react';
import { View } from 'react-native';

const MockIcon = () => <View testID="mock-icon" />;

// Export every named icon used in Icon.tsx as the same mock
export const Moon = MockIcon;
export const Sun = MockIcon;
export const Trash2 = MockIcon;
export const Plus = MockIcon;
export const Minus = MockIcon;
export const Calendar = MockIcon;
export const ChevronRight = MockIcon;
export const ChevronLeft = MockIcon;
export const ChevronDown = MockIcon;
export const ChevronUp = MockIcon;
export const Check = MockIcon;
export const X = MockIcon;
export const AlertTriangle = MockIcon;
export const AlertCircle = MockIcon;
export const Info = MockIcon;
export const Settings = MockIcon;
export const User = MockIcon;
export const LogOut = MockIcon;
export const LogIn = MockIcon;
export const Activity = MockIcon;
export const BarChart2 = MockIcon;
export const TrendingUp = MockIcon;
export const TrendingDown = MockIcon;
export const Clock = MockIcon;
export const Zap = MockIcon;
export const Heart = MockIcon;
export const Target = MockIcon;
export const Award = MockIcon;
export const Dumbbell = MockIcon;
export const Bike = MockIcon;
export const Waves = MockIcon;
export const Upload = MockIcon;
export const Download = MockIcon;
export const RefreshCw = MockIcon;
export const Edit2 = MockIcon;
export const Save = MockIcon;
export const Link2 = MockIcon;
export const ExternalLink = MockIcon;
export const MessageCircle = MockIcon;
export const Home = MockIcon;

export type LucideProps = {
  size?: number;
  color?: string;
  strokeWidth?: number;
};
