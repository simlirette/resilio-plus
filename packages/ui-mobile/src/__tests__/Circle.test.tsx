import React from 'react';
import { renderWithTheme } from './helpers';
import { Circle } from '../components/Circle';

describe('Circle', () => {
  it('renders value=0 without crash', () => {
    const { getByText } = renderWithTheme(
      <Circle value={0} color="#10b981" />
    );
    expect(getByText('0')).toBeTruthy();
  });

  it('renders value=50 without crash', () => {
    const { getByText } = renderWithTheme(
      <Circle value={50} color="#f59e0b" />
    );
    expect(getByText('50')).toBeTruthy();
  });

  it('renders value=100 without crash', () => {
    const { getByText } = renderWithTheme(
      <Circle value={100} color="#10b981" />
    );
    expect(getByText('100')).toBeTruthy();
  });

  it('clamps value above 100 to 100', () => {
    const { getByText } = renderWithTheme(
      <Circle value={150} color="#ef4444" />
    );
    expect(getByText('100')).toBeTruthy();
  });

  it('clamps value below 0 to 0', () => {
    const { getByText } = renderWithTheme(
      <Circle value={-10} color="#ef4444" />
    );
    expect(getByText('0')).toBeTruthy();
  });

  it('renders with label', () => {
    const { getByText } = renderWithTheme(
      <Circle value={75} color="#10b981" label="Forme" />
    );
    expect(getByText('75')).toBeTruthy();
    expect(getByText('Forme')).toBeTruthy();
  });

  it('renders without label (no crash)', () => {
    expect(() =>
      renderWithTheme(<Circle value={60} color="#B8552E" />)
    ).not.toThrow();
  });

  it('renders with custom size', () => {
    expect(() =>
      renderWithTheme(<Circle value={80} color="#10b981" size={120} />)
    ).not.toThrow();
  });
});
