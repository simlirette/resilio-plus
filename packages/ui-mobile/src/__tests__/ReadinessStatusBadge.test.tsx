import React from 'react';
import { renderWithTheme } from './helpers';
import { ReadinessStatusBadge } from '../components/ReadinessStatusBadge';

describe('ReadinessStatusBadge', () => {
  it('shows "Optimal" for value 80', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={80} />);
    expect(getByText('Optimal')).toBeTruthy();
  });

  it('shows "Optimal" for value 100', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={100} />);
    expect(getByText('Optimal')).toBeTruthy();
  });

  it('shows "Prudent" for value 79 (just below Optimal)', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={79} />);
    expect(getByText('Prudent')).toBeTruthy();
  });

  it('shows "Prudent" for value 60', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={60} />);
    expect(getByText('Prudent')).toBeTruthy();
  });

  it('shows "Repos recommandé" for value 59 (just below Prudent)', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={59} />);
    expect(getByText('Repos recommandé')).toBeTruthy();
  });

  it('shows "Repos recommandé" for value 0', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={0} />);
    expect(getByText('Repos recommandé')).toBeTruthy();
  });

  it('shows "Prudent" for value 65 (middle of yellow range)', () => {
    const { getByText } = renderWithTheme(<ReadinessStatusBadge value={65} />);
    expect(getByText('Prudent')).toBeTruthy();
  });
});
