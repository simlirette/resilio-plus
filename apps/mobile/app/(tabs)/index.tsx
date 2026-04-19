/**
 * Home screen — P6 rewrite (2026-04-19)
 * Source: docs/design/homedashboard/ (screenshots = visual contract)
 *
 * Layout (top → bottom, scrollable):
 *   Header (greeting + date + avatar "SR" — tap to cycle DEV states)
 *   ReadinessRingHome (160px, semantic color, delta)
 *   MetricsStrip (Nutrition kcal/target + bar, Strain, Sommeil)
 *   HomeSessionCard (discipline + targets + full-width CTA footer)
 *   CognitiveLoadBar (24 segments, semantic color)
 *
 * Removed from P3: MetricRow, SessionCard, CognitiveLoadDial, ReadinessStatusBadge
 * (candidates for deletion after Expo Go test — see docs/p6-home-plan.md)
 *
 * Expo Go SDK 54 safe: no reanimated, no @gorhom. Ring is static (no mount animation).
 */
import React, { useState, useCallback } from 'react';
import { View, ScrollView, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native';
import Svg, { Circle as SvgCircle } from 'react-native-svg';
import * as Haptics from 'expo-haptics';
import { Screen, Card, Text, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import { DASH_MOCK, nextDashState } from '../../src/mocks/home-dashboard-mock';
import type { DashState, HomeDashSession } from '../../src/mocks/home-dashboard-mock';

// ─── Semantic color helpers ───────────────────────────────────────────────────

type ColorMode = 'light' | 'dark';

function readinessColor(value: number, mode: ColorMode): string {
  if (value >= 80) return colors.physio.green[mode];
  if (value >= 60) return colors.physio.yellow[mode];
  return colors.physio.red[mode];
}

function strainColor(semanticValue: number, mode: ColorMode): string {
  if (semanticValue >= 18) return colors.physio.red[mode];
  if (semanticValue >= 14) return colors.physio.yellow[mode];
  return colors.physio.green[mode];
}

function sleepColor(score: number, mode: ColorMode): string {
  if (score >= 80) return colors.physio.green[mode];
  if (score >= 65) return colors.physio.yellow[mode];
  return colors.physio.red[mode];
}

function cognitiveColor(value: number, mode: ColorMode): string {
  if (value >= 70) return colors.physio.red[mode];
  if (value >= 45) return colors.physio.yellow[mode];
  return colors.physio.green[mode];
}

// ─── ReadinessRingHome ────────────────────────────────────────────────────────

interface ReadinessRingProps {
  value: number;
  delta: number;
  colorMode: ColorMode;
}

function ReadinessRingHome({ value, delta, colorMode }: ReadinessRingProps): React.JSX.Element {
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const ringColor = readinessColor(value, colorMode);
  const clampedValue = Math.min(100, Math.max(0, value));
  const size = 160;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - clampedValue / 100);
  const deltaStr = `${delta > 0 ? '+' : ''}${delta} vs hier`;

  return (
    <View style={s.ringContainer}>
      <View style={{ width: size, height: size }}>
        <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Track */}
          <SvgCircle
            cx={size / 2} cy={size / 2} r={radius}
            stroke={themeColors.track} strokeWidth={strokeWidth} fill="none"
          />
          {/* Progress arc */}
          <SvgCircle
            cx={size / 2} cy={size / 2} r={radius}
            stroke={ringColor} strokeWidth={strokeWidth} fill="none"
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            rotation="-90"
            origin={`${size / 2}, ${size / 2}`}
          />
        </Svg>
        {/* Center content */}
        <View style={[StyleSheet.absoluteFill, s.ringCenter]}>
          <Text
            variant="body"
            color={themeColors.foreground}
            style={s.ringValue}
          >
            {clampedValue}
          </Text>
          <Text
            variant="label"
            color={themeColors.textMuted}
            style={s.ringLabel}
          >
            READINESS
          </Text>
          <Text
            variant="label"
            color={ringColor}
            style={s.ringDelta}
          >
            {deltaStr}
          </Text>
        </View>
      </View>
    </View>
  );
}

// ─── MetricsStrip ─────────────────────────────────────────────────────────────

interface MetricsStripProps {
  nutrition: { kcal: number; target: number };
  strain: { displayValue: string; semanticValue: number };
  sleep: { duration: string; score: number };
  colorMode: ColorMode;
}

