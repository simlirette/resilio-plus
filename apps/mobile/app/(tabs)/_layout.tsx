import { NativeTabs } from 'expo-router/unstable-native-tabs';
import { colors } from '@resilio/design-tokens';

/**
 * Tab bar layout using NativeTabs (expo-router/unstable-native-tabs).
 * iOS: UITabBarController with liquid glass (systemChromeMaterial blur).
 * Android: Material 3 bottom navigation.
 * Web: Radix UI tabs fallback (built into expo-router).
 *
 * Icons: SF Symbols (iOS), fallback to src on other platforms.
 * Exception to Lucide-only rule: tab bar uses SF Symbols for native iOS integration.
 * All other icons in the app continue to use Lucide via @resilio/ui-mobile/Icon.
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

      <NativeTabs.Trigger name="check-in">
        <NativeTabs.Trigger.Label>Check-in</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'heart', selected: 'heart.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="training">
        <NativeTabs.Trigger.Label>Entraînement</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon
          sf={{ default: 'chart.bar', selected: 'chart.bar.fill' }}
        />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="coach">
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
