/**
 * Training History — P4
 * Calendar view (month grid + discipline dots) + List view (week groups).
 * Day detail via bottom sheet Modal (no reanimated).
 * Design: docs/design/training historycalendar/
 */
import React, { useMemo, useState } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import Svg, { Circle as SvgCircle, Path } from 'react-native-svg';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors } from '@resilio/design-tokens';
import { IconComponent, SegmentedControl, Text, useTheme } from '@resilio/ui-mobile';
import type { IconName } from '@resilio/ui-mobile';

// ── Types ─────────────────────────────────────────────────────────────────────

type SportType = 'run' | 'lift' | 'bike' | 'swim';

interface TrainingSession {
  id: number;
  dateKey: string;
  type: SportType;
  name: string;
  dur: number;
  load: number;
  rpe: number;
  dist?: number;
}

type ByDate = Record<string, TrainingSession[]>;

// ── Utils ─────────────────────────────────────────────────────────────────────

function fmt(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function fmtDur(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h > 0 ? `${h}h${String(m).padStart(2, '0')}` : `${min} min`;
}

const SPORT_LABEL: Record<SportType, string> = {
  run: 'Course', lift: 'Muscu', bike: 'Vélo', swim: 'Natation',
};

const SPORT_ICON: Record<SportType, IconName> = {
  run: 'Activity', lift: 'Lifting', bike: 'Biking', swim: 'Swimming',
};

// ── Mock data ─────────────────────────────────────────────────────────────────

function buildData(): ByDate {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  let id = 1;

  type Raw = Omit<TrainingSession, 'id' | 'dateKey'>;
  const plan: Array<{ da: number; s: Raw[] }> = [
    { da: 0,  s: [{ type: 'run',  name: 'Sortie longue Z2',            dur: 95,  load: 88,  rpe: 5, dist: 18.2 }] },
    { da: 1,  s: [{ type: 'lift', name: 'Full body — Force',            dur: 62,  load: 55,  rpe: 7 }] },
    { da: 2,  s: [
      { type: 'swim', name: 'Technique + 8x100',                        dur: 45,  load: 28,  rpe: 4, dist: 2.1 },
      { type: 'bike', name: 'Home trainer Z2',                          dur: 60,  load: 52,  rpe: 5, dist: 28.4 },
    ]},
    { da: 3,  s: [{ type: 'run',  name: 'Seuil 3x8 min',               dur: 58,  load: 74,  rpe: 8, dist: 11.6 }] },
    { da: 5,  s: [{ type: 'lift', name: 'Lower — Hypertrophie',         dur: 70,  load: 62,  rpe: 7 }] },
    { da: 6,  s: [{ type: 'run',  name: 'Footing récup',                dur: 35,  load: 22,  rpe: 3, dist: 6.4 }] },
    { da: 7,  s: [{ type: 'run',  name: 'Sortie longue + côtes',        dur: 105, load: 96,  rpe: 6, dist: 19.5 }] },
    { da: 8,  s: [{ type: 'bike', name: 'Sweet spot 3x12',              dur: 75,  load: 89,  rpe: 7, dist: 34.1 }] },
    { da: 9,  s: [{ type: 'lift', name: 'Upper — Force',                dur: 58,  load: 52,  rpe: 7 }] },
    { da: 11, s: [{ type: 'swim', name: 'Endurance 2500m',              dur: 50,  load: 34,  rpe: 5, dist: 2.5 }] },
    { da: 12, s: [{ type: 'run',  name: 'VMA 8x400',                    dur: 48,  load: 68,  rpe: 9, dist: 9.2 }] },
    { da: 13, s: [{ type: 'lift', name: 'Full body — Volume',           dur: 65,  load: 58,  rpe: 6 }] },
    { da: 14, s: [{ type: 'run',  name: 'Sortie longue Z2',             dur: 88,  load: 80,  rpe: 5, dist: 16.8 }] },
    { da: 15, s: [
      { type: 'swim', name: 'Pull + kick',                               dur: 42,  load: 26,  rpe: 4, dist: 2.0 },
      { type: 'lift', name: 'Lower — Force',                            dur: 55,  load: 48,  rpe: 7 },
    ]},
    { da: 17, s: [{ type: 'bike', name: 'Z2 long',                      dur: 95,  load: 78,  rpe: 5, dist: 42.3 }] },
    { da: 18, s: [{ type: 'run',  name: 'Tempo 30 min',                 dur: 52,  load: 64,  rpe: 7, dist: 10.2 }] },
    { da: 19, s: [{ type: 'lift', name: 'Upper — Volume',               dur: 62,  load: 54,  rpe: 6 }] },
    { da: 21, s: [{ type: 'run',  name: 'Sortie longue progressive',     dur: 92,  load: 86,  rpe: 6, dist: 17.4 }] },
    { da: 22, s: [{ type: 'lift', name: 'Full body — Force',            dur: 60,  load: 54,  rpe: 7 }] },
    { da: 23, s: [{ type: 'swim', name: 'Seuil 6x200',                  dur: 48,  load: 38,  rpe: 7, dist: 2.2 }] },
    { da: 24, s: [{ type: 'bike', name: 'Intervalles 5x5',              dur: 70,  load: 92,  rpe: 8, dist: 31.8 }] },
    { da: 26, s: [{ type: 'run',  name: 'VMA courte 12x200',            dur: 45,  load: 62,  rpe: 9, dist: 8.4 }] },
    { da: 27, s: [{ type: 'lift', name: 'Lower — Hypertrophie',         dur: 72,  load: 64,  rpe: 7 }] },
    { da: 28, s: [{ type: 'run',  name: 'Sortie longue Z2',             dur: 85,  load: 76,  rpe: 5, dist: 16.2 }] },
    { da: 29, s: [{ type: 'bike', name: 'Sweet spot 2x20',              dur: 80,  load: 95,  rpe: 7, dist: 36.4 }] },
    { da: 31, s: [
      { type: 'swim', name: 'Technique',                                 dur: 40,  load: 24,  rpe: 3, dist: 1.8 },
      { type: 'lift', name: 'Upper — Force',                            dur: 55,  load: 50,  rpe: 7 },
    ]},
    { da: 32, s: [{ type: 'run',  name: 'Seuil 20 min continu',         dur: 50,  load: 70,  rpe: 8, dist: 9.8 }] },
    { da: 33, s: [{ type: 'lift', name: 'Lower — Force',                dur: 58,  load: 52,  rpe: 7 }] },
    { da: 34, s: [{ type: 'run',  name: 'Footing récup',                dur: 32,  load: 20,  rpe: 3, dist: 5.8 }] },
    { da: 35, s: [{ type: 'run',  name: 'Sortie longue 20k',            dur: 110, load: 102, rpe: 6, dist: 20.1 }] },
    { da: 36, s: [{ type: 'lift', name: 'Full body — Force',            dur: 62,  load: 56,  rpe: 7 }] },
    { da: 37, s: [{ type: 'swim', name: 'Endurance 3000m',              dur: 55,  load: 38,  rpe: 5, dist: 3.0 }] },
    { da: 38, s: [{ type: 'bike', name: 'Z2 vallonné',                  dur: 90,  load: 82,  rpe: 6, dist: 38.2 }] },
    { da: 41, s: [{ type: 'run',  name: 'VMA 10x300',                   dur: 50,  load: 66,  rpe: 9, dist: 9.0 }] },
    { da: 42, s: [{ type: 'lift', name: 'Upper — Volume',               dur: 65,  load: 58,  rpe: 6 }] },
    { da: 43, s: [{ type: 'run',  name: 'Sortie longue Z2',             dur: 90,  load: 82,  rpe: 5, dist: 17.0 }] },
    { da: 44, s: [{ type: 'bike', name: 'Intervalles courts',           dur: 65,  load: 86,  rpe: 8, dist: 29.8 }] },
    { da: 46, s: [{ type: 'swim', name: 'Seuil 8x150',                  dur: 45,  load: 34,  rpe: 7, dist: 2.0 }] },
    { da: 47, s: [
      { type: 'run',  name: 'Tempo progressif',                          dur: 55,  load: 68,  rpe: 7, dist: 10.8 },
      { type: 'lift', name: 'Lower — Volume',                           dur: 60,  load: 52,  rpe: 6 },
    ]},
    { da: 49, s: [{ type: 'run',  name: 'Sortie longue Z2',             dur: 82,  load: 74,  rpe: 5, dist: 15.6 }] },
    { da: 50, s: [{ type: 'lift', name: 'Full body — Force',            dur: 58,  load: 52,  rpe: 7 }] },
    { da: 51, s: [{ type: 'bike', name: 'Sweet spot 4x8',               dur: 72,  load: 88,  rpe: 7, dist: 32.6 }] },
    { da: 53, s: [{ type: 'swim', name: 'Technique + 6x100',            dur: 42,  load: 28,  rpe: 4, dist: 1.9 }] },
    { da: 54, s: [{ type: 'run',  name: 'VMA 6x600',                    dur: 55,  load: 72,  rpe: 9, dist: 10.4 }] },
    { da: 55, s: [{ type: 'lift', name: 'Upper — Force',                dur: 56,  load: 50,  rpe: 7 }] },
    { da: 56, s: [{ type: 'run',  name: 'Sortie longue 18k',            dur: 96,  load: 88,  rpe: 6, dist: 18.0 }] },
    { da: 57, s: [{ type: 'bike', name: 'Z2 long',                      dur: 100, load: 82,  rpe: 5, dist: 44.1 }] },
    { da: 59, s: [{ type: 'lift', name: 'Lower — Hypertrophie',         dur: 68,  load: 62,  rpe: 7 }] },
    { da: 60, s: [{ type: 'swim', name: 'Endurance 2800m',              dur: 52,  load: 36,  rpe: 5, dist: 2.8 }] },
    { da: 61, s: [{ type: 'run',  name: 'Seuil 2x15 min',               dur: 54,  load: 72,  rpe: 8, dist: 10.6 }] },
    { da: 62, s: [{ type: 'lift', name: 'Full body — Volume',           dur: 60,  load: 54,  rpe: 6 }] },
    { da: 63, s: [{ type: 'run',  name: 'Sortie longue Z2',             dur: 86,  load: 78,  rpe: 5, dist: 16.4 }] },
    { da: 64, s: [{ type: 'lift', name: 'Upper — Force',                dur: 58,  load: 52,  rpe: 7 }] },
    { da: 66, s: [{ type: 'bike', name: 'Sweet spot 3x10',              dur: 70,  load: 86,  rpe: 7, dist: 31.4 }] },
    { da: 68, s: [{ type: 'run',  name: 'VMA 8x400',                    dur: 48,  load: 68,  rpe: 9, dist: 9.2 }] },
  ];

  const byDate: ByDate = {};
  plan.forEach(({ da, s }) => {
    const d = new Date(today);
    d.setDate(d.getDate() - da);
    const key = fmt(d);
    byDate[key] = s.map(sess => ({ ...sess, id: id++, dateKey: key }));
  });
  return byDate;
}

const MOCK_DATA: ByDate = buildData();
const TODAY = (() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; })();
const TODAY_KEY = fmt(TODAY);

