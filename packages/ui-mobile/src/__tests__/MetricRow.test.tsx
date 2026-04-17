import React from 'react';
import { renderWithTheme } from './helpers';
import { MetricRow } from '../components/MetricRow';

describe('MetricRow', () => {
  const allGreen = {
    nutrition: { value: 74, state: 'green' as const },
    strain:    { value: 38, state: 'green' as const },
    sleep:     { value: 88, state: 'green' as const },
  };

  it('renders all three section labels', () => {
    const { getByText } = renderWithTheme(<MetricRow {...allGreen} />);
    expect(getByText('Nutrition')).toBeTruthy();
    expect(getByText('Strain')).toBeTruthy();
    expect(getByText('Sommeil')).toBeTruthy();
  });

  it('renders with mixed states', () => {
    const mixed = {
      nutrition: { value: 52, state: 'yellow' as const },
      strain:    { value: 85, state: 'red' as const },
      sleep:     { value: 69, state: 'yellow' as const },
    };
    const { getByText } = renderWithTheme(<MetricRow {...mixed} />);
    expect(getByText('Nutrition')).toBeTruthy();
  });

  it('renders red state for high strain', () => {
    const redStrain = {
      nutrition: { value: 80, state: 'green' as const },
      strain:    { value: 85, state: 'red' as const },
      sleep:     { value: 76, state: 'green' as const },
    };
    const { getByText } = renderWithTheme(<MetricRow {...redStrain} />);
    expect(getByText('85')).toBeTruthy();
    expect(getByText('Strain')).toBeTruthy();
  });

  it('renders values inside circles', () => {
    const { getByText } = renderWithTheme(<MetricRow {...allGreen} />);
    expect(getByText('74')).toBeTruthy();
    expect(getByText('38')).toBeTruthy();
    expect(getByText('88')).toBeTruthy();
  });
});
