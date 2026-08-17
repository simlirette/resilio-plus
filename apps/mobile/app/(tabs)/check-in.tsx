import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { Button, Screen, useTheme, Icon } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import { MobileApiError } from '../../src/api/client';
import { useAuth } from '../../src/auth/AuthProvider';

type Step = 0 | 1 | 2 | 3;
type CheckInField = 'work_intensity' | 'stress_level' | 'legs_feeling' | 'energy_global';

interface CheckInPayload {
  work_intensity: 'light' | 'normal' | 'heavy' | 'exhausting';
  stress_level: 'none' | 'mild' | 'significant';
  legs_feeling: 'fresh' | 'normal' | 'heavy' | 'dead';
  energy_global: 'great' | 'ok' | 'low' | 'exhausted';
}

const QUESTIONS: Array<{
  field: CheckInField;
  label: string;
  options: Array<{ label: string; value: string }>;
}> = [
  {
    field: 'work_intensity',
    label: 'Charge de travail aujourd’hui',
    options: [
      { label: 'Legere', value: 'light' },
      { label: 'Normale', value: 'normal' },
      { label: 'Lourde', value: 'heavy' },
      { label: 'Epuisante', value: 'exhausting' },
    ],
  },
  {
    field: 'stress_level',
    label: 'Stress hors entrainement',
    options: [
      { label: 'Aucun', value: 'none' },
      { label: 'Leger', value: 'mild' },
      { label: 'Significatif', value: 'significant' },
    ],
  },
  {
    field: 'legs_feeling',
    label: 'Sensation des jambes',
    options: [
      { label: 'Fraiches', value: 'fresh' },
      { label: 'Normales', value: 'normal' },
      { label: 'Lourdes', value: 'heavy' },
      { label: 'Mortes', value: 'dead' },
    ],
  },
  {
    field: 'energy_global',
    label: 'Energie globale',
    options: [
      { label: 'Excellente', value: 'great' },
      { label: 'Correcte', value: 'ok' },
      { label: 'Basse', value: 'low' },
      { label: 'Epuisee', value: 'exhausted' },
    ],
  },
];

function isComplete(answers: Partial<Record<CheckInField, string>>): answers is CheckInPayload {
  return QUESTIONS.every((question) => Boolean(answers[question.field]));
}

export default function CheckInScreen() {
  const router = useRouter();
  const { session, apiRequest } = useAuth();
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const [step, setStep] = useState<Step>(0);
  const [answers, setAnswers] = useState<Partial<Record<CheckInField, string>>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const question = QUESTIONS[step];
  const isLast = step === QUESTIONS.length - 1;
  const canProceed = answers[question.field] !== undefined && !submitting;

  function handleSelect(value: string) {
    setError(null);
    setAnswers((prev) => ({ ...prev, [question.field]: value }));
  }

  async function submitCheckIn() {
    if (!session || !isComplete(answers)) {
      setError('Session ou reponses incompletes.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await apiRequest(`/athletes/${session.athleteId}/checkin`, {
        method: 'POST',
        body: JSON.stringify(answers),
      });
      router.replace('/(tabs)');
    } catch (err) {
      if (err instanceof MobileApiError && err.status === 409) {
        setError('Check-in deja soumis aujourd’hui.');
      } else {
        setError(err instanceof Error ? err.message : 'Check-in impossible.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleNext() {
    if (isLast) {
      void submitCheckIn();
    } else {
      setStep((s) => (s + 1) as Step);
    }
  }

  function handleBack() {
    if (submitting) return;
    if (step === 0) { router.back(); }
    else { setStep((s) => (s - 1) as Step); }
  }

  return (
    <Screen>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBack} style={styles.backButton}>
            <Icon.ChevronLeft color={themeColors.foreground} size={24} />
          </TouchableOpacity>
          <Text style={[styles.title, { color: themeColors.foreground }]}>Check-in quotidien</Text>
          <Text style={[styles.stepIndicator, { color: themeColors.textSecondary }]}>
            {step + 1} / {QUESTIONS.length}
          </Text>
        </View>
        <View style={[styles.progressTrack, { backgroundColor: themeColors.border }]}>
          <View style={[styles.progressFill, { backgroundColor: colors.primary, width: `${((step + 1) / QUESTIONS.length) * 100}%` }]} />
        </View>
        <Text style={[styles.question, { color: themeColors.foreground }]}>{question.label}</Text>
        <View style={styles.options}>
          {question.options.map((option) => {
            const selected = answers[question.field] === option.value;
            return (
              <TouchableOpacity
                key={option.value}
                style={[styles.option, {
                  backgroundColor: selected ? colors.primaryDim : themeColors.surface2,
                  borderColor: selected ? colors.primary : themeColors.border,
                }]}
                onPress={() => handleSelect(option.value)}
                activeOpacity={0.7}
                disabled={submitting}
              >
                <Text style={[styles.optionText, { color: selected ? colors.primary : themeColors.foreground, fontWeight: selected ? '600' : '400' }]}>
                  {option.label}
                </Text>
                {selected && <Icon.Check color={colors.primary} size={16} />}
              </TouchableOpacity>
            );
          })}
        </View>
        {error ? (
          <Text style={[styles.error, { color: colors.zoneRed }]}>{error}</Text>
        ) : null}
        <View style={styles.actions}>
          <Button title="Precedent" onPress={handleBack} variant="secondary" style={styles.actionButton} disabled={submitting} />
          <Button
            title={isLast ? 'Terminer' : 'Continuer'}
            onPress={handleNext}
            disabled={!canProceed}
            loading={submitting}
            style={styles.actionButton}
          />
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 24, paddingTop: 16, paddingBottom: 32 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  backButton: { padding: 4 },
  title: { fontSize: 16, fontWeight: '600' },
  stepIndicator: { fontSize: 13 },
  progressTrack: { height: 4, borderRadius: 2, marginBottom: 32, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 2 },
  question: { fontSize: 20, fontWeight: '700', lineHeight: 28, marginBottom: 24 },
  options: { flex: 1, gap: 10 },
  option: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 14, borderRadius: 12, borderWidth: 1 },
  optionText: { fontSize: 15 },
  error: { fontSize: 13, marginTop: 12 },
  actions: { flexDirection: 'row', gap: 12, marginTop: 24 },
  actionButton: { flex: 1 },
});
