import * as SecureStore from 'expo-secure-store';

const ACCESS_TOKEN_KEY = 'resilio.accessToken';
const REFRESH_TOKEN_KEY = 'resilio.refreshToken';
const ATHLETE_ID_KEY = 'resilio.athleteId';

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  athleteId: string;
}

export async function saveAuthSession(session: AuthSession): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_TOKEN_KEY, session.accessToken),
    SecureStore.setItemAsync(REFRESH_TOKEN_KEY, session.refreshToken),
    SecureStore.setItemAsync(ATHLETE_ID_KEY, session.athleteId),
  ]);
}

export async function loadAuthSession(): Promise<AuthSession | null> {
  const [accessToken, refreshToken, athleteId] = await Promise.all([
    SecureStore.getItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.getItemAsync(REFRESH_TOKEN_KEY),
    SecureStore.getItemAsync(ATHLETE_ID_KEY),
  ]);

  if (!accessToken || !refreshToken || !athleteId) {
    return null;
  }

  return { accessToken, refreshToken, athleteId };
}

export async function clearAuthSession(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
    SecureStore.deleteItemAsync(ATHLETE_ID_KEY),
  ]);
}

