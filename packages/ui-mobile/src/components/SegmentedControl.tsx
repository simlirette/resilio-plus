import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { Text } from './Text';

interface SegmentedControlProps {
  options: string[];
  selected: number;
  onChange: (index: number) => void;
}

/**
 * Segmented control — 2 to 4 segments.
 * Spec: docs/design/training historycalendar/SPEC.md + onboarding/SPEC.md
 *
 * Active segment: surface (white/dark card) on surfaceAlt container.
 * Radius: 10px on container, 8px on active pill.
 * Height: 36px.
 */
export function SegmentedControl({ options, selected, onChange }: SegmentedControlProps): React.JSX.Element {
  const { colors: themeColors } = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: themeColors.surface2 }]}>
      {options.map((option, i) => {
        const active = i === selected;
        return (
          <Pressable
            key={option}
            onPress={() => onChange(i)}
            style={[
              styles.segment,
              active && [styles.activeSegment, { backgroundColor: themeColors.surface1 }],
            ]}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
          >
            <Text
              variant="body"
              color={themeColors.foreground}
              style={active ? [styles.label, styles.labelActive] : styles.label}
            >
              {option}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    borderRadius: 10,
    padding: 3,
    height: 36,
  },
  segment: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
  },
  activeSegment: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 1,
  },
  label: {
    fontSize: 13,
  },
  labelActive: {
    fontFamily: 'SpaceGrotesk_600SemiBold' as const,
  },
});
