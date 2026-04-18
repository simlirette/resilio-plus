import React from 'react';
import { renderWithTheme } from './helpers';
import { DisciplineIcon } from '../components/DisciplineIcon';
import type { SportType } from '../components/SessionCard';

describe('DisciplineIcon', () => {
  const sports: SportType[] = ['running', 'lifting', 'swimming', 'cycling', 'rest'];

  sports.forEach((sport) => {
    it(`renders without crash for sport=${sport}`, () => {
      expect(() =>
        renderWithTheme(<DisciplineIcon sport={sport} />)
      ).not.toThrow();
    });
  });

  it('accepts custom size', () => {
    expect(() =>
      renderWithTheme(<DisciplineIcon sport="running" size={24} />)
    ).not.toThrow();
  });

  it('accepts custom color', () => {
    expect(() =>
      renderWithTheme(<DisciplineIcon sport="lifting" color="#ff0000" />)
    ).not.toThrow();
  });
});
