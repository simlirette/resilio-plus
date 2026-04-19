import { Tabs } from 'expo-router';
import { colors } from '@resilio/design-tokens';
import { IconComponent } from '@resilio/ui-mobile';

/**
 * Tab bar layout — 4 tabs V1.
 * Accueil | Entraînement | Coach | Profil
 *
 * NativeTabs (SDK 55 only) replaced with standard expo-router Tabs for SDK 54 compat.
 */
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: 'rgba(255,255,255,0.45)',
        tabBarStyle: {
          backgroundColor: '#1A1816',
          borderTopColor: 'rgba(255,255,255,0.08)',
          borderTopWidth: 0.5,
        },
        tabBarLabelStyle: {
          fontFamily: 'SpaceGrotesk_500Medium',
          fontSize: 10,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Accueil',
          tabBarIcon: ({ color, size }) => (
            <IconComponent name="Home" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="training"
        options={{
          title: 'Entraînement',
          tabBarIcon: ({ color, size }) => (
            <IconComponent name="Calendar" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Coach',
          tabBarIcon: ({ color, size }) => (
            <IconComponent name="Energy" color={color} size={size} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profil',
          tabBarIcon: ({ color, size }) => (
            <IconComponent name="User" color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
