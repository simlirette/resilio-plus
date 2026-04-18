// apps/mobile/app/(onboarding)/index.tsx
import React, { useState, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Card, ProgressDots, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

type Step = 0 | 1 | 2 | 3 | 4;
const TOTAL = 5;

interface StepConfig {
  label: string;
  title: string;
  sub: string;
  options: string[];
}

const STEPS: Record<Step, StepConfig> = {
  0: {
    label: 'ÉTAPE 1 / 5',
    title: 'Quels sports pratiques-tu ?',
    sub: "Sélectionne tout ce qui s'applique.",
    options: ['Course à pied', 'Musculation', 'Natation', 'Cyclisme'],
  },
  1: {
    label: 'ÉTAPE 2 / 5',
    title: 'Quel est ton objectif principal ?',
    sub: 'Un seul objectif pour commencer.',
    options: ['Perdre du poids', 'Gagner en endurance', 'Améliorer ma force', 'Compétition'],
  },
  2: {
    label: 'ÉTAPE 3 / 5',
    title: "Combien d'heures par semaine ?",
    sub: "Volume d'entraînement hebdomadaire visé.",
    options: ['Moins de 3 h', '3–5 h', '6–8 h', 'Plus de 8 h'],
  },
  3: {
    label: 'ÉTAPE 4 / 5',
    title: 'Quel est ton niveau ?',
    sub: 'Auto-évaluation honnête.',
    options: ['Débutant', 'Intermédiaire', 'Avancé', 'Compétiteur'],
  },
  4: {
    label: 'ÉTAPE 5 / 5',
    title: 'Connecte tes applis',
    sub: 'Optionnel — tu peux le faire plus tard dans les réglages.',
    options: ['Strava', 'Hevy', 'Apple Santé', 'Passer cette étape'],
  },
};

export default function OnboardingScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  const [step, setStep] = useState<Step>(0);
  const [answers, setAnswers] = useState<Partial<Record<Step, string>>>({});

  const config = STEPS[step];
  const canContinue = answers[step] !== undefined;
  const isLast = step === TOTAL - 1;

  const handleSelect = useCallback((option: string) => {
    setAnswers((prev) => ({ ...prev, [step]: option }));
  }, [step]);

  const handleNext = useCallback(() => {
    if (isLast) {
      router.replace('/(tabs)' as never);
    } else {
      setStep((s) => (s + 1) as Step);
    }
  }, [isLast, router]);

  const handleBack = useCallback(() => {
    if (step === 0) {
      router.back();
    } else {
      setStep((s) => (s - 1) as Step);
    }
  }, [step, router]);

  return (
    <Screen>
      <View style={[styles.topBar, { borderBottomColor: themeColors.border }]}>
        <Pressable onPress={handleBack} style={styles.backBtn}>
          <Text variant="secondary" color={step === 0 ? themeColors.textMuted : themeColors.textSecondary}>
            ← Retour
          </Text>
        </Pressable>
        <ProgressDots step={step} total={TOTAL} />
        <Pressable onPress={() => router.replace('/(tabs)' as never)} style={styles.skipBtn}>
          <Text variant="secondary" color={themeColors.textMuted}>Passer</Text>
        </Pressable>
      </View>

      <ScrollView
        style={styles.flex}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        <Text
          variant="label"
          color={themeColors.textMuted}
          style={styles.stepLabel}
        >
          {config.label}
        </Text>

        <Text variant="title" color={themeColors.foreground} style={styles.title}>
          {config.title}
        </Text>
        <Text variant="secondary" color={themeColors.textSecondary} style={styles.sub}>
          {config.sub}
        </Text>

        <View style={styles.options}>
          {config.options.map((option) => {
            const selected = answers[step] === option;
            return (
              <Pressable
                key={option}
                onPress={() => handleSelect(option)}
                style={[
                  styles.optionCard,
                  {
                    backgroundColor: selected ? colors.accentDim : themeColors.surface1,
                    borderColor: selected ? colors.accent : themeColors.border,
                  },
                ]}
              >
                <Text
                  variant="body"
                  color={selected ? colors.accent : themeColors.foreground}
                >
                  {option}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>

      <View style={[styles.cta, { borderTopColor: themeColors.border }]}>
        <Button
          title={isLast ? 'Commencer' : 'Continuer'}
          onPress={handleNext}
          disabled={!canContinue}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
  },
  backBtn: { padding: 4, minWidth: 60 },
  skipBtn: { padding: 4, minWidth: 60, alignItems: 'flex-end' },
  content: { paddingHorizontal: 24, paddingTop: 28, paddingBottom: 24 },
  stepLabel: {
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 14,
  },
  title: { marginBottom: 10 },
  sub: { marginBottom: 28 },
  options: { gap: 10 },
  optionCard: {
    borderRadius: 16,
    borderWidth: 0.5,
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  cta: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 32,
    borderTopWidth: 0.5,
  },
});
