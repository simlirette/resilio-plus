import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card } from './Card';
import { Text } from './Text';
import { IconComponent } from '../Icon';
import type { IconName } from '../Icon';
import { useTheme } from '../theme/ThemeProvider';
import { colors } from '@resilio/design-tokens';

/**
 * Sport types must match WorkoutSlotStub.sport from apps/mobile/src/mocks/athlete-home-stub.ts
 */
export type SportType = 'running' | 'lifting' | 'swimming' | 'cycling' | 'rest';

export interface WorkoutSlotForCard {
  sport: SportType;
  title: string;
  duration_min: number;
  zone: string;
  is_rest_day: boolean;
}

interface SessionCardProps {
  /**
   * Today's planned session.
   * null = no session planned (rest day, not in plan yet, etc.)
   */
  session: WorkoutSlotForCard | null;
}

/**
 * Sport icon mapping. Uses IconComponent (typed wrapper) — no direct lucide JSX.
 * Running → Activity (no dedicated Running icon in lucide-react-native).
 * Unknown sport → Target as safe fallback.
 */
const SPORT_ICON_MAP: Record<SportType, IconName> = {
  running:  'Activity',
  lifting:  'Lifting',
  swimming: 'Swimming',
  cycling:  'Biking',
  rest:     'DarkMode',
};

function SportIcon({ sport, color }: { sport: SportType; color: string }): React.JSX.Element {
  const name: IconName = SPORT_ICON_MAP[sport] ?? 'Target';
  return <IconComponent name={name} size={18} color={color} />;
}

function sportLabel(sport: SportType): string {
  switch (sport) {
    case 'running':  return 'Course';
    case 'lifting':  return 'Musculation';
    case 'swimming': return 'Natation';
    case 'cycling':  return 'Vélo';
    case 'rest':     return 'Repos';
    default:         return 'Séance';
  }
}

export function SessionCard({ session }: SessionCardProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  // Rest day — no session planned
  if (session === null) {
    return (
      <Card>
        <View style={styles.row}>
          <IconComponent name="DarkMode" size={18} color={themeColors.textSecondary} />
          <Text variant="caption" color={themeColors.textSecondary} style={styles.sectionLabel}>
            Séance du jour
          </Text>
        </View>
        <Text variant="body" color={themeColors.textMuted} style={styles.restText}>
          Repos programmé — aucune séance aujourd'hui
        </Text>
      </Card>
    );
  }

  // Active rest day (prescribed recovery)
  if (session.is_rest_day) {
    return (
      <Card>
        <View style={styles.row}>
          <IconComponent name="Heart" size={18} color={themeColors.textSecondary} />
          <Text variant="caption" color={themeColors.textSecondary} style={styles.sectionLabel}>
            Séance du jour
          </Text>
        </View>
        <Text variant="body" color={themeColors.textMuted} style={styles.restText}>
          Repos actif — récupération
        </Text>
      </Card>
    );
  }

  // Normal session
  const sportColor = colors.primary;
  return (
    <Card>
      <View style={styles.row}>
        <SportIcon sport={session.sport} color={themeColors.textSecondary} />
        <Text variant="caption" color={themeColors.textSecondary} style={styles.sectionLabel}>
          Séance du jour
        </Text>
      </View>

      <View style={styles.row}>
        <SportIcon sport={session.sport} color={sportColor} />
        <Text variant="caption" color={sportColor} style={styles.sportLabelAccent}>
          {sportLabel(session.sport)}
        </Text>
      </View>

      <Text variant="body" color={themeColors.foreground} style={styles.title} numberOfLines={2}>
        {session.title}
      </Text>

      <Text variant="caption" color={themeColors.textSecondary} style={styles.zone}>
        {session.zone}
      </Text>

      <View style={styles.durationBadge}>
        <IconComponent name="Clock" size={12} color={colors.primary} />
        <Text variant="caption" color={colors.primary} style={styles.durationText}>
          {session.duration_min} min
        </Text>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  sectionLabel: { textTransform: 'uppercase', letterSpacing: 0.5 },
  restText: { marginTop: 4 },
  sportLabel: { marginLeft: 2 },
  sportLabelAccent: { marginLeft: 2, fontWeight: '600' },
  title: { marginBottom: 6, fontWeight: '600' },
  zone: { marginBottom: 12 },
  durationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    backgroundColor: colors.primaryDim,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  durationText: { marginLeft: 2 },
});
