import { Redirect, Tabs } from 'expo-router';
import { useTheme, Icon } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';
import { useAuth } from '../../src/auth/AuthProvider';

export default function TabsLayout() {
  const { colorMode } = useTheme();
  const { status } = useAuth();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;

  if (status === 'loading') {
    return null;
  }

  if (status === 'unauthenticated') {
    return <Redirect href="/(auth)/login" />;
  }

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
