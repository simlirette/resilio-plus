/**
 * Home screen tests.
 * All tests use jest-expo via apps/mobile/jest.regression.config.js — Node env only.
 * useHomeData is mocked to inject specific scenarios.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { ThemeProvider } from '@resilio/ui-mobile';

// Mock expo-router
jest.mock('expo-router', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
}));

// Mock expo-haptics
jest.mock('expo-haptics', () => ({
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  NotificationFeedbackType: { Success: 'success' },
  impactAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Medium: 'medium', Light: 'light' },
}));

// Mock react-native-safe-area-context
jest.mock('react-native-safe-area-context', () => ({
  useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
}));

// Mock useHomeData — default returns green scenario
const mockRefresh = jest.fn().mockResolvedValue(undefined);
const mockGreen = {
  data: {
    readiness: { value: 82, state: 'green' as const, trend: 'improving' as const, objective_score: 85, subjective_score: 78 },
    nutrition:     { value: 74, state: 'green' as const },
    strain:        { value: 38, state: 'green' as const },
    sleep:         { value: 88, state: 'green' as const, sleep_hours: 7.5 },
    cognitiveLoad: { value: 28, state: 'green' as const },
    acwrStatus: 'safe' as const,
    todaysSessions: [{
      sport: 'running' as const,
      title: 'Easy Run Z1',
      duration_min: 45,
      zone: 'Zone 1 (60–74% FCmax)',
      is_rest_day: false,
    }],
  },
  loading: false,
  refresh: mockRefresh,
  lastRefreshedAt: new Date('2026-04-17'),
};

const mockYellow = {
  ...mockGreen,
  data: {
    ...mockGreen.data,
    readiness: { value: 61, state: 'yellow' as const, trend: 'stable' as const, objective_score: 58, subjective_score: 65 },
  },
};

const mockRestDay = {
  ...mockGreen,
  data: {
    ...mockGreen.data,
    readiness: { value: 72, state: 'green' as const, trend: 'stable' as const, objective_score: 70, subjective_score: null },
    todaysSessions: null,
  },
};

const mockLowReadiness = {
  ...mockGreen,
  data: {
    ...mockGreen.data,
    readiness: { value: 42, state: 'red' as const, trend: 'declining' as const, objective_score: 40, subjective_score: 45 },
  },
};

const mockUseHomeData = jest.fn().mockReturnValue(mockGreen);

jest.mock('../../../src/hooks/useHomeData', () => ({
  useHomeData: (...args: unknown[]) => mockUseHomeData(...args),
}));

function renderHome() {
  // Dynamic require to pick up the mock
  const HomeScreen = require('../index').default as React.ComponentType;
  return render(
    <ThemeProvider>
      <HomeScreen />
    </ThemeProvider>
  );
}

describe('HomeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHomeData.mockReturnValue(mockGreen);
  });

  it('renders without crashing (green scenario)', () => {
    const { getByText } = renderHome();
    expect(getByText('Bonjour,')).toBeTruthy();
  });

  it('does NOT show rest banner when readiness >= 50 (green scenario)', () => {
    const { queryByText } = renderHome();
    expect(queryByText(/Repos recommandé — ton score de forme/)).toBeNull();
  });

  it('shows rest banner when readiness < 50', () => {
    mockUseHomeData.mockReturnValue(mockLowReadiness);
    const { getByText } = renderHome();
    expect(getByText('Repos recommandé — ton score de forme est bas')).toBeTruthy();
  });

  it('does NOT show rest banner for yellow scenario (readiness = 61)', () => {
    mockUseHomeData.mockReturnValue(mockYellow);
    const { queryByText } = renderHome();
    expect(queryByText(/Repos recommandé — ton score de forme/)).toBeNull();
  });

  it('renders session title for normal session', () => {
    const { getByText } = renderHome();
    expect(getByText('Easy Run Z1')).toBeTruthy();
  });

  it('renders "Repos programmé" for rest day (null sessions)', () => {
    mockUseHomeData.mockReturnValue(mockRestDay);
    const { getByText } = renderHome();
    expect(getByText('Repos programmé — aucune séance aujourd\'hui')).toBeTruthy();
  });

  it('renders CTA button', () => {
    const { getByText } = renderHome();
    expect(getByText('Check-in quotidien')).toBeTruthy();
  });

  it('renders greeting text', () => {
    const { getByText } = renderHome();
    expect(getByText('Résumé de coaching du jour')).toBeTruthy();
  });

  it('renders charge allostatique label', () => {
    const { getByText } = renderHome();
    expect(getByText('Charge allostatique')).toBeTruthy();
  });
});