// ── Week helpers ──────────────────────────────────────────────────────────────

function mondayOf(d: Date): Date {
  const m = new Date(d);
  m.setHours(0, 0, 0, 0);
  m.setDate(m.getDate() - ((m.getDay() + 6) % 7));
  return m;
}

interface WeekStats { sessions: number; volume: number; load: number; }

function weekStats(byDate: ByDate, monday: Date): WeekStats {
  let sessions = 0, volume = 0, load = 0;
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    (byDate[fmt(d)] ?? []).forEach(s => { sessions++; volume += s.dur; load += s.load; });
  }
  return { sessions, volume, load };
}

// ── DiscDot ───────────────────────────────────────────────────────────────────

function DiscDot({ type, fg, sec }: { type: SportType; fg: string; sec: string }) {
  const SIZE = 7;
  const R = SIZE / 2;
  if (type === 'run')  return <View style={[styles.dot, { backgroundColor: fg }]} />;
  if (type === 'lift') return <View style={[styles.dot, { backgroundColor: sec }]} />;
  if (type === 'bike') return <View style={[styles.dot, styles.dotOutline, { borderColor: fg }]} />;
  // swim: left half filled
  return (
    <Svg width={SIZE} height={SIZE}>
      <SvgCircle cx={R} cy={R} r={R - 0.75} fill="none" stroke={fg} strokeWidth={1} />
      <Path d={`M ${R} 0.75 A ${R - 0.75} ${R - 0.75} 0 0 1 ${R} ${SIZE - 0.75} Z`} fill={fg} />
    </Svg>
  );
}

