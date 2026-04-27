import { NativeTabs, Label, Icon } from 'expo-router/unstable-native-tabs';
import { colors } from '@resilio/design-tokens';

/**
 * Tab bar layout using NativeTabs (expo-router/unstable-native-tabs).
 * iOS: UITabBarController with liquid glass (systemChromeMaterial blur).
 * Android: Material 3 bottom navigation.
 * Web: Radix UI tabs fallback (built into expo-router).
 *
 * SF Symbols: tab bar only (exception to Lucide-only rule — native iOS integration).
 * Label + Icon are children of NativeTabs.Trigger (not sub-components).
 * tintColor: colors.accent (amber). Confirmed on SDK 54 (see commit e2d1810).
 * 0 hex inline: all colors via design-tokens.
 */
export default function TabsLayout() {
  return (
    <NativeTabs
      tintColor={colors.accent}
      blurEffect="systemChromeMaterial"
    >
      <NativeTabs.Trigger name="index">
        <Label>Accueil</Label>
        <Icon sf={{ default: 'house', selected: 'house.fill' }} />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="training">
        <Label>Entraînement</Label>
        <Icon sf={{ default: 'calendar.circle', selected: 'calendar.circle.fill' }} />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="chat">
        <Label>Coach</Label>
        <Icon sf={{ default: 'message', selected: 'message.fill' }} />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="profile">
        <Label>Profil</Label>
        <Icon sf={{ default: 'person', selected: 'person.fill' }} />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
