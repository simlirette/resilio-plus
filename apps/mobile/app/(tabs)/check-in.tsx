import { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { Button, Screen, useTheme, Icon } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

type Step = 0 | 1;

const QUESTIONS = [
  { id: 0 as Step, label: 'Quel est ton niveau d\'énergie aujourd\'hui ?', options: ['Très bas', 'Bas', 'Modéré', 'Élevé', 'Très élevé'] },
  { id: 1 as Step, label: 'Comment as-tu dormi la nuit dernière ?', options: ['Très mal', 'Mal', 'Correctement', 'Bien', 'Excellent'] },
];

export default function CheckInScreen() {
  const router = useRouter();
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;
  const [step, setStep] = useState<Step>(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});

  const question = QUESTIONS[step];
  const isLast = step === QUESTIONS.length - 1;
  const canProceed = answers[step] !== undefined;

  function handleSelect(option: string) {
    setAnswers((prev) => ({ ...prev, [step]: option }));
  }

  function handleNext() {
    if (isLast) {
      router.replace('/');
    } else {
      setStep((s) => (s + 1) as Step);
    }
  }

  function handleBack() {
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
            const selected = answers[step] === option;
            return (
              <TouchableOpacity
                key={option}
                style={[styles.option, {
                  backgroundColor: selected ? colors.primaryDim : themeColors.surface2,
                  borderColor: selected ? colors.primary : themeColors.border,
                }]}
                onPress={() => handleSelect(option)}
                activeOpacity={0.7}
              >
                <Text style={[styles.optionText, { color: selected ? colors.primary : themeColors.foreground, fontWeight: selected ? '600' : '400' }]}>
                  {option}
                </Text>
                {selected && <Icon.Check color={colors.primary} size={16} />}
              </TouchableOpacity>
            );
          })}
        </View>
        <View style={styles.actions}>
          <Button title="Précédent" onPress={handleBack} variant="secondary" style={styles.actionButton} />
          <Button title={isLast ? 'Terminer' : 'Continuer'} onPress={handleNext} disabled={!canProceed} style={styles.actionButton} />
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
  actions: { flexDirection: 'row', gap: 12, marginTop: 24 },
  actionButton: { flex: 1 },
});
