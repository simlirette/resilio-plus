import React from 'react';
import { Text } from 'react-native';
import { renderWithTheme } from './helpers';
import { Screen } from '../components/Screen';

describe('Screen', () => {
  it('renders children without crash', () => {
    const { getByText } = renderWithTheme(
      <Screen>
        <Text>contenu écran</Text>
      </Screen>
    );
    expect(getByText('contenu écran')).toBeTruthy();
  });

  it('renders with scroll prop without crash', () => {
    const { getByText } = renderWithTheme(
      <Screen scroll>
        <Text>scrollable</Text>
      </Screen>
    );
    expect(getByText('scrollable')).toBeTruthy();
  });

  it('renders with padded prop without crash', () => {
    const { getByText } = renderWithTheme(
      <Screen padded>
        <Text>padded</Text>
      </Screen>
    );
    expect(getByText('padded')).toBeTruthy();
  });

  it('renders scroll + padded combination without crash', () => {
    const { getByText } = renderWithTheme(
      <Screen scroll padded>
        <Text>scroll padded</Text>
      </Screen>
    );
    expect(getByText('scroll padded')).toBeTruthy();
  });

  it('applies safe area insets (mocked as 0)', () => {
    // useSafeAreaInsets mock returns {top:0, bottom:0, left:0, right:0}
    // No crash = safe area context mock works
    expect(() =>
      renderWithTheme(
        <Screen>
          <Text>safe area ok</Text>
        </Screen>
      )
    ).not.toThrow();
  });
});
