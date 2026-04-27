import React, { useRef, useState } from 'react';
import {
  Animated,
  Dimensions,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { colors } from '@resilio/design-tokens';
import {
  Button,
  FloatingLabelInput,
  IconComponent,
  ProgressSegments,
  SegmentedControl,
  Text,
  useTheme,
} from '@resilio/ui-mobile';

// ── Types ─────────────────────────────────────────────────────────────────────

type Sport = 'running' | 'lifting' | 'cycling' | 'swimming';
type Level = 'beginner' | 'intermediate' | 'advanced' | 'elite';

interface OnboardingData {
  // Step 1
  firstName: string;
  birthDate: string;
  genderIndex: number; // 0=Femme 1=Homme
  height: string;
  weight: string;
  // Step 2
  sports: Sport[];
  // Step 3
  levels: Partial<Record<Sport, number>>; // index into LEVELS
  // Step 4
  objective: number; // -1 = none
}

// ── Constants ─────────────────────────────────────────────────────────────────

const TOTAL_STEPS = 5;

const SPORTS: { key: Sport; label: string; sub: string; icon: 'Activity' | 'Lifting' | 'Biking' | 'Swimming' }[] = [
  { key: 'running',  label: 'Course',       sub: 'Running · Trail',               icon: 'Activity' },
  { key: 'lifting',  label: 'Musculation',  sub: 'Force · Hypertrophie',          icon: 'Lifting'  },
  { key: 'cycling',  label: 'Vélo',         sub: 'Route · Gravel · Home trainer', icon: 'Biking'   },
  { key: 'swimming', label: 'Natation',     sub: 'Piscine · Eau libre',           icon: 'Swimming' },
];

const LEVEL_LABELS = ['Débutant', 'Inter.', 'Avancé', 'Élite'];

const OBJECTIVES = [
  'Performance compétitive',
  'Hypertrophie et force',
  'Endurance et VO2max',
  'Santé et longévité',
  'Composition corporelle',
];

const STEP_META = [
  { label: 'PROFIL',      title: 'Quelques infos\nsur toi',         subtitle: 'Pour calibrer ta charge et ta nutrition.' },
  { label: 'SPORTS',      title: 'Tes disciplines',                  subtitle: 'Sélectionne au minimum une discipline.' },
  { label: 'NIVEAU',      title: 'Ton niveau',                       subtitle: 'Resilio adapte l\'intensité à ton niveau réel.' },
  { label: 'OBJECTIF',    title: 'Ton objectif',                     subtitle: 'Un seul objectif pour des recommandations précises.' },
  { label: 'CONNECTEURS', title: 'Connecte tes apps',                subtitle: 'Synchronise tes données pour un coaching basé sur le réel.' },
];

const INITIAL_DATA: OnboardingData = {
  firstName: '',
  birthDate: '',
  genderIndex: 0,
  height: '',
  weight: '',
  sports: [],
  levels: {},
  objective: -1,
};

// ── Step components ───────────────────────────────────────────────────────────

function Step1Profile({ data, onChange, themeColors, accent }: {
  data: OnboardingData;
  onChange: (d: Partial<OnboardingData>) => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  return (
    <ScrollView keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
      <View style={styles.stepContent}>
        <FloatingLabelInput
          label="Prénom"
          value={data.firstName}
          onChangeText={(v) => onChange({ firstName: v })}
          autoComplete="given-name"
          autoCapitalize="words"
          autoFocus
        />
        <View style={styles.fieldGap}>
          <FloatingLabelInput
            label="Date de naissance (JJ/MM/AAAA)"
            value={data.birthDate}
            onChangeText={(v) => onChange({ birthDate: v })}
            keyboardType="numbers-and-punctuation"
            autoComplete="off"
          />
        </View>

        <View style={styles.fieldGap}>
          <Text variant="label" color={themeColors.textMuted} style={styles.fieldLabel}>
            Genre biologique
          </Text>
          <View style={styles.segRow}>
            <SegmentedControl
              options={['Femme', 'Homme']}
              selected={data.genderIndex}
              onChange={(i) => onChange({ genderIndex: i })}
            />
          </View>
          <Text variant="caption" color={themeColors.textMuted} style={styles.note}>
            Utilisé pour calibrer les calculs énergétiques (DEJ, EA, seuils).
          </Text>
        </View>

        <View style={styles.fieldGap}>
          <FloatingLabelInput
            label="Taille (cm)"
            value={data.height}
            onChangeText={(v) => onChange({ height: v })}
            keyboardType="numeric"
            autoComplete="off"
          />
        </View>
        <View style={styles.fieldGap}>
          <FloatingLabelInput
            label="Poids (kg)"
            value={data.weight}
            onChangeText={(v) => onChange({ weight: v })}
            keyboardType="numeric"
            autoComplete="off"
          />
        </View>
        <View style={styles.scrollPad} />
      </View>
    </ScrollView>
  );
}

function Step2Sports({ data, onChange, themeColors, accent }: {
  data: OnboardingData;
  onChange: (d: Partial<OnboardingData>) => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  function toggleSport(key: Sport) {
    const next = data.sports.includes(key)
      ? data.sports.filter((s) => s !== key)
      : [...data.sports, key];
    // Remove levels for deselected sports
    const nextLevels = { ...data.levels };
    if (!next.includes(key)) delete nextLevels[key];
    onChange({ sports: next, levels: nextLevels });
  }

  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <View style={styles.stepContent}>
        <View style={[styles.rowList, { borderColor: themeColors.border }]}>
          {SPORTS.map((sport, i) => {
            const active = data.sports.includes(sport.key);
            return (
              <Pressable
                key={sport.key}
                onPress={() => toggleSport(sport.key)}
                style={[
                  styles.disciplineRow,
                  active && { backgroundColor: `${accent}14` },
                  i < SPORTS.length - 1 && { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: themeColors.border },
                ]}
              >
                <View style={[styles.disciplineIcon, { backgroundColor: themeColors.surface2 }]}>
                  <IconComponent name={sport.icon} size={20} color={active ? accent : themeColors.textSecondary} />
                </View>
                <View style={styles.disciplineText}>
                  <Text variant="bodyBold" color={themeColors.foreground}>{sport.label}</Text>
                  <Text variant="caption" color={themeColors.textSecondary}>{sport.sub}</Text>
                </View>
                {active && (
                  <IconComponent name="Check" size={18} color={accent} />
                )}
              </Pressable>
            );
          })}
        </View>
        <Text variant="caption" color={themeColors.textMuted} style={styles.note}>
          {data.sports.length === 0
            ? 'Sélectionne au minimum 1 discipline.'
            : `${data.sports.length} sélectionné${data.sports.length > 1 ? 's' : ''}`}
        </Text>
      </View>
    </ScrollView>
  );
}

function Step3Level({ data, onChange, themeColors, accent }: {
  data: OnboardingData;
  onChange: (d: Partial<OnboardingData>) => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  function setLevel(sport: Sport, idx: number) {
    onChange({ levels: { ...data.levels, [sport]: idx } });
  }

  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <View style={styles.stepContent}>
        {data.sports.map((sportKey) => {
          const sport = SPORTS.find((s) => s.key === sportKey)!;
          const currentLevel = data.levels[sportKey] ?? -1;
          return (
            <View key={sportKey} style={styles.levelBlock}>
              <View style={styles.levelHeader}>
                <IconComponent name={sport.icon} size={16} color={themeColors.textSecondary} />
                <Text variant="bodyBold" color={themeColors.foreground} style={{ marginLeft: 8 }}>{sport.label}</Text>
              </View>
              <View style={styles.segRow}>
                <SegmentedControl
                  options={LEVEL_LABELS}
                  selected={currentLevel}
                  onChange={(i) => setLevel(sportKey, i)}
                  variant="accent"
                />
              </View>
            </View>
          );
        })}
        <View style={styles.scrollPad} />
      </View>
    </ScrollView>
  );
}

function Step4Objective({ data, onChange, themeColors, accent }: {
  data: OnboardingData;
  onChange: (d: Partial<OnboardingData>) => void;
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <View style={styles.stepContent}>
        <View style={[styles.rowList, { borderColor: themeColors.border }]}>
          {OBJECTIVES.map((obj, i) => {
            const active = data.objective === i;
            return (
              <Pressable
                key={obj}
                onPress={() => onChange({ objective: i })}
                style={[
                  styles.objectiveRow,
                  active && { backgroundColor: `${accent}14` },
                  i < OBJECTIVES.length - 1 && { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: themeColors.border },
                ]}
              >
                {/* Radio bullet */}
                <View style={[
                  styles.radio,
                  { borderColor: active ? accent : themeColors.border },
                  active && { backgroundColor: accent },
                ]}>
                  {active && <View style={styles.radioDot} />}
                </View>
                <Text variant="body" color={themeColors.foreground} style={{ flex: 1 }}>{obj}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </ScrollView>
  );
}

function Step5Connectors({ themeColors, accent }: {
  themeColors: ReturnType<typeof useTheme>['colors'];
  accent: string;
}) {
  const [stravaConnected, setStravaConnected] = useState(false);
  const [hevyConnected, setHevyConnected] = useState(false);

  const CONNECTORS = [
    {
      key: 'apple',
      label: 'Apple Health',
      icon: 'Heart' as const,
      connected: true,
      onToggle: () => {},
      disabled: true,
    },
    {
      key: 'strava',
      label: 'Strava',
      icon: 'Activity' as const,
      connected: stravaConnected,
      onToggle: () => setStravaConnected((c) => !c),
      disabled: false,
    },
    {
      key: 'hevy',
      label: 'Hevy',
      icon: 'Lifting' as const,
      connected: hevyConnected,
      onToggle: () => setHevyConnected((c) => !c),
      disabled: false,
    },
  ];

  return (
    <ScrollView showsVerticalScrollIndicator={false}>
      <View style={styles.stepContent}>
        <View style={[styles.rowList, { borderColor: themeColors.border }]}>
          {CONNECTORS.map((c, i) => (
            <View
              key={c.key}
              style={[
                styles.connectorRow,
                i < CONNECTORS.length - 1 && { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: themeColors.border },
              ]}
            >
              <View style={[styles.disciplineIcon, { backgroundColor: themeColors.surface2 }]}>
                <IconComponent name={c.icon} size={18} color={themeColors.textSecondary} />
              </View>
              <View style={styles.connectorText}>
                <Text variant="bodyBold" color={themeColors.foreground}>{c.label}</Text>
                <Text variant="caption" color={c.connected ? colors.zoneGreen : themeColors.textMuted}>
                  {c.connected ? '• Connecté' : '• Non connecté'}
                </Text>
              </View>
              {!c.disabled && (
                <Pressable
                  onPress={c.onToggle}
                  style={[styles.connectBtn, { borderColor: c.connected ? themeColors.border : accent }]}
                >
                  <Text variant="caption" color={c.connected ? themeColors.textSecondary : accent}>
                    {c.connected ? 'Déconnecter' : 'Connecter'}
                  </Text>
                </Pressable>
              )}
            </View>
          ))}
        </View>
        <Text variant="caption" color={themeColors.textMuted} style={styles.note}>
          Tu pourras connecter ou déconnecter tes apps à tout moment dans les réglages.
        </Text>
      </View>
    </ScrollView>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function OnboardingScreen() {
  const router = useRouter();
  const { colorMode, colors: themeColors } = useTheme();
  const isDark = colorMode === 'dark';
  const accent = isDark ? colors.accentDark : colors.accent;
  const insets = useSafeAreaInsets();

  const [step, setStep] = useState(1);
  const [data, setData] = useState<OnboardingData>(INITIAL_DATA);
  const slideAnim = useRef(new Animated.Value(0)).current;
  const { width } = Dimensions.get('window');

  function update(partial: Partial<OnboardingData>) {
    setData((d) => ({ ...d, ...partial }));
  }

  function animateStep(newStep: number, dir: 'forward' | 'back') {
    const outTo = dir === 'forward' ? -width : width;
    const inFrom = dir === 'forward' ? width : -width;
    Animated.timing(slideAnim, {
      toValue: outTo,
      duration: 220,
      useNativeDriver: true,
    }).start(() => {
      setStep(newStep);
      slideAnim.setValue(inFrom);
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 220,
        useNativeDriver: true,
      }).start();
    });
  }

  function goNext() {
    if (step < TOTAL_STEPS) {
      animateStep(step + 1, 'forward');
    } else {
      router.replace('/(tabs)');
    }
  }

  function goBack() {
    if (step > 1) {
      animateStep(step - 1, 'back');
    }
  }

  // CTA enabled logic
  const ctaEnabled = (() => {
    if (step === 1) return data.firstName.trim().length > 0;
    if (step === 2) return data.sports.length > 0;
    if (step === 3) return data.sports.every((s) => data.levels[s] !== undefined);
    if (step === 4) return data.objective !== -1;
    return true; // step 5 always enabled
  })();

  const meta = STEP_META[step - 1]!;
  const sharedProps = { data, onChange: update, themeColors, accent };

  return (
    <KeyboardAvoidingView
      style={[styles.flex, { backgroundColor: themeColors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <SafeAreaView style={styles.flex} edges={['top']}>
        {/* Header — progress + back + skip */}
        <View style={styles.header}>
          <Pressable
            onPress={goBack}
            disabled={step === 1}
            hitSlop={12}
            style={{ opacity: step === 1 ? 0 : 1 }}
          >
            <Text variant="secondary" color={accent}>← Retour</Text>
          </Pressable>

          <View style={styles.progressWrap}>
            <ProgressSegments total={TOTAL_STEPS} current={step} />
          </View>

          <View style={{ width: 60, alignItems: 'flex-end' }}>
            {step === TOTAL_STEPS ? (
              <Pressable onPress={() => router.replace('/(tabs)')} hitSlop={12}>
                <Text variant="secondary" color={themeColors.textSecondary}>Passer</Text>
              </Pressable>
            ) : <View />}
          </View>
        </View>

        {/* Animated step body */}
        <Animated.View
          style={[styles.flex, { transform: [{ translateX: slideAnim }] }]}
        >
          <View style={styles.stepHeader}>
            <Text variant="label" color={themeColors.textMuted}>
              {`ÉTAPE 0${step} · ${meta.label}`}
            </Text>
            <Text variant="stepTitle" style={styles.stepTitle}>{meta.title}</Text>
            <Text variant="body" color={themeColors.textSecondary}>{meta.subtitle}</Text>
          </View>

          <View style={styles.flex}>
            {step === 1 && <Step1Profile {...sharedProps} />}
            {step === 2 && <Step2Sports  {...sharedProps} />}
            {step === 3 && <Step3Level   {...sharedProps} />}
            {step === 4 && <Step4Objective {...sharedProps} />}
            {step === 5 && <Step5Connectors themeColors={themeColors} accent={accent} />}
          </View>
        </Animated.View>
      </SafeAreaView>

      {/* Fixed CTA */}
      <View style={[styles.ctaBar, { paddingBottom: insets.bottom + 16, backgroundColor: themeColors.background }]}>
        <Button
          title={step === TOTAL_STEPS ? 'Terminer' : 'Suivant'}
          onPress={goNext}
          disabled={!ctaEnabled}
          style={styles.ctaBtn}
        />
      </View>
    </KeyboardAvoidingView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  flex: { flex: 1 },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 8,
    gap: 8,
  },
  progressWrap: { flex: 1 },

  // Step header (label + title + subtitle)
  stepHeader: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 0,
    gap: 6,
  },
  stepTitle: { marginTop: 2, marginBottom: 2 },

  // Step content
  stepContent: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 8,
  },
  fieldGap: { marginTop: 14 },
  fieldLabel: { marginBottom: 8 },
  segRow: { marginTop: 4 },
  note: { marginTop: 8, lineHeight: 18 },
  scrollPad: { height: 80 },

  // Discipline rows
  rowList: {
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  disciplineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    minHeight: 64,
    gap: 12,
  },
  disciplineIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  disciplineText: { flex: 1, gap: 2 },

  // Level block
  levelBlock: { marginBottom: 20 },
  levelHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },

  // Objective
  objectiveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    gap: 14,
  },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FFFFFF',
  },

  // Connectors
  connectorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 12,
  },
  connectorText: { flex: 1, gap: 2 },
  connectBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
  },

  // CTA bar
  ctaBar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  ctaBtn: { width: '100%' },
});
