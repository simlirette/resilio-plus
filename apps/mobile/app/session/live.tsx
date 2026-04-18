import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Card, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import * as Haptics from 'expo-haptics';

export default function LiveSessionScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();
  const [paused, setPaused] = useState(false);

  const handlePause = useCallback(async () => {
    setPaused((p) => !p);
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  }, []);

  const handleEnd = useCallback(async () => {
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    router.replace('/(tabs)' as never);
  }, [router]);

  return (
    <Screen>
      <View style={[styles.header, { borderBottomColor: themeColors.border }]}>
        <View style={styles.headerInfo}>
          <Text variant="label" color={themeColors.textMuted} style={styles.enCours}>
            EN COURS
          </Text>
          <Text variant="body" color={themeColors.foreground} style={styles.sessionTitle}>
            Endurance fondamentale Z2
          </Text>
          <Text variant="secondary" color={themeColors.textMuted} style={styles.elapsed}>
            12:34 / 52:00
          </Text>
        </View>
        <Pressable
          onPress={handlePause}
          style={[styles.pauseBtn, { borderColor: themeColors.border }]}
          accessibilityLabel={paused ? 'Reprendre' : 'Pause'}
        >
          <Text variant="secondary" color={themeColors.foreground}>
            {paused ? '▶' : '⏸'}
          </Text>
        </Pressable>
      </View>

      <ScrollView style={styles.flex} contentContainerStyle={styles.content}>
        <View style={styles.phaseRow}>
          <View style={[styles.phaseDot, { backgroundColor: colors.accent }]} />
          <Text variant="label" color={themeColors.textMuted} style={styles.phaseLabel}>
            BLOC PRINCIPAL · Z2 · 2/3
          </Text>
        </View>

        <Card style={styles.targetCard}>
          <Text variant="label" color={themeColors.textMuted} style={styles.targetLabel}>
            ALLURE CIBLE
          </Text>
          <Text variant="display" color={themeColors.foreground} style={styles.targetValue}>
            5:20
          </Text>
          <Text variant="secondary" color={themeColors.textMuted}>
            min/km
          </Text>
        </Card>

        <View style={styles.statsRow}>
          <Card style={styles.statCard}>
            <Text variant="label" color={themeColors.textMuted} style={styles.statLabel}>FC CIBLE</Text>
            <Text variant="headline" color={themeColors.foreground} style={styles.statValue}>145–155</Text>
            <Text variant="secondary" color={themeColors.textMuted}>bpm</Text>
          </Card>
          <Card style={styles.statCard}>
            <Text variant="label" color={themeColors.textMuted} style={styles.statLabel}>RPE CIBLE</Text>
            <Text variant="headline" color={themeColors.foreground} style={styles.statValue}>5–6</Text>
            <Text variant="secondary" color={themeColors.textMuted}>/ 10</Text>
          </Card>
        </View>

        <Card style={styles.zoneCard}>
          <View style={[styles.zoneBadge, { backgroundColor: colors.accentDim }]}>
            <Text variant="secondary" color={colors.accent}>Zone 2 — Fondamental</Text>
          </View>
          <Text variant="secondary" color={themeColors.textSecondary} style={styles.zoneDesc}>
            Maintiens une allure conversationnelle. Si tu ne peux pas parler, ralentis.
          </Text>
        </Card>
      </ScrollView>

      <View style={[styles.cta, { borderTopColor: themeColors.border, backgroundColor: themeColors.background }]}>
        <Button
          title="Terminer la séance"
          variant="secondary"
          onPress={handleEnd}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
  },
  headerInfo: { flex: 1 },
  enCours: { letterSpacing: 0.6, marginBottom: 2 },
  sessionTitle: { fontWeight: '500', marginBottom: 2 } as const,
  elapsed: { fontVariant: ['tabular-nums'] as const },
  pauseBtn: {
    width: 40, height: 40, borderRadius: 20,
    borderWidth: 1, alignItems: 'center', justifyContent: 'center',
  },
  content: { paddingHorizontal: 20, paddingBottom: 32, paddingTop: 16 },
  phaseRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 16 },
  phaseDot: { width: 8, height: 8, borderRadius: 4 },
  phaseLabel: { letterSpacing: 0.5 },
  targetCard: { alignItems: 'center', paddingVertical: 24, marginBottom: 12 },
  targetLabel: { letterSpacing: 0.8, marginBottom: 8 },
  targetValue: { fontSize: 72, fontWeight: '300', letterSpacing: -2, lineHeight: 72 },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 12 },
  statCard: { flex: 1, alignItems: 'center', paddingVertical: 16 },
  statLabel: { letterSpacing: 0.6, marginBottom: 6 },
  statValue: { fontVariant: ['tabular-nums'] as const },
  zoneCard: { marginBottom: 8 },
  zoneBadge: { borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, alignSelf: 'flex-start', marginBottom: 8 },
  zoneDesc: { lineHeight: 20 },
  cta: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 32, borderTopWidth: 0.5 },
});