// ── WeekStats bar ─────────────────────────────────────────────────────────────

function WeekStatsBar({ byDate, themeColors }: {
  byDate: ByDate;
  themeColors: ReturnType<typeof useTheme>['colors'];
}) {
  const thisMonday = mondayOf(TODAY);
  const prevMonday = new Date(thisMonday);
  prevMonday.setDate(prevMonday.getDate() - 7);

  const curr = weekStats(byDate, thisMonday);
  const prev = weekStats(byDate, prevMonday);

  function deltaSessions(a: number, b: number): string {
    const d = a - b;
    return d === 0 ? '—' : `${d > 0 ? '↑+' : '↓'}${Math.abs(d)} vs 7j préc.`;
  }
  function deltaDur(a: number, b: number): string {
    const d = a - b;
    return d === 0 ? '—' : `${d > 0 ? '↑+' : '↓'}${fmtDur(Math.abs(d))} vs 7j préc.`;
  }
  function deltaLoad(a: number, b: number): string {
    const d = a - b;
    return d === 0 ? '—' : `${d > 0 ? '↑+' : '↓'}${Math.abs(d)} vs 7j préc.`;
  }

  return (
    <View style={[styles.statsBar, { borderBottomColor: themeColors.border }]}>
      <View style={styles.statCol}>
        <Text variant="label" color={themeColors.textMuted} style={styles.statLabel}>SÉANCES</Text>
        <Text variant="headline" color={themeColors.foreground} style={styles.statValue}>{curr.sessions}</Text>
        <Text variant="caption" color={themeColors.textMuted}>{deltaSessions(curr.sessions, prev.sessions)}</Text>
      </View>
      <View style={[styles.statCol, styles.statColBorder, { borderLeftColor: themeColors.border }]}>
        <Text variant="label" color={themeColors.textMuted} style={styles.statLabel}>VOLUME</Text>
        <Text variant="headline" color={themeColors.foreground} style={styles.statValue}>{fmtDur(curr.volume)}</Text>
        <Text variant="caption" color={themeColors.textMuted}>{deltaDur(curr.volume, prev.volume)}</Text>
      </View>
      <View style={[styles.statCol, styles.statColBorder, { borderLeftColor: themeColors.border }]}>
        <Text variant="label" color={themeColors.textMuted} style={styles.statLabel}>CHARGE</Text>
        <Text variant="headline" color={themeColors.foreground} style={styles.statValue}>{curr.load}</Text>
        <Text variant="caption" color={themeColors.textMuted}>{deltaLoad(curr.load, prev.load)}</Text>
      </View>
    </View>
  );
}

