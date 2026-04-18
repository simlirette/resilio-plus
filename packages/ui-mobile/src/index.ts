// Icon abstraction (sole importer of lucide-react-native)
export { Icon, IconComponent } from './Icon';
export type { IconName, IconComponentProps } from './Icon';

// Theme
export { ThemeProvider, useTheme } from './theme/ThemeProvider';
export type { ColorMode, ThemeContextValue } from './theme/ThemeProvider';

// Components
export { Button } from './components/Button';
export { Card } from './components/Card';
export { HeroNumber } from './components/HeroNumber';
export { ProgressSegments } from './components/ProgressSegments';
export { SegmentedControl } from './components/SegmentedControl';
export { Circle } from './components/Circle';
export { CognitiveLoadDial } from './components/CognitiveLoadDial';
export type { DialState } from './components/CognitiveLoadDial';
export { Input } from './components/Input';
export { FloatingLabelInput } from './components/FloatingLabelInput';
export { MetricRow } from './components/MetricRow';
export { ReadinessStatusBadge } from './components/ReadinessStatusBadge';
export { Screen } from './components/Screen';
export { SessionCard } from './components/SessionCard';
export type { WorkoutSlotForCard, SportType as CardSportType } from './components/SessionCard';
export { Text } from './components/Text';
