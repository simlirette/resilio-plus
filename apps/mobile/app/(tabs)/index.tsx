/**
 * Home screen — Resilio+ Mobile
 * Design v2 (2026-04-17) — Warm minimalist, Apple Health / Whoop 5.0 inspired.
 * Source: Claude Design handoff RbXZRFnMZI1nsG_v0vkzMw
 *
 * Layout:
 * ┌────────────────────────────────────┐
 * │ Bonjour, Simon-Olivier             │  ← Greeting (px 24)
 * │ Vendredi 17 avril                  │
 * ├────────────────────────────────────┤
 * │  [Bannière repos recommandé]       │  ← Conditionnelle si readiness < 50
 * ├────────────────────────────────────┤
 * │       ┌──────────────────┐         │
 * │       │  [Circle 216px]  │         │  ← Readiness ring accent color
 * │       └──────────────────┘         │
 * │        [ReadinessStatusBadge]      │
 * ├────────────────────────────────────┤
 * │  [Card: MetricRow Nut/Rcup/Sleep]  │  ← px 20
 * ├────────────────────────────────────┤
 * │  [Card: Allostatic — text | dial]  │  ← px 20, side-by-side layout
 * ├────────────────────────────────────┤
 * │  [SessionCard]                     │  ← px 20
 * ├────────────────────────────────────┤
 * │     [ Check-in quotidien ]         │  ← Button primary, px 20
 * └────────────────────────────────────┘
 *
 * Data source: useHomeData() → GET /mobile/home
 * StyleSheet exception: contentContainerStyle on ScrollView (NativeWind cannot
 * target contentContainerStyle). All other styles use StyleSheet.
 */