// ── Calendar ──────────────────────────────────────────────────────────────────

const WEEKDAYS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];

interface DayCellProps {
  dayNum: number;
  dateKey: string;
  sessions: TrainingSession[];
  isToday: boolean;
  isFuture: boolean;
  isSelected: boolean;
  onPress: () => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}

function DayCell({ dayNum, sessions, isToday, isFuture, isSelected, onPress, themeColors, accent }: DayCellProps) {
  const types = [...new Set(sessions.map(s => s.type))].slice(0, 3) as SportType[];

  const bg = isSelected
    ? `${accent}25`
    : sessions.length > 0 && !isFuture
      ? themeColors.surface2
      : 'transparent';

  return (
    <Pressable
      onPress={onPress}
      disabled={isFuture}
      style={[
        styles.dayCell,
        { backgroundColor: bg, borderColor: isToday || isSelected ? accent : 'transparent', opacity: isFuture ? 0.3 : 1 },
      ]}
    >
      <Text
        variant="label"
        color={isToday ? accent : themeColors.foreground}
        style={[styles.dayCellNum, isToday && styles.dayCellNumBold]}
      >
        {dayNum}
      </Text>
      <View style={styles.dotRow}>
        {types.map(t => (
          <DiscDot key={t} type={t} fg={themeColors.foreground} sec={themeColors.textSecondary} />
        ))}
      </View>
    </Pressable>
  );
}

interface CalendarGridProps {
  byDate: ByDate;
  monthOffset: number;
  onMonthChange: (delta: number) => void;
  selectedDay: string | null;
  onSelectDay: (key: string) => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}

