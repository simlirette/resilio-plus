import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { Screen, Text, Card, DisciplineIcon, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

type SportType = 'running' | 'lifting' | 'swimming' | 'cycling' | 'rest';

interface SessionRecord {
  id: string;
  date: string;
  sport: SportType;
  title: string;
  duration_min: number;
  load: 'Légère' | 'Modérée' | 'Élevée';
  completed: boolean;
}

const MOCK_SESSIONS: SessionRecord[] = [
  { id: '1', date: 'VEN 18 AVR', sport: 'running', title: 'Endurance fondamentale', duration_min: 52, load: 'Modérée', completed: true },
  { id: '2', date: 'MER 16 AVR', sport: 'lifting', title: 'Musculation haut du corps', duration_min: 65, load: 'Élevée', completed: true },
  { id: '3', date: 'LUN 14 AVR', sport: 'running', title: 'Récupération active', duration_min: 35, load: 'Légère', completed: true },
  { id: '4', date: 'SAM 12 AVR', sport: 'cycling', title: 'Endurance vélo Z2', duration_min: 90, load: 'Modérée', completed: true },
  { id: '5', date: 'VEN 11 AVR', sport: 'lifting', title: 'Musculation bas du corps', duration_min: 60, load: 'Élevée', completed: false },
];

type ViewMode = 'list' | 'cal';

export default function TrainingScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const [view, setView] = useState<ViewMode>('list');

  return (
    <Screen>
      <ScrollView style={styles.flex} contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text variant="title" color={themeColors.foreground}>Entraînement</Text>
        </View>

        <View style={[styles.segmented, { backgroundColor: themeColors.surface2, borderColor: themeColors.border }]}>
          {(['list', 'cal'] as ViewMode[]).map((mode) => {
            const active = view === mode;
            return (
              <Pressable
                key={mode}
                style={[styles.segmentBtn, active && { backgroundColor: themeColors.surface1 }]}
                onPress={() => setView(mode)}
              >
                <Text
                  variant="secondary"
                  color={active ? themeColors.foreground : themeColors.textSecondary}
                >
                  {mode === 'list' ? 'Liste' : 'Calendrier'}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {view === 'cal' ? (
          <Card style={styles.calPlaceholder}>
            <Text variant="secondary" color={themeColors.textSecondary}>
              Vue calendrier — disponible prochainement.
            </Text>
          </Card>
        ) : (
          <View style={styles.list}>
            {MOCK_SESSIONS.map((session) => {
              const dotColor = session.completed ? colors.zoneGreen : themeColors.textMuted;
              return (
                <Card key={session.id} style={styles.sessionRow}>
                  <View style={styles.sessionLeft}>
                    <Text variant="label" color={themeColors.textMuted} style={styles.sessionDate}>
                      {session.date}
                    </Text>
                    <View style={styles.sessionTitleRow}>
                      <DisciplineIcon sport={session.sport} size={14} color={themeColors.textMuted} />
                      <Text variant="body" color={themeColors.foreground} style={styles.sessionTitle}>
                        {session.title}
                      </Text>
                    </View>
                    <Text variant="secondary" color={themeColors.textSecondary}>
                      {session.duration_min} min · {session.load}
                    </Text>
                  </View>
                  <View style={[styles.statusDot, { backgroundColor: dotColor }]} />
                </Card>
              );
            })}
          </View>
        )}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingBottom: 48 },
  header: { paddingHorizontal: 24, paddingTop: 14, paddingBottom: 20 },
  segmented: {
    flexDirection: 'row',
    marginHorizontal: 20,
    borderRadius: 12,
    borderWidth: 0.5,
    padding: 3,
    marginBottom: 20,
  },
  segmentBtn: { flex: 1, alignItems: 'center', paddingVertical: 8, borderRadius: 10 },
  calPlaceholder: { marginHorizontal: 20, alignItems: 'center', paddingVertical: 40 },
  list: { paddingHorizontal: 20, gap: 8 },
  sessionRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  sessionLeft: { flex: 1, gap: 3 },
  sessionDate: { letterSpacing: 0.6 },
  sessionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sessionTitle: { flex: 1 },
  statusDot: { width: 8, height: 8, borderRadius: 4, marginLeft: 12 },
});
