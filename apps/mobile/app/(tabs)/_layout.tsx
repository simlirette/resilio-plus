import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { colors } from '@resilio/design-tokens';

/**
 * Tab bar layout — 4 tabs V1.
 * Accueil | Entraînement | Coach | Profil
 * Métriques = V2 (drill-down depuis Home via tap sur les anneaux).
 * Check-in = hors tab bar, accessible depuis Home via CTA → /check-in.
 *
 * iOS: UITabBarController with liquid glass (systemChromeMaterial blur).
 * Android: Material 3 bottom navigation.
 * Web: Radix UI tabs fallback (built into expo-router).
 *
 * Icons: SF Symbols (iOS).
 * Exception to Lucide-only rule: tab bar uses SF Symbols for native iOS integration.
 */
export default function TabsLayout() {
  return (
    <NativeTabs
      tintColor={colors.accent}
      blurEffect="systemChromeMaterial"
    >
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Accueil</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'house', selected: 'house.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="training">
        <NativeTabs.Trigger.Label>Entraînement</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'calendar', selected: 'calendar' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="chat">
        <NativeTabs.Trigger.Label>Coach</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'bolt', selected: 'bolt.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="profile">
        <NativeTabs.Trigger.Label>Profil</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'person', selected: 'person.fill' }}
        />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