import React, { useCallback } from 'react';
import { View, ScrollView, RefreshControl, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { useFocusEffect, useRouter } from 'expo-router';
import {
  Screen,
  Text,
  Circle,
  Card,
  Button,
  CognitiveLoadDial,
  ReadinessStatusBadge,
  SessionCard,
  useTheme,
} from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import { useHomeData } from '../../src/hooks/useHomeData';
import type { MetricState, MetricStatus, WorkoutSlotStub } from '../../src/types/home';
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

function knownState(state: MetricState): 'green' | 'yellow' | 'red' {
  return state === 'unknown' ? 'yellow' : state;
}

function statusLabel(status: MetricStatus): string {
  switch (status) {
    case 'measured':
      return 'Mesure';
    case 'estimated':
      return 'Estime';
    case 'unavailable':
      return 'En attente';
    default:
      return 'En attente';
  }
}

export default function HomeScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors, colorMode } = useTheme();
  const { data, loading, error, refresh } = useHomeData();

  const handleRefresh = useCallback(async () => {
    await refresh();
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  }, [refresh]);

  const handleCheckin = useCallback(() => {
    router.push('/(tabs)/check-in');
  }, [router]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  if (!data) {
    return (
      <Screen>
        <View style={styles.centerState}>
          <Card style={styles.stateCard}>
            <Text variant="title" color={themeColors.foreground}>
              {loading ? 'Chargement' : 'Accueil indisponible'}
            </Text>
            <Text variant="body" color={themeColors.textSecondary} style={styles.stateText}>
              {error ?? 'Synchronisation avec le backend en cours.'}
            </Text>
            {error ? (
              <Button title="Reessayer" onPress={refresh} variant="secondary" style={styles.stateButton} />
            ) : null}
          </Card>
        </View>
      </Screen>
    );
  }

  const readiness = data.readiness.value;
  const showRestBanner = readiness !== null && readiness < 50;

  const todaySession = data.todaysSessions?.[0] ?? null;

  // Today's date formatted
  const today = new Date();
  const dateStr = today.toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
  const dateCap = dateStr.charAt(0).toUpperCase() + dateStr.slice(1);

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
        {/* ── Greeting ──────────────────────────────────────────────────────── */}
        <View style={styles.greetingSection}>
          <Text
            variant="title"
            color={themeColors.foreground}
          >
            Bonjour, Simon-Olivier
          </Text>
          <Text
            variant="secondary"
            color={themeColors.textSecondary}
            style={styles.dateText}
          >
            {dateCap}
          </Text>
        </View>

        {/* ── Bannière repos recommandé ─────────────────────────────────────── */}
        {showRestBanner && (
          <View
            style={[styles.restBanner, { backgroundColor: colorMode === 'dark' ? 'rgba(239,68,68,0.12)' : 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.20)' }]}
            accessibilityRole="alert"
            accessibilityLabel="Repos recommandé — ton score de forme est bas"
          >
            <Text variant="body" color={colors.zoneRed}>
              Repos recommandé — ton score de forme est bas
            </Text>
          </View>
        )}

        {/* ── Readiness ring (dominant) ──────────────────────────────────────── */}
        {readiness !== null ? (
          <View
            style={styles.readinessSection}
            accessibilityLabel={`Score de forme : ${readiness} sur 100`}
          >
            <Circle
              value={readiness}
              size={216}
              strokeWidth={10}
              color={colors.accent}
              innerLabel="Readiness"
            />
            <View style={styles.badgeContainer}>
              <ReadinessStatusBadge value={readiness} />
            </View>
          </View>
        ) : (
          <View style={styles.cardRow}>
            <Card style={styles.stateCard}>
              <Text variant="label" color={themeColors.textMuted}>READINESS</Text>
              <Text variant="body" color={themeColors.textSecondary} style={styles.stateText}>
                Check-in requis pour calculer ton etat du jour.
              </Text>
              <Button title="Check-in quotidien" onPress={handleCheckin} style={styles.stateButton} />
            </Card>
          </View>
        )}

        {/* ── Row 3 metric rings ──────────────────────────────────────────────── */}
        <View style={styles.cardRow}>
          <Card style={styles.metricCard}>
            <View style={styles.signalRow}>
              <Text variant="caption" color={themeColors.textSecondary}>Nutrition</Text>
              <Text variant="body" color={themeColors.foreground}>
                {data.nutrition.calories_target ? `${data.nutrition.calories_target} kcal cible` : 'En attente'}
              </Text>
              <Text variant="caption" color={themeColors.textMuted}>{statusLabel(data.nutrition.status)}</Text>
            </View>
            <View style={[styles.signalDivider, { backgroundColor: themeColors.border }]} />
            <View style={styles.signalRow}>
              <Text variant="caption" color={themeColors.textSecondary}>Récup.</Text>
              <Text variant="body" color={themeColors.foreground}>
                {data.strain.value !== null ? `${Math.round(data.strain.value)} / 100` : 'Connecteurs requis'}
              </Text>
              <Text variant="caption" color={themeColors.textMuted}>{statusLabel(data.strain.status)}</Text>
            </View>
            <View style={[styles.signalDivider, { backgroundColor: themeColors.border }]} />
            <View style={styles.signalRow}>
              <Text variant="caption" color={themeColors.textSecondary}>Sommeil</Text>
              <Text variant="body" color={themeColors.foreground}>
                {data.sleep.sleep_hours !== null ? `${data.sleep.sleep_hours} h` : 'Connecteur requis'}
              </Text>
              <Text variant="caption" color={themeColors.textMuted}>{statusLabel(data.sleep.status)}</Text>
            </View>
          </Card>
        </View>

        {/* ── Charge allostatique card ────────────────────────────────────────── */}
        <View style={styles.cardRow}>
          <Card style={styles.allostaticCard}>
            {/* Side-by-side: text left, dial right */}
            <View style={styles.allostaticRow}>
              <View style={styles.allostaticLeft}>
                <Text
                  variant="label"
                  color={themeColors.textMuted}
                  style={styles.allostaticLabel}
                >
                  CHARGE ALLOSTATIQUE
                </Text>
                <Text
                  variant="body"
                  color={themeColors.textSecondary}
                  style={styles.allostaticDesc}
                >
                  Stress cumulé 7 jours.
                </Text>
              </View>
              {data.cognitiveLoad.value !== null ? (
                <CognitiveLoadDial
                  value={data.cognitiveLoad.value}
                  state={knownState(data.cognitiveLoad.state)}
                  size={160}
                />
              ) : (
                <View style={styles.allostaticPending}>
                  <Text variant="body" color={themeColors.textSecondary}>
                    Check-in requis
                  </Text>
                </View>
              )}
            </View>
            {/* 0 / 50 / 100 legend */}
            <View style={styles.legend}>
              <Text variant="label" color={themeColors.textMuted} style={styles.legendText}>0</Text>
              <Text variant="label" color={themeColors.textMuted} style={styles.legendText}>50</Text>
              <Text variant="label" color={themeColors.textMuted} style={styles.legendText}>100</Text>
            </View>
          </Card>
        </View>

        {/* ── Séance du jour ─────────────────────────────────────────────────── */}
        <View style={styles.cardRow}>
          <SessionCard session={todaySession ? mapSession(todaySession) : null} />
        </View>

        {/* ── CTA Check-in ───────────────────────────────────────────────────── */}
        <View style={styles.cardRow}>
          <Button
            variant="primary"
            title="Check-in quotidien"
            onPress={handleCheckin}
          />
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingBottom: 48 },
  centerState: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  stateCard: { padding: 20 },
  stateText: { marginTop: 10 },
  stateButton: { marginTop: 18 },

  greetingSection: {
    paddingHorizontal: 24,
    paddingTop: 14,
    paddingBottom: 20,
  },
  dateText: { marginTop: 6 },

  restBanner: {
    marginHorizontal: 20,
    marginBottom: 16,
    borderRadius: 12,
    borderWidth: 0.5,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },

  readinessSection: {
    paddingHorizontal: 24,
    paddingBottom: 20,
    alignItems: 'center',
  },
  badgeContainer: { marginTop: 18 },

  cardRow: {
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  metricCard: { paddingHorizontal: 18, paddingVertical: 16 },
  signalRow: {
    minHeight: 46,
    justifyContent: 'center',
  },
  signalDivider: { height: 0.5, marginVertical: 8 },

  allostaticCard: { padding: 20 },
  allostaticRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' },
  allostaticLeft: { flex: 1, paddingRight: 12, justifyContent: 'flex-start' },
  allostaticLabel: { textTransform: 'uppercase', marginBottom: 6 },
  allostaticDesc: { fontSize: 13, lineHeight: 18, letterSpacing: -0.05 },
  allostaticPending: {
    width: 160,
    height: 160,
    alignItems: 'center',
    justifyContent: 'center',
  },

  legend: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  legendText: {
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    fontVariant: ['tabular-nums'] as const,
  },
});
