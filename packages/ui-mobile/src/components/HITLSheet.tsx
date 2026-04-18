import React from 'react';
import { View, Modal, Pressable, StyleSheet, ScrollView } from 'react-native';
import { Text } from './Text';
import { Button } from './Button';
import { useTheme } from '../theme/ThemeProvider';

export interface HITLOption {
  id: string;
  label: string;
  description?: string;
}

interface HITLSheetProps {
  visible: boolean;
  title: string;
  options: HITLOption[];
  onSelect: (id: string) => void;
  onDismiss: () => void;
}

export function HITLSheet({
  visible, title, options, onSelect, onDismiss,
}: HITLSheetProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onDismiss}
    >
      <Pressable
        style={styles.overlay}
        onPress={onDismiss}
        accessibilityLabel="Fermer"
      />
      <View
        style={[
          styles.sheet,
          {
            backgroundColor: themeColors.surface1,
            borderColor: themeColors.border,
          },
        ]}
      >
        <View style={[styles.handle, { backgroundColor: themeColors.border }]} />
        <Text variant="body" color={themeColors.foreground} style={styles.title}>
          {title}
        </Text>
        <ScrollView style={styles.scroll} bounces={false}>
          {options.map((opt) => (
            <Pressable
              key={opt.id}
              style={[styles.option, { borderColor: themeColors.border }]}
              onPress={() => { onSelect(opt.id); onDismiss(); }}
            >
              <Text variant="body" color={themeColors.foreground}>{opt.label}</Text>
              {opt.description !== undefined && (
                <Text variant="secondary" color={themeColors.textSecondary}>
                  {opt.description}
                </Text>
              )}
            </Pressable>
          ))}
        </ScrollView>
        <Button variant="ghost" title="Annuler" onPress={onDismiss} style={styles.cancel} />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)' },
  sheet: {
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderWidth: 0.5,
    paddingTop: 12,
    paddingHorizontal: 20,
    paddingBottom: 40,
    maxHeight: '80%',
  },
  handle: {
    width: 36, height: 4, borderRadius: 2,
    alignSelf: 'center', marginBottom: 20,
  },
  title: { fontWeight: '600', marginBottom: 16 } as const,
  scroll: { flexGrow: 0 },
  option: {
    paddingVertical: 14,
    borderBottomWidth: 0.5,
    gap: 4,
  },
  cancel: { marginTop: 12 },
});