function CalendarGrid({ byDate, monthOffset, onMonthChange, selectedDay, onSelectDay, themeColors, accent }: CalendarGridProps) {
  const viewDate = new Date(TODAY.getFullYear(), TODAY.getMonth() + monthOffset, 1);
  const monthLabel = viewDate.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  const firstDow = (viewDate.getDay() + 6) % 7;
  const daysInMonth = new Date(TODAY.getFullYear(), TODAY.getMonth() + monthOffset + 1, 0).getDate();

  type Cell =
    | { blank: true; key: string }
    | { blank: false; key: string; dayNum: number; dateKey: string; isToday: boolean; isFuture: boolean };

  const cells: Cell[] = [];
  for (let i = 0; i < firstDow; i++) cells.push({ blank: true, key: `b${i}` });
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(TODAY.getFullYear(), TODAY.getMonth() + monthOffset, d);
    const dateKey = fmt(date);
    cells.push({ blank: false, key: dateKey, dayNum: d, dateKey, isToday: dateKey === TODAY_KEY, isFuture: date > TODAY });
  }
  while (cells.length % 7 !== 0) cells.push({ blank: true, key: `be${cells.length}` });

  const rows: Cell[][] = [];
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));

  return (
    <View style={styles.calendarWrap}>
      {/* Month header */}
      <View style={styles.monthHeader}>
        <Text variant="body" color={themeColors.foreground} style={styles.monthLabel}>
          {monthLabel.charAt(0).toUpperCase() + monthLabel.slice(1)}
        </Text>
        <View style={styles.monthNav}>
          <Pressable onPress={() => onMonthChange(-1)} hitSlop={8} style={styles.navBtn}>
            <IconComponent name="ChevronLeft" size={16} color={themeColors.textSecondary} />
          </Pressable>
          <Pressable onPress={() => onMonthChange(1)} hitSlop={8} style={styles.navBtn}>
            <IconComponent name="ChevronRight" size={16} color={themeColors.textSecondary} />
          </Pressable>
        </View>
      </View>

      {/* Weekday row */}
      <View style={styles.weekdayRow}>
        {WEEKDAYS.map((w, i) => (
          <Text key={i} variant="label" color={themeColors.textMuted} style={styles.weekdayLabel}>{w}</Text>
        ))}
      </View>

      {/* Grid */}
      <View style={styles.calGrid}>
        {rows.map((row, ri) => (
          <View key={ri} style={styles.calRow}>
            {row.map(cell =>
              cell.blank ? (
                <View key={cell.key} style={styles.dayCellBlank} />
              ) : (
                <DayCell
                  key={cell.key}
                  dayNum={cell.dayNum}
                  dateKey={cell.dateKey}
                  sessions={byDate[cell.dateKey] ?? []}
                  isToday={cell.isToday}
                  isFuture={cell.isFuture}
                  isSelected={selectedDay === cell.dateKey}
                  onPress={() => onSelectDay(cell.dateKey)}
                  themeColors={themeColors}
                  accent={accent}
                />
              )
            )}
          </View>
        ))}
      </View>
    </View>
  );
}

// ── List view ─────────────────────────────────────────────────────────────────

