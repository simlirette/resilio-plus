import { Redirect } from 'expo-router';

export default function Index() {
  // No auth implemented yet — redirect directly to login
  return <Redirect href="/(auth)/login" />;
}
