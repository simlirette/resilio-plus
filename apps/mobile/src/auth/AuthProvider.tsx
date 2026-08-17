import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  loginRequest,
  logoutRequest,
  meRequest,
  refreshRequest,
  type MeResponse,
} from '../api/auth';
import { getApiBaseUrl, mobileApiRequest, MobileApiError, type MobileApiRequestOptions } from '../api/client';
import {
  clearAuthSession,
  loadAuthSession,
  saveAuthSession,
  type AuthSession,
} from './tokenStorage';

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  status: AuthStatus;
  session: AuthSession | null;
  user: MeResponse | null;
  apiBaseUrl: string;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<string>;
  apiRequest: <T>(path: string, options?: MobileApiRequestOptions) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function sessionFromTokenResponse(tokens: {
  access_token: string;
  refresh_token: string;
  athlete_id: string;
}): AuthSession {
  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    athleteId: tokens.athlete_id,
  };
}

export function AuthProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const apiBaseUrl = useMemo(() => getApiBaseUrl(), []);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [session, setSession] = useState<AuthSession | null>(null);
  const [user, setUser] = useState<MeResponse | null>(null);
  const sessionRef = useRef<AuthSession | null>(null);

  const applySession = useCallback(async (nextSession: AuthSession): Promise<MeResponse> => {
    await saveAuthSession(nextSession);
    const nextUser = await meRequest(apiBaseUrl, nextSession.accessToken);
    sessionRef.current = nextSession;
    setSession(nextSession);
    setUser(nextUser);
    setStatus('authenticated');
    return nextUser;
  }, [apiBaseUrl]);

  const clearLocalSession = useCallback(async (): Promise<void> => {
    sessionRef.current = null;
    setSession(null);
    setUser(null);
    await clearAuthSession();
    setStatus('unauthenticated');
  }, []);

  const refreshSession = useCallback(async (): Promise<string> => {
    const current = sessionRef.current;
    if (!current) {
      await clearLocalSession();
      throw new MobileApiError(401, 'No session to refresh');
    }

    try {
      const tokens = await refreshRequest(apiBaseUrl, current.refreshToken);
      const nextSession = sessionFromTokenResponse(tokens);
      await applySession(nextSession);
      return nextSession.accessToken;
    } catch (error) {
      await clearLocalSession();
      throw error;
    }
  }, [apiBaseUrl, applySession, clearLocalSession]);

  useEffect(() => {
    let mounted = true;

    async function bootstrap(): Promise<void> {
      const stored = await loadAuthSession();
      if (!mounted) return;

      if (!stored) {
        setStatus('unauthenticated');
        return;
      }

      sessionRef.current = stored;

      try {
        const tokens = await refreshRequest(apiBaseUrl, stored.refreshToken);
        const nextSession = sessionFromTokenResponse(tokens);
        const nextUser = await applySession(nextSession);
        if (!mounted) return;
        setUser(nextUser);
      } catch {
        if (!mounted) return;
        await clearLocalSession();
      }
    }

    void bootstrap();
    return () => {
      mounted = false;
    };
  }, [apiBaseUrl, applySession, clearLocalSession]);

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    try {
      const tokens = await loginRequest(apiBaseUrl, { email, password });
      await applySession(sessionFromTokenResponse(tokens));
    } catch (error) {
      await clearLocalSession();
      throw error;
    }
  }, [apiBaseUrl, applySession, clearLocalSession]);

  const logout = useCallback(async (): Promise<void> => {
    const current = sessionRef.current;
    if (current) {
      await logoutRequest(apiBaseUrl, current.accessToken, current.refreshToken).catch(() => undefined);
    }
    await clearLocalSession();
  }, [apiBaseUrl, clearLocalSession]);

  const apiRequest = useCallback(async <T,>(
    path: string,
    options: MobileApiRequestOptions = {}
  ): Promise<T> => {
    const current = sessionRef.current;
    if (!current) {
      throw new MobileApiError(401, 'Not authenticated');
    }

    try {
      return await mobileApiRequest<T>(apiBaseUrl, path, {
        ...options,
        token: current.accessToken,
      });
    } catch (error) {
      if (error instanceof MobileApiError && error.status === 401) {
        const accessToken = await refreshSession();
        return mobileApiRequest<T>(apiBaseUrl, path, {
          ...options,
          token: accessToken,
        });
      }
      throw error;
    }
  }, [apiBaseUrl, refreshSession]);

  const value = useMemo<AuthContextValue>(() => ({
    status,
    session,
    user,
    apiBaseUrl,
    login,
    logout,
    refreshSession,
    apiRequest,
  }), [apiBaseUrl, apiRequest, login, logout, refreshSession, session, status, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return value;
}
