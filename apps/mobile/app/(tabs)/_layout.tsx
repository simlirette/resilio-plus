import { Tabs } from 'expo-router';
import { useTheme, Icon } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function TabsLayout() {
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: themeColors.surface1,
          borderTopColor: themeColors.border,
          borderTopWidth: 1,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: themeColors.textMuted,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Accueil',
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Icon.Activity color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="check-in"
        options={{
          title: 'Check-in',
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Icon.Heart color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Coach',
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Icon.Energy color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profil',
          tabBarIcon: ({ color, size }: { color: string; size: number }) => (
            <Icon.User color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
