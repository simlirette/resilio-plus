import React from 'react';
import { View, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { Screen, Text, Button, Card, DisciplineIcon, useTheme } from '@resilio/ui-mobile';

interface Block {
  label: string;
  duration?: string;
  note?: string;
}

const MOCK_SESSION = {
  sport: 'running' as const,
  category: 'SÉANCE COURSE · Z2',
  title: 'Endurance fondamentale',
  duration: '52 min',
  load: 'Modérée',
  zone: 'Z2',
  why: "Cette séance développe ta base aérobie. Le volume Z2 est le fondement de l'endurance à long terme — tu dois pouvoir tenir une conversation sans effort.",
  blocks: [
    { label: 'Échauffement', duration: '10 min', note: 'Allure très facile' },
    { label: 'Bloc principal', duration: '34 min', note: 'Z2 — allure conversationnelle' },
    { label: 'Retour au calme', duration: '8 min', note: 'Décompression progressive' },
  ] as Block[],
};

export default function TodaySessionScreen(): React.JSX.Element {
  const router = useRouter();
  const { colors: themeColors } = useTheme();

  return (
    <Screen>
      <View style={[styles.header, { borderBottomColor: themeColors.border }]}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text variant="secondary" color={themeColors.textSecondary}>← Retour</Text>
        </Pressable>
        <View style={styles.headerCenter}>
          <Text variant="label" color={themeColors.textMuted} style={styles.headerSub}>
            {MOCK_SESSION.category}
          </Text>
          <Text variant="body" color={themeColors.foreground} style={styles.headerTitle}>
            {MOCK_SESSION.title}
          </Text>
        </View>
        <View style={styles.headerRight} />
      </View>

      <ScrollView style={styles.flex} contentContainerStyle={styles.content}>
        <View style={styles.titleRow}>
          <DisciplineIcon sport={MOCK_SESSION.sport} size={20} color={themeColors.textMuted} />
          <Text variant="title" color={themeColors.foreground} style={styles.titleText}>
            {MOCK_SESSION.title}
          </Text>
        </View>

        <View style={[styles.metaRow, { borderColor: themeColors.border }]}>
          <View style={styles.metaCell}>
            <Text variant="label" color={themeColors.textMuted} style={styles.metaCellLabel}>DURÉE</Text>
            <Text variant="body" color={themeColors.foreground}>{MOCK_SESSION.duration}</Text>
          </View>
          <View style={[styles.metaSep, { backgroundColor: themeColors.border }]} />
          <View style={styles.metaCell}>
            <Text variant="label" color={themeColors.textMuted} style={styles.metaCellLabel}>CHARGE</Text>
            <Text variant="body" color={themeColors.foreground}>{MOCK_SESSION.load}</Text>
          </View>
          <View style={[styles.metaSep, { backgroundColor: themeColors.border }]} />
          <View style={styles.metaCell}>
            <Text variant="label" color={themeColors.textMuted} style={styles.metaCellLabel}>INTENSITÉ</Text>
            <Text variant="body" color={themeColors.foreground}>{MOCK_SESSION.zone}</Text>
          </View>
        </View>

        <Card style={styles.whyCard}>
          <Text variant="label" color={themeColors.textMuted} style={styles.whyLabel}>
            POURQUOI CETTE SÉANCE
          </Text>
          <Text variant="body" color={themeColors.textSecondary} style={styles.whyText}>
            {MOCK_SESSION.why}
          </Text>
        </Card>

        <Text variant="label" color={themeColors.textMuted} style={styles.sectionLabel}>
          DÉROULÉ
        </Text>
        {MOCK_SESSION.blocks.map((block, i) => (
          <Card key={i} style={styles.blockCard}>
            <View style={styles.blockHeader}>
              <Text variant="body" color={themeColors.foreground}>{block.label}</Text>
              {block.duration !== undefined && (
                <Text variant="secondary" color={themeColors.textMuted}>{block.duration}</Text>
              )}
            </View>
            {block.note !== undefined && (
              <Text variant="secondary" color={themeColors.textSecondary} style={styles.blockNote}>
                {block.note}
              </Text>
            )}
          </Card>
        ))}
      </ScrollView>

      <View style={[styles.cta, { borderTopColor: themeColors.border, backgroundColor: themeColors.background }]}>
        <Button
          title="Démarrer la séance"
          onPress={() => router.push('/session/live' as never)}
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
    paddingVertical: 10,
    borderBottomWidth: 0.5,
  },
  backBtn: { width: 36, padding: 4 },
  headerCenter: { flex: 1, alignItems: 'center' },
  headerSub: { letterSpacing: 0.6, marginBottom: 2 },
  headerTitle: { fontWeight: '500' } as const,
  headerRight: { width: 36 },
  content: { paddingHorizontal: 20, paddingBottom: 32, paddingTop: 20 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 16 },
  titleText: { flex: 1 },
  metaRow: {
    flexDirection: 'row',
    borderRadius: 14,
    borderWidth: 0.5,
    overflow: 'hidden',
    marginBottom: 16,
  },
  metaCell: { flex: 1, alignItems: 'center', paddingVertical: 12 },
  metaCellLabel: { letterSpacing: 0.4, marginBottom: 4 },
  metaSep: { width: 0.5 },
  whyCard: { marginBottom: 20 },
  whyLabel: { letterSpacing: 0.8, marginBottom: 8 },
  whyText: { lineHeight: 20 },
  sectionLabel: { letterSpacing: 0.8, marginBottom: 12 },
  blockCard: { marginBottom: 8 },
  blockHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  blockNote: { marginTop: 4 },
  cta: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 32,
    borderTopWidth: 0.5,
  },
});
