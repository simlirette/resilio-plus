import '../global.css';
import { Stack } from 'expo-router';
import { ThemeProvider } from '@resilio/ui-mobile';

export default function RootLayout() {
  return (
    <ThemeProvider>
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="login" />
        <Stack.Screen name="dashboard" />
        <Stack.Screen name="check-in" />
      </Stack>
    </ThemeProvider>
  );
}
