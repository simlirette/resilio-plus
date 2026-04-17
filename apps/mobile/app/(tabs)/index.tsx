/**
 * Home screen — Resilio+ Mobile
 *
 * Layout:
 * ┌────────────────────────────────────┐
 * │ [Bannière "Repos recommandé"]      │  ← conditionnelle si readiness < 50
 * ├────────────────────────────────────┤
 * │ Bonjour,                           │
 * │ Résumé de coaching du jour         │
 * ├────────────────────────────────────┤
 * │         [Circle size=160]          │  ← Readiness principal
 * │          [ReadinessStatusBadge]    │
 * ├────────────────────────────────────┤
 * │  (●)       (●)       (●)           │  ← MetricRow
 * │ Nutrition  Récup.   Sommeil        │
 * ├────────────────────────────────────┤
 * │  [CognitiveLoadDial — card]        │  ← label="Charge allostatique"
 * ├────────────────────────────────────┤
 * │  [SessionCard]                     │
 * ├────────────────────────────────────┤
 * │     [ Check-in quotidien ]         │  ← Button primary
 * └────────────────────────────────────┘
 *
 * Data source: useHomeData() → mockHomeData (FE-MOBILE-2)
 * To test different scenarios, change the import in src/hooks/useHomeData.ts.
 *
 * StyleSheet exception: contentContainerStyle on ScrollView (NativeWind cannot
 * target contentContainerStyle). All other styles use className (NativeWind).
 */
import React, { useCallback } from 'react';
import { View, ScrollView, RefreshControl, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useRouter } from 'expo-router';
import {
  Screen,
  Text,
  Circle,
  Card,
  Button,
  CognitiveLoadDial,
  MetricRow,
  ReadinessStatusBadge,
  SessionCard,
  useTheme,
} from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import { useHomeData } from '../../src/hooks/useHomeData';
import type { WorkoutSlotStub } from '../../src/types/home';
import type { WorkoutSlotForCard } from '@resilio/ui-mobile';

function mapSession(s: WorkoutSlotStub): WorkoutSlotForCard {
  return {
    sport: s.sport,
    title: s.title,
    duration_min: s.duration_min,
    zone: s.zone,
    is_rest_day: s.is_rest_day,
  };
}

function readinessColor(value: number): string {
  if (value >= 70) return colors.zoneGreen;
  if (value >= 50) return colors.zoneYellow;
  return colors.zoneRed;
}

export default function HomeScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();
  const { data, loading, refresh } = useHomeData();

  const handleRefresh = useCallback(async () => {
    await refresh();
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  }, [refresh]);

  const handleCheckin = useCallback(() => {
    router.push('/(tabs)/check-in');
  }, [router]);

  const readiness = data.readiness.value;
  const showRestBanner = readiness < 50;
  const circleColor = readinessColor(readiness);

  const todaySession = data.todaysSessions?.[0] ?? null;

  return (
    <Screen>
      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={loading}
            onRefresh={handleRefresh}
            tintColor={themeColors.textSecondary}
          />
        }
      >
        {/* ── Bannière repos recommandé ─────────────────────────────────────── */}
        {showRestBanner && (
          <View
            className="rounded-xl px-4 py-3 mb-4"
            style={{ backgroundColor: colors.zoneRedBg }}
            accessibilityRole="alert"
            accessibilityLabel="Repos recommandé — ton score de forme est bas"
          >
            <Text variant="body" color={colors.zoneRed}>
              Repos recommandé — ton score de forme est bas
            </Text>
          </View>
        )}

        {/* ── Greeting ──────────────────────────────────────────────────────── */}
        <View className="mb-8">
          <Text variant="title" color={themeColors.foreground}>
            Bonjour,
          </Text>
          <Text variant="body" color={themeColors.textSecondary}>
            Résumé de coaching du jour
          </Text>
        </View>

        {/* ── Readiness principal ────────────────────────────────────────────── */}
        <View
          className="items-center mb-8"
          accessibilityLabel={`Score de forme : ${readiness} sur 100`}
        >
          <Circle
            value={readiness}
            size={160}
            color={circleColor}
          />
          <View className="mt-3">
            <ReadinessStatusBadge value={readiness} />
          </View>
        </View>

        {/* ── Sous-métriques ─────────────────────────────────────────────────── */}
        <View className="mb-8">
          <MetricRow
            nutrition={data.nutrition}
            strain={data.strain}
            sleep={data.sleep}
          />
        </View>

        {/* ── Charge allostatique ────────────────────────────────────────────── */}
        <Card style={styles.cardSpacing}>
          <View className="items-center">
            <CognitiveLoadDial
              value={data.cognitiveLoad.value}
              state={data.cognitiveLoad.state}
              size={180}
              label="Charge allostatique"
            />
          </View>
        </Card>

        {/* ── Séance du jour ─────────────────────────────────────────────────── */}
        <View style={styles.cardSpacing}>
          <SessionCard session={todaySession ? mapSession(todaySession) : null} />
        </View>

        {/* ── CTA Check-in ───────────────────────────────────────────────────── */}
        {/* Button.primary handles haptics internally (ImpactFeedbackStyle.Medium) */}
        <Button
          variant="primary"
          title="Check-in quotidien"
          onPress={handleCheckin}
        />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  // flex:1 on ScrollView (NativeWind className="flex-1" targets View wrapper only)
  flex: { flex: 1 },
  // contentContainerStyle: NativeWind cannot target this prop on ScrollView
  content: { paddingHorizontal: 24, paddingVertical: 24, paddingBottom: 48 },
  cardSpacing: { marginBottom: 16 },
});
