/**
 * Debug: Text variants showcase — Space Grotesk
 * Naviguer vers /_debug/text-showcase dans Expo Go pour valider.
 * Comparer avec docs/design/<page>/SPEC.md sections Typographie.
 */
import { ScrollView, View, StyleSheet } from 'react-native';
import { Screen, Text, useTheme } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

function Section({ label }: { label: string }) {
  const { colors: c } = useTheme();
  return (
    <View style={styles.sectionHeader}>
      <Text variant="label" color={c.textMuted}>{label}</Text>
    </View>
  );
}

function Row({ variant, sample }: { variant: string; sample?: string }) {
  const { colors: c } = useTheme();
  return (
    <View style={styles.row}>
      {/* @ts-ignore — intentional showcase of all variants including back-compat */}
      <Text variant={variant} color={c.foreground}>{sample ?? variant}</Text>
      <Text variant="caption" color={c.textMuted} style={styles.variantLabel}>{variant}</Text>
    </View>
  );
}

export default function TextShowcase() {
  const { colorMode, colors: c } = useTheme();
  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.content}>
        <Text variant="pageTitle" color={c.foreground}>Text Variants</Text>
        <Text variant="caption" color={c.textMuted} style={styles.mode}>
          Mode: {colorMode}
        </Text>

        <Section label="HERO NUMBERS" />
        <Row variant="heroNumber" sample="78" />
        <Row variant="heroPace" sample="5:42" />
        <Row variant="heroLarge" sample="72 kg" />

        <Section label="TITRES" />
        <Row variant="pageTitle" sample="Entraînement" />
        <Row variant="stepTitle" sample="Ton profil" />
        <Row variant="sectionTitle" sample="Séance du jour" />

        <Section label="NAVIGATION" />
        <Row variant="wordmark" sample="Resilio+" />
        <Row variant="navBar" sample="Head Coach" />
        <Row variant="metric" sample="5:42 /km" />

        <Section label="BODY" />
        <Row variant="body" sample="Corps de texte normal, 15px regular." />
        <Row variant="bodyBold" sample="Corps de texte accentué, 15px semibold." />
        <Row variant="secondary" sample="Texte secondaire, 14px regular — justification coach." />
        <Row variant="caption" sample="Delta: +4 vs hier — 13px tabular" />

        <Section label="LABELS SMALL-CAPS" />
        <Row variant="label" sample="SÉANCE DU JOUR" />
        <Row variant="smallCaps" sample="READINESS" />

        <Section label="COULEURS SÉMANTIQUES" />
        <View style={styles.row}>
          <Text variant="metric" color={colors.physio.red.light}>45</Text>
          <Text variant="metric" color={colors.accent}>78</Text>
          <Text variant="metric" color={colors.physio.green.light}>92</Text>
        </View>

        <Section label="BACK-COMPAT" />
        <Row variant="display" sample="72" />
        <Row variant="title" sample="Titre compat" />
        <Row variant="mono" sample="5:42" />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: 20, paddingVertical: 24, paddingBottom: 80, gap: 4 },
  mode: { marginBottom: 16, marginTop: 4 },
  sectionHeader: { marginTop: 24, marginBottom: 8 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', paddingVertical: 6, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: 'rgba(128,128,128,0.2)' },
  variantLabel: { opacity: 0.5, fontSize: 10 },
});
