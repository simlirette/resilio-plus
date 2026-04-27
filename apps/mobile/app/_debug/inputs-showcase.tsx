/**
 * Debug: FloatingLabelInput + SegmentedControl showcase.
 * Naviguer vers /_debug/inputs-showcase dans Expo Go.
 * Comparer avec docs/design/flow auth/<page>/SPEC.md
 */
import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { FloatingLabelInput, Screen, Text, useTheme } from '@resilio/ui-mobile';

export default function InputsShowcase() {
  const { colors: c } = useTheme();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [filled, setFilled] = useState('athlete@resilio.app');
  const [errorVal, setErrorVal] = useState('test@bad');

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text variant="pageTitle" color={c.foreground}>Inputs</Text>

        <View style={styles.section}>
          <Text variant="label" color={c.textMuted}>ÉTAT VIDE</Text>
          <FloatingLabelInput
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        <View style={styles.section}>
          <Text variant="label" color={c.textMuted}>ÉTAT REMPLI</Text>
          <FloatingLabelInput
            label="Email"
            value={filled}
            onChangeText={setFilled}
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        <View style={styles.section}>
          <Text variant="label" color={c.textMuted}>MOT DE PASSE (toggle)</Text>
          <FloatingLabelInput
            label="Mot de passe"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            showToggle
          />
        </View>

        <View style={styles.section}>
          <Text variant="label" color={c.textMuted}>ÉTAT ERREUR</Text>
          <FloatingLabelInput
            label="Email"
            value={errorVal}
            onChangeText={setErrorVal}
            keyboardType="email-address"
            autoCapitalize="none"
            error="Format d'email invalide."
          />
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: 24, paddingVertical: 24, paddingBottom: 80, gap: 8 },
  section: { gap: 8, marginTop: 16 },
});