function MetricsStrip({ nutrition, strain, sleep, colorMode }: MetricsStripProps): React.JSX.Element {
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const nutritionPct = Math.min(100, (nutrition.kcal / nutrition.target) * 100);
  const sColor = strainColor(strain.semanticValue, colorMode);
  const slColor = sleepColor(sleep.score, colorMode);

  return (
    <View style={s.stripRow}>
      {/* Nutrition */}
      <View style={s.stripCol}>
        <Text variant="label" color={themeColors.textMuted} style={s.stripLabel}>NUTRITION</Text>
        <View style={s.stripValueRow}>
          <Text variant="body" color={themeColors.foreground} style={s.stripValue}>
            {nutrition.kcal}
          </Text>
          <Text variant="body" color={themeColors.textMuted} style={s.stripValue}>
            {' / '}{nutrition.target}
          </Text>
        </View>
        <Text variant="label" color={themeColors.textMuted} style={s.stripSub}>kcal</Text>
        {/* Progress bar */}
        <View style={[s.progressTrack, { backgroundColor: themeColors.track }]}>
          <View style={[s.progressFill, {
            width: `${nutritionPct}%` as `${number}%`,
            backgroundColor: themeColors.foreground,
          }]} />
        </View>
      </View>

      <View style={[s.stripDivider, { backgroundColor: themeColors.border }]} />

      {/* Strain */}
      <View style={s.stripCol}>
        <Text variant="label" color={themeColors.textMuted} style={s.stripLabel}>STRAIN</Text>
        <Text variant="body" color={sColor} style={s.stripValue}>
          {strain.displayValue}
        </Text>
        <Text variant="label" color={themeColors.textMuted} style={[s.stripSub, { lineHeight: 15 }]} numberOfLines={2}>
          Fatigue musculaire
        </Text>
      </View>

      <View style={[s.stripDivider, { backgroundColor: themeColors.border }]} />

      {/* Sommeil */}
      <View style={s.stripCol}>
        <Text variant="label" color={themeColors.textMuted} style={s.stripLabel}>SOMMEIL</Text>
        <Text variant="body" color={themeColors.foreground} style={s.stripValue}>
          {sleep.duration}
        </Text>
        <View style={s.stripValueRow}>
          <Text variant="label" color={themeColors.textMuted} style={s.stripSub}>Score </Text>
          <Text variant="label" color={slColor} style={[s.stripSub, s.tabular]}>
            {sleep.score}
          </Text>
        </View>
      </View>
    </View>
  );
}

// ─── HomeSessionCard ──────────────────────────────────────────────────────────

interface HomeSessionCardProps {
  session: HomeDashSession;
  colorMode: ColorMode;
  onStart: () => void;
}

