import React from 'react';
import { renderWithTheme } from './helpers';
import { SessionCard } from '../components/SessionCard';
import type { WorkoutSlotForCard } from '../components/SessionCard';

const baseSession: WorkoutSlotForCard = {
  sport: 'running',
  title: 'Easy Run Z1',
  duration_min: 45,
  zone: 'Zone 1 (60–74% FCmax)',
  is_rest_day: false,
};

describe('SessionCard', () => {
  it('renders rest state when session is null', () => {
    const { getByText } = renderWithTheme(<SessionCard session={null} />);
    expect(getByText('Repos programmé — aucune séance aujourd\'hui')).toBeTruthy();
  });

  it('renders active rest when is_rest_day is true', () => {
    const session: WorkoutSlotForCard = { ...baseSession, is_rest_day: true };
    const { getByText } = renderWithTheme(<SessionCard session={session} />);
    expect(getByText('Repos actif — récupération')).toBeTruthy();
  });

  it('renders session title for normal session', () => {
    const { getByText } = renderWithTheme(<SessionCard session={baseSession} />);
    expect(getByText('Easy Run Z1')).toBeTruthy();
  });

  it('renders meta line with duration and zone', () => {
    const { getByText } = renderWithTheme(<SessionCard session={baseSession} />);
    expect(getByText('45 min · Zone 1 (60–74% FCmax)')).toBeTruthy();
  });

  it('renders zone badge abbreviated (Z1 format)', () => {
    const { getByText } = renderWithTheme(<SessionCard session={baseSession} />);
    expect(getByText('Z1')).toBeTruthy();
  });

  it('renders lifting session title', () => {
    const session: WorkoutSlotForCard = { ...baseSession, sport: 'lifting', title: 'Upper Pull' };
    const { getByText } = renderWithTheme(<SessionCard session={session} />);
    expect(getByText('Upper Pull')).toBeTruthy();
  });

  it('renders swimming session title', () => {
    const session: WorkoutSlotForCard = { ...baseSession, sport: 'swimming', title: 'Endurance Natation' };
    const { getByText } = renderWithTheme(<SessionCard session={session} />);
    expect(getByText('Endurance Natation')).toBeTruthy();
  });

  it('renders cycling session title', () => {
    const session: WorkoutSlotForCard = { ...baseSession, sport: 'cycling', title: 'Zone 2 Vélo' };
    const { getByText } = renderWithTheme(<SessionCard session={session} />);
    expect(getByText('Zone 2 Vélo')).toBeTruthy();
  });

  it('shows section label on all variants', () => {
    const { getAllByText } = renderWithTheme(<SessionCard session={null} />);
    expect(getAllByText('Séance du jour').length).toBeGreaterThan(0);
  });
});