function SessionListRow({ session, showDate, isToday, themeColors, accent }: {
  session: TrainingSession;
  showDate: boolean;
  isToday: boolean;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  const [y, m, d] = session.dateKey.split('-').map(Number) as [number, number, number];
  const date = new Date(y, m - 1, d);
  const weekday = date.toLocaleDateString('fr-FR', { weekday: 'short' }).replace('.', '').toUpperCase();

  return (
    <View style={[styles.sessionRow, { borderBottomColor: themeColors.border }]}>
      <View style={styles.dateCol}>
        {showDate && (
          <>
            <Text variant="label" color={isToday ? accent : themeColors.textSecondary} style={styles.weekdaySmall}>{weekday}</Text>
            <Text variant="body" color={isToday ? accent : themeColors.foreground} style={styles.dayNumText}>{d}</Text>
          </>
        )}
      </View>
      <View style={[styles.sportIconBg, { backgroundColor: themeColors.surface2 }]}>
        <IconComponent name={SPORT_ICON[session.type]} size={16} color={themeColors.textSecondary} />
      </View>
      <View style={styles.sessionContent}>
        <Text variant="bodyBold" color={themeColors.foreground} numberOfLines={1} style={styles.sessionName}>
          {session.name}
        </Text>
        <Text variant="label" color={themeColors.textMuted} numberOfLines={1} style={styles.sessionMeta}>
          {SPORT_LABEL[session.type].toUpperCase()}{session.dist ? ` · ${session.dist} KM` : ''}
        </Text>
      </View>
      <View style={styles.sessionRight}>
        <Text variant="body" color={themeColors.foreground} style={styles.sessionDur}>{fmtDur(session.dur)}</Text>
        <Text variant="label" color={themeColors.textMuted} style={styles.sessionLoad}>{session.load} charge</Text>
      </View>
    </View>
  );
}

function DayListRow({ dateKey, sessions, isToday, themeColors, accent }: {
  dateKey: string;
  sessions: TrainingSession[];
  isToday: boolean;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  const [y, m, d] = dateKey.split('-').map(Number) as [number, number, number];
  const date = new Date(y, m - 1, d);
  const weekday = date.toLocaleDateString('fr-FR', { weekday: 'short' }).replace('.', '').toUpperCase();

  if (sessions.length === 0) {
    return (
      <View style={[styles.restRow, { borderBottomColor: themeColors.border }]}>
        <View style={styles.dateCol}>
          <Text variant="label" color={isToday ? accent : themeColors.textMuted} style={styles.weekdaySmall}>{weekday}</Text>
          <Text variant="body" color={isToday ? accent : themeColors.textMuted} style={styles.dayNumText}>{d}</Text>
        </View>
        <View style={styles.restDashWrap}>
          <View style={[styles.restDash, { backgroundColor: themeColors.border }]} />
        </View>
        <Text variant="secondary" color={themeColors.textMuted}>Récupération</Text>
      </View>
    );
  }

  return (
    <>
      {sessions.map((s, idx) => (
        <SessionListRow
          key={s.id}
          session={s}
          showDate={idx === 0}
          isToday={isToday}
          themeColors={themeColors}
          accent={accent}
        />
      ))}
    </>
  );
}

function WeekBlock({ monday, byDate, isFirst, themeColors, accent }: {
  monday: Date;
  byDate: ByDate;
  isFirst: boolean;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  let totalSessions = 0, totalVol = 0, totalLoad = 0;
  const days: Array<{ dateKey: string; sessions: TrainingSession[]; isToday: boolean }> = [];

  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    if (d > TODAY) continue;
    const key = fmt(d);
    const sList = byDate[key] ?? [];
    totalSessions += sList.length;
    sList.forEach(s => { totalVol += s.dur; totalLoad += s.load; });
    days.push({ dateKey: key, sessions: sList, isToday: key === TODAY_KEY });
  }

  if (days.length === 0) return null;

  const weekLabel = `SEM. DU ${monday.getDate()} ${monday.toLocaleDateString('fr-FR', { month: 'short' }).replace('.', '').toUpperCase()}`;
  const summary = `${totalSessions} séance${totalSessions !== 1 ? 's' : ''} · ${fmtDur(totalVol)} · ${totalLoad} charge`;

  return (
    <View>
      <View style={[styles.weekHeader, isFirst && styles.weekHeaderFirst, { borderBottomColor: themeColors.border }]}>
        <Text variant="label" color={themeColors.textMuted}>{weekLabel}</Text>
        <Text variant="label" color={themeColors.textMuted}>{summary}</Text>
      </View>
      {days.map(({ dateKey, sessions, isToday }) => (
        <DayListRow key={dateKey} dateKey={dateKey} sessions={sessions} isToday={isToday} themeColors={themeColors} accent={accent} />
      ))}
    </View>
  );
}

function ListView({ byDate, themeColors, accent }: {
  byDate: ByDate;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  const weeks = useMemo(() => {
    const result: Date[] = [];
    const m = mondayOf(TODAY);
    for (let i = 0; i < 10; i++) {
      result.push(new Date(m));
      m.setDate(m.getDate() - 7);
    }
    return result;
  }, []);

  return (
    <ScrollView style={styles.flex} showsVerticalScrollIndicator={false} contentContainerStyle={styles.listContent}>
      {weeks.map((monday, i) => (
        <WeekBlock key={fmt(monday)} monday={monday} byDate={byDate} isFirst={i === 0} themeColors={themeColors} accent={accent} />
      ))}
      <View style={styles.listPad} />
    </ScrollView>
  );
}

// ── Day detail drawer ─────────────────────────────────────────────────────────

function DayDetailDrawer({ dayKey, byDate, onClose, themeColors, accent }: {
  dayKey: string;
  byDate: ByDate;
  onClose: () => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  const insets = useSafeAreaInsets();
  const sessions = byDate[dayKey] ?? [];
  const [y, m, d] = dayKey.split('-').map(Number) as [number, number, number];
  const date = new Date(y, m - 1, d);
  const isToday = dayKey === TODAY_KEY;
  const dayLabel = date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

  let totalVol = 0, totalLoad = 0;
  sessions.forEach(s => { totalVol += s.dur; totalLoad += s.load; });

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose} statusBarTranslucent>
      <View style={styles.drawerOverlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={[styles.drawerSheet, { backgroundColor: themeColors.surface1, paddingBottom: insets.bottom + 20 }]}>
          <View style={[styles.handle, { backgroundColor: themeColors.border }]} />

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Title */}
            <View style={styles.drawerTitleWrap}>
              <Text variant="label" color={isToday ? accent : themeColors.textMuted}>
                {isToday ? "AUJOURD'HUI" : 'JOUR'}
              </Text>
              <Text variant="pageTitle" color={themeColors.foreground} style={styles.drawerDayLabel}>
                {dayLabel.charAt(0).toUpperCase() + dayLabel.slice(1)}
              </Text>
            </View>

            {/* Totals */}
            {sessions.length > 0 && (
              <View style={[styles.drawerStats, { borderTopColor: themeColors.border, borderBottomColor: themeColors.border }]}>
                {[
                  { label: 'SÉANCES', value: String(sessions.length) },
                  { label: 'VOLUME',  value: fmtDur(totalVol) },
                  { label: 'CHARGE',  value: String(totalLoad) },
                ].map(({ label, value }, i) => (
                  <React.Fragment key={label}>
                    {i > 0 && <View style={[styles.drawerStatDiv, { backgroundColor: themeColors.border }]} />}
                    <View style={styles.drawerStatCol}>
                      <Text variant="label" color={themeColors.textMuted} style={styles.drawerStatLabel}>{label}</Text>
                      <Text variant="headline" color={themeColors.foreground}>{value}</Text>
                    </View>
                  </React.Fragment>
                ))}
              </View>
            )}

            {/* Sessions or empty */}
            {sessions.length === 0 ? (
              <Text variant="secondary" color={themeColors.textSecondary} style={styles.drawerRest}>
                Récupération. Pas de séance prévue.
              </Text>
            ) : sessions.map(s => (
              <View key={s.id} style={[styles.drawerSession, { borderBottomColor: themeColors.border }]}>
                <View style={styles.drawerSHeader}>
                  <View style={[styles.drawerSIcon, { backgroundColor: themeColors.surface2 }]}>
                    <IconComponent name={SPORT_ICON[s.type]} size={20} color={themeColors.textSecondary} />
                  </View>
                  <View style={styles.drawerSMeta}>
                    <Text variant="bodyBold" color={themeColors.foreground}>{s.name}</Text>
                    <Text variant="label" color={themeColors.textMuted} style={styles.drawerSType}>
                      {SPORT_LABEL[s.type].toUpperCase()}
                    </Text>
                  </View>
                </View>
                <View style={styles.metricsGrid}>
                  {[
                    { label: 'DURÉE',    value: fmtDur(s.dur) },
                    { label: 'CHARGE',   value: String(s.load) },
                    { label: 'RPE',      value: `${s.rpe}/10` },
                    { label: 'DISTANCE', value: s.dist ? `${s.dist} km` : '—' },
                  ].map(({ label, value }) => (
                    <View key={label} style={styles.metricCell}>
                      <Text variant="label" color={themeColors.textMuted} style={styles.metricCellLabel}>{label}</Text>
                      <Text variant="body" color={themeColors.foreground} style={styles.metricCellValue}>{value}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ))}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function TrainingScreen(): React.JSX.Element {
  const { colorMode, colors: themeColors } = useTheme();
  const insets = useSafeAreaInsets();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;

  const [modeIndex, setModeIndex] = useState(0); // 0=calendar 1=list
  const [monthOffset, setMonthOffset] = useState(0);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  return (
    <View style={[styles.flex, { backgroundColor: themeColors.background, paddingTop: insets.top }]}>
      {/* Page header */}
      <View style={[styles.pageHeader, { borderBottomColor: themeColors.border }]}>
        <Text variant="pageTitle" color={themeColors.foreground}>Entraînement</Text>
      </View>

      {/* Segmented toggle */}
      <View style={styles.segWrap}>
        <SegmentedControl options={['Calendrier', 'Liste']} selected={modeIndex} onChange={setModeIndex} />
      </View>

      {/* Weekly stats */}
      <WeekStatsBar byDate={MOCK_DATA} themeColors={themeColors} />

      {/* Content */}
      {modeIndex === 0 ? (
        <ScrollView style={styles.flex} showsVerticalScrollIndicator={false} contentContainerStyle={styles.calScroll}>
          <CalendarGrid
            byDate={MOCK_DATA}
            monthOffset={monthOffset}
            onMonthChange={(delta) => setMonthOffset(o => Math.min(0, o + delta))}
            selectedDay={selectedDay}
            onSelectDay={setSelectedDay}
            themeColors={themeColors}
            accent={accent}
          />
        </ScrollView>
      ) : (
        <ListView byDate={MOCK_DATA} themeColors={themeColors} accent={accent} />
      )}

      {/* Day detail drawer */}
      {selectedDay !== null && (
        <DayDetailDrawer
          dayKey={selectedDay}
          byDate={MOCK_DATA}
          onClose={() => setSelectedDay(null)}
          themeColors={themeColors}
          accent={accent}
        />
      )}
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },

  pageHeader: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },

  segWrap: { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 4 },

  statsBar: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  statCol: { flex: 1, gap: 2 },
  statColBorder: { borderLeftWidth: StyleSheet.hairlineWidth, paddingLeft: 14 },
  statLabel: { letterSpacing: 0.5, textTransform: 'uppercase' as const },
  statValue: { marginVertical: 1 },

  // Calendar
  calScroll: { paddingBottom: 40 },
  calendarWrap: { paddingHorizontal: 12, paddingTop: 16 },
  monthHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 8,
    marginBottom: 14,
  },
  monthLabel: { fontFamily: 'SpaceGrotesk_500Medium' as const, fontSize: 17, letterSpacing: -0.3 },
  monthNav: { flexDirection: 'row', gap: 4 },
  navBtn: { width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  weekdayRow: { flexDirection: 'row', paddingHorizontal: 2, marginBottom: 8 },
  weekdayLabel: { flex: 1, textAlign: 'center' as const, letterSpacing: 0.5 },
  calGrid: { gap: 4 },
  calRow: { flexDirection: 'row', gap: 4 },
  dayCell: {
    flex: 1,
    aspectRatio: 0.85,
    borderRadius: 8,
    borderWidth: 1.5,
    padding: 5,
    justifyContent: 'space-between',
  },
  dayCellBlank: { flex: 1, aspectRatio: 0.85 },
  dayCellNum: { fontSize: 12, letterSpacing: -0.2, lineHeight: 16 },
  dayCellNumBold: { fontFamily: 'SpaceGrotesk_600SemiBold' as const },
  dotRow: { flexDirection: 'row', gap: 3, alignItems: 'center', minHeight: 10 },
  dot: { width: 7, height: 7, borderRadius: 3.5 },
  dotOutline: { backgroundColor: 'transparent', borderWidth: 1.5 },

  // List view
  listContent: { paddingBottom: 4 },
  listPad: { height: 48 },
  weekHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  weekHeaderFirst: { paddingTop: 14 },
  sessionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: 12,
  },
  restRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: 0,
  },
  dateCol: { width: 44 },
  weekdaySmall: { fontSize: 10, letterSpacing: 0.4, lineHeight: 14 },
  dayNumText: { fontFamily: 'SpaceGrotesk_500Medium' as const, fontSize: 16, letterSpacing: -0.3, lineHeight: 20 },
  sportIconBg: { width: 32, height: 32, borderRadius: 8, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  sessionContent: { flex: 1, minWidth: 0, gap: 2 },
  sessionName: { fontSize: 14, letterSpacing: -0.2 },
  sessionMeta: { letterSpacing: 0.3 },
  sessionRight: { alignItems: 'flex-end', gap: 2, flexShrink: 0 },
  sessionDur: { fontFamily: 'SpaceGrotesk_500Medium' as const, fontSize: 14, letterSpacing: -0.3 },
  sessionLoad: { letterSpacing: 0.2 },
  restDashWrap: { width: 44, alignItems: 'center' },
  restDash: { width: 12, height: 1 },

  // Drawer
  drawerOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.35)',
  },
  drawerSheet: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
    paddingTop: 10,
    paddingHorizontal: 20,
  },
  handle: {
    width: 36, height: 4, borderRadius: 2,
    alignSelf: 'center', marginBottom: 16,
  },
  drawerTitleWrap: { marginBottom: 16, gap: 4 },
  drawerDayLabel: { fontSize: 22, letterSpacing: -0.5 },
  drawerStats: {
    flexDirection: 'row',
    paddingVertical: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderBottomWidth: StyleSheet.hairlineWidth,
    marginBottom: 16,
  },
  drawerStatCol: { flex: 1, alignItems: 'center', gap: 4 },
  drawerStatDiv: { width: StyleSheet.hairlineWidth, marginVertical: 4 },
  drawerStatLabel: { letterSpacing: 0.5, textTransform: 'uppercase' as const },
  drawerRest: { textAlign: 'center', paddingVertical: 32 },
  drawerSession: { paddingVertical: 14, borderBottomWidth: StyleSheet.hairlineWidth },
  drawerSHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 },
  drawerSIcon: { width: 36, height: 36, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  drawerSMeta: { flex: 1, gap: 2 },
  drawerSType: { letterSpacing: 0.3 },
  metricsGrid: { flexDirection: 'row' },
  metricCell: { width: '25%', gap: 3, paddingRight: 4 },
  metricCellLabel: { letterSpacing: 0.5, textTransform: 'uppercase' as const },
  metricCellValue: { fontFamily: 'SpaceGrotesk_500Medium' as const, fontSize: 14, letterSpacing: -0.2 },
});
