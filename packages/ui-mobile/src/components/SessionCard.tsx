import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card } from './Card';
import { Text } from './Text';
import { IconComponent } from '../Icon';
import type { IconName } from '../Icon';
import { useTheme } from '../theme/ThemeProvider';

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

const SPORT_ICON_MAP: Record<SportType, IconName> = {
  running:  'Activity',
  lifting:  'Lifting',
  swimming: 'Swimming',
  cycling:  'Biking',
  rest:     'DarkMode',
};

function SportIcon({ sport, color }: { sport: SportType; color: string }): React.JSX.Element {
  const name: IconName = SPORT_ICON_MAP[sport] ?? 'Target';
  return <IconComponent name={name} size={16} color={color} />;
}

/** Extract short zone badge: "Zone 1 (60–74% FCmax)" → "Z1", "MEV — volume modéré" → "MEV" */
function zoneBadge(zone: string): string {
  const match = zone.match(/[Zz]one\s+(\d+)/);
  if (match) return `Z${match[1]}`;
  return zone.split(/[\s—]+/)[0] ?? zone.substring(0, 5);
}

export function SessionCard({ session }: SessionCardProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  if (session === null) {
    return (
      <Card style={styles.cardPad}>
        <View style={styles.labelRow}>
          <IconComponent name="DarkMode" size={14} color={themeColors.textMuted} />
          <Text variant="label" color={themeColors.textMuted} style={styles.sectionLabel}>
            Séance du jour
          </Text>
        </View>
        <Text variant="body" color={themeColors.textSecondary} style={styles.restText}>
          Repos programmé — aucune séance aujourd'hui
        </Text>
      </Card>
    );
  }

  if (session.is_rest_day) {
    return (
      <Card style={styles.cardPad}>
        <View style={styles.labelRow}>
          <IconComponent name="Heart" size={14} color={themeColors.textMuted} />
          <Text variant="label" color={themeColors.textMuted} style={styles.sectionLabel}>
            Séance du jour
          </Text>
        </View>
        <Text variant="body" color={themeColors.textSecondary} style={styles.restText}>
          Repos actif — récupération
        </Text>
      </Card>
    );
  }

  // Normal session — side-by-side: content left, chevron right
  return (
    <Card style={styles.cardPad}>
      <View style={styles.row}>
        {/* Left content */}
        <View style={styles.leftContent}>
          {/* Label row: icon + SÉANCE DU JOUR + zone badge */}
          <View style={styles.labelRow}>
            <SportIcon sport={session.sport} color={themeColors.textMuted} />
            <Text variant="label" color={themeColors.textMuted} style={styles.sectionLabel}>
              Séance du jour
            </Text>
            <View style={[styles.zoneBadge, { backgroundColor: themeColors.surface2 }]}>
              <Text variant="label" color={themeColors.textSecondary} style={styles.zoneText}>
                {zoneBadge(session.zone)}
              </Text>
            </View>
          </View>

          {/* Session title */}
          <Text variant="body" color={themeColors.foreground} style={styles.title} numberOfLines={2}>
            {session.title}
          </Text>

          {/* Meta: duration · zone on one line */}
          <Text variant="secondary" color={themeColors.textSecondary} numberOfLines={1} style={styles.meta}>
            {session.duration_min} min · {session.zone}
          </Text>
        </View>

        {/* Chevron */}
        <View style={[styles.chevronCircle, { backgroundColor: themeColors.surface2 }]}>
          <IconComponent name="ChevronRight" size={14} color={themeColors.textSecondary} />
        </View>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  cardPad: { padding: 18 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  leftContent: { flex: 1 },
  labelRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  sectionLabel: { textTransform: 'uppercase' },
  zoneBadge: { paddingHorizontal: 7, paddingVertical: 2, borderRadius: 4 },
  zoneText: { textTransform: 'uppercase' },
  title: { fontFamily: 'SpaceGrotesk_500Medium', fontSize: 17, letterSpacing: -0.3, lineHeight: 21, marginBottom: 6 },
  meta: { marginBottom: 2 },
  restText: { marginTop: 2 },
  chevronCircle: {
    width: 36, height: 36, borderRadius: 18,
    alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
});