function HomeSessionCard({ session, colorMode, onStart }: HomeSessionCardProps): React.JSX.Element {
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const accentColor = colorMode === 'dark' ? colors.accentDark : colors.accent;
  const accentTextColor = colorMode === 'dark' ? colors.accentTextDark : colors.accentText;
  const isRecovery = session.type === 'recovery';

  return (
    <View>
      {/* Card body */}
      <View style={[s.sessionBody, { paddingHorizontal: 18, paddingTop: 18 }]}>
        {/* Header: label + time */}
        <View style={s.sessionHeader}>
          <Text variant="label" color={themeColors.textMuted} style={s.sessionCardLabel}>
            {session.cardLabel}
          </Text>
          <Text variant="label" color={themeColors.textMuted} style={[s.tabular, { fontSize: 11 }]}>
            {session.time}
          </Text>
        </View>

        {/* Discipline + duration */}
        <View style={s.sessionTitleRow}>
          <Text
            variant="body"
            color={themeColors.foreground}
            style={s.sessionDiscipline}
            numberOfLines={1}
          >
            {session.discipline}
          </Text>
          <Text variant="body" color={themeColors.textMuted} style={[s.sessionDuration, s.tabular]}>
            {session.duration}
          </Text>
        </View>

        {/* Brief */}
        <Text
          variant="body"
          color={themeColors.textMuted}
          style={s.sessionBrief}
          numberOfLines={2}
        >
          {session.brief}
        </Text>

        {/* Targets row (non-recovery only) */}
        {!isRecovery && session.targets.length > 0 && (
          <View style={[s.targetsRow, { borderTopColor: themeColors.border }]}>
            {session.targets.map((t, i) => (
              <View key={i} style={s.targetCol}>
                <Text variant="label" color={themeColors.textMuted} style={s.targetLabel}>
                  {t.label.toUpperCase()}
                </Text>
                <Text variant="body" color={themeColors.foreground} style={[s.targetValue, s.tabular]}>
                  {t.value}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Full-width CTA footer */}
      <TouchableOpacity
        onPress={onStart}
        activeOpacity={0.82}
        style={[
          s.sessionCTA,
          {
            backgroundColor: isRecovery ? themeColors.surface2 : accentColor,
            borderTopColor: isRecovery ? themeColors.border : 'transparent',
          },
        ]}
      >
        <Text
          variant="body"
          color={isRecovery ? themeColors.foreground : accentTextColor}
          style={s.sessionCTAText}
        >
          {isRecovery ? 'Voir le protocole' : 'Démarrer la séance'}
        </Text>
        <Svg width={14} height={14} viewBox="0 0 14 14">
          <SvgCircle r={0} cx={0} cy={0} fill="none" />
        </Svg>
        {/* Arrow → inline SVG path via Text as workaround */}
        <Text
          variant="body"
          color={isRecovery ? themeColors.foreground : accentTextColor}
          style={s.sessionCTAArrow}
        >
          →
        </Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── CognitiveLoadBar ─────────────────────────────────────────────────────────

interface CognitiveLoadBarProps {
  value: number;
  label: string;
  context: string;
  colorMode: ColorMode;
}

function CognitiveLoadBar({ value, label, context, colorMode }: CognitiveLoadBarProps): React.JSX.Element {
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const segCount = 24;
  const filled = Math.round((Math.min(100, Math.max(0, value)) / 100) * segCount);
  const barColor = cognitiveColor(value, colorMode);

  return (
    <View>
      <Text variant="label" color={themeColors.foreground} style={s.cogSub}>
        Charge allostatique
      </Text>

      {/* Segmented bar */}
      <View style={s.cogBar}>
        {Array.from({ length: segCount }).map((_, i) => (
          <View
            key={i}
            style={[
              s.cogSegment,
              {
                backgroundColor: i < filled ? barColor : themeColors.track,
                opacity: i < filled ? 0.35 + (i / segCount) * 0.65 : 1,
              },
            ]}
          />
        ))}
      </View>

      {/* Footer */}
      <View style={s.cogFooter}>
        <Text variant="body" color={themeColors.foreground} style={[s.cogLabel, s.tabular]}>
          {label}
        </Text>
        <Text variant="label" color={themeColors.textMuted} style={[s.tabular, { fontSize: 13 }]}>
          {context}
        </Text>
      </View>
    </View>
  );
}

// ─── HomeScreen ───────────────────────────────────────────────────────────────

export default function HomeScreen(): React.JSX.Element {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const accentColor = colorMode === 'dark' ? colors.accentDark : colors.accent;

  const [dashState, setDashState] = useState<DashState>('normal');
  const [refreshing, setRefreshing] = useState(false);

  const data = DASH_MOCK[dashState];

  const handleAvatarTap = useCallback(() => {
    setDashState(prev => nextDashState(prev));
  }, []);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await new Promise<void>(r => setTimeout(r, 400));
    setRefreshing(false);
  }, []);

  const handleStart = useCallback(async () => {
    if (data.session.type === 'recovery') {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      // TODO: router.push('/protocol/recovery') — passe future
    } else {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      // TODO: router.push('/session/live') — passe future
    }
  }, [data.session.type]);

  return (
    <Screen>
      <ScrollView
        style={s.flex}
        contentContainerStyle={s.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={themeColors.textMuted}
          />
        }
      >
        {/* ── Header ── */}
        <View style={s.header}>
          <View>
            <Text
              variant="body"
              color={themeColors.foreground}
              style={s.greeting}
            >
              Bonjour {data.firstName}
            </Text>
            <Text
              variant="label"
              color={themeColors.textMuted}
              style={[s.dateLabel, s.tabular]}
            >
              {data.dateLabel}
            </Text>
          </View>
          {/* Avatar — tap to cycle DEV states */}
          <TouchableOpacity
            onPress={handleAvatarTap}
            activeOpacity={0.7}
            style={[s.avatar, { backgroundColor: themeColors.surface2, borderColor: themeColors.border }]}
            accessibilityLabel="Changer l'état de démonstration"
          >
            <Text variant="label" color={themeColors.foreground} style={s.avatarText}>
              SR
            </Text>
          </TouchableOpacity>
        </View>

        {/* ── Readiness ring ── */}
        <View style={s.ringSection}>
          <ReadinessRingHome
            value={data.readiness.value}
            delta={data.readiness.delta}
            colorMode={colorMode}
          />
        </View>

        {/* ── Metrics strip ── */}
        <View style={s.cardRow}>
          <Card style={s.stripCard}>
            <MetricsStrip
              nutrition={data.nutrition}
              strain={data.strain}
              sleep={data.sleep}
              colorMode={colorMode}
            />
          </Card>
        </View>

        {/* ── Session / Recovery card ── */}
        <View style={s.cardRow}>
          <Card style={s.sessionCard}>
            <HomeSessionCard
              session={data.session}
              colorMode={colorMode}
              onStart={handleStart}
            />
          </Card>
        </View>

        {/* ── Cognitive load bar ── */}
        <View style={s.cardRow}>
          <Card style={s.cogCard}>
            <CognitiveLoadBar
              value={data.cognitiveLoad.value}
              label={data.cognitiveLoad.label}
              context={data.cognitiveLoad.context}
              colorMode={colorMode}
            />
          </Card>
        </View>
      </ScrollView>
    </Screen>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  flex: { flex: 1 },
  content: { paddingBottom: 32 },

  // Header
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 24,
  },
  greeting: {
    fontSize: 22,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -0.6,
    lineHeight: 27,
  },
  dateLabel: {
    fontSize: 11,
    fontFamily: 'SpaceGrotesk_600SemiBold',
    textTransform: 'uppercase',
    letterSpacing: 1.5,
    marginTop: 4,
  },
  avatar: {
    width: 36, height: 36, borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center', justifyContent: 'center',
  },
  avatarText: {
    fontSize: 13,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: 0.4,
  },

  // Ring
  ringSection: {
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 28,
  },
  ringContainer: { alignItems: 'center' },
  ringCenter: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  ringValue: {
    fontSize: 52,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -2.5,
    lineHeight: 58,
    fontVariant: ['tabular-nums'],
  },
  ringLabel: {
    fontSize: 11,
    fontFamily: 'SpaceGrotesk_500Medium',
    textTransform: 'uppercase',
    letterSpacing: 1.8,
    marginTop: 6,
  },
  ringDelta: {
    fontSize: 12,
    fontFamily: 'SpaceGrotesk_500Medium',
    marginTop: 4,
    fontVariant: ['tabular-nums'],
  },

  // Layout
  cardRow: { paddingHorizontal: 20, marginBottom: 16 },

  // Metrics strip
  stripCard: { padding: 0, overflow: 'hidden' },
  stripRow: { flexDirection: 'row', alignItems: 'stretch' },
  stripCol: { flex: 1, padding: 16, paddingHorizontal: 14 },
  stripDivider: { width: StyleSheet.hairlineWidth, marginVertical: 14 },
  stripLabel: {
    fontSize: 10,
    fontFamily: 'SpaceGrotesk_600SemiBold',
    textTransform: 'uppercase',
    letterSpacing: 1.4,
    marginBottom: 6,
  },
  stripValue: {
    fontSize: 17,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -0.4,
    fontVariant: ['tabular-nums'],
  },
  stripValueRow: { flexDirection: 'row', flexWrap: 'wrap' },
  stripSub: {
    fontSize: 11,
    marginTop: 2,
  },
  progressTrack: {
    height: 3, borderRadius: 2,
    overflow: 'hidden', marginTop: 6,
  },
  progressFill: {
    height: '100%', opacity: 0.85,
  },

  // Session card
  sessionCard: { padding: 0, overflow: 'hidden' },
  sessionBody: { paddingBottom: 0 },
  sessionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 14,
  },
  sessionCardLabel: {
    fontSize: 10,
    fontFamily: 'SpaceGrotesk_600SemiBold',
    textTransform: 'uppercase',
    letterSpacing: 1.4,
  },
  sessionTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  sessionDiscipline: {
    fontSize: 22,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -0.5,
    lineHeight: 30,
    flex: 1,
  },
  sessionDuration: {
    fontSize: 15,
    fontFamily: 'SpaceGrotesk_500Medium',
  },
  sessionBrief: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  targetsRow: {
    flexDirection: 'row',
    gap: 12,
    paddingTop: 12,
    paddingBottom: 16,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  targetCol: { flex: 1 },
  targetLabel: {
    fontSize: 10,
    fontFamily: 'SpaceGrotesk_500Medium',
    textTransform: 'uppercase',
    letterSpacing: 1.2,
    marginBottom: 3,
  },
  targetValue: {
    fontSize: 14,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -0.2,
  },
  sessionCTA: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 16,
    paddingHorizontal: 18,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomLeftRadius: 13,
    borderBottomRightRadius: 13,
  },
  sessionCTAText: {
    fontSize: 15,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -0.2,
  },
  sessionCTAArrow: {
    fontSize: 16,
    fontFamily: 'SpaceGrotesk_500Medium',
  },

  // Cognitive load bar
  cogCard: { padding: 18 },
  cogSub: {
    fontSize: 13,
    marginBottom: 14,
  },
  cogBar: {
    flexDirection: 'row',
    gap: 2,
    height: 28,
    alignItems: 'stretch',
    marginBottom: 12,
  },
  cogSegment: {
    flex: 1,
    borderRadius: 1,
  },
  cogFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  cogLabel: {
    fontSize: 18,
    fontFamily: 'SpaceGrotesk_500Medium',
    letterSpacing: -0.4,
  },

  // Utility
  tabular: { fontVariant: ['tabular-nums'] },
});
