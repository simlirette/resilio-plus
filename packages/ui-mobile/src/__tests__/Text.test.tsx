import React from 'react';
import { renderWithTheme } from './helpers';
import { Text } from '../components/Text';

describe('Text', () => {
  it('renders default (body) variant without crash', () => {
    const { getByText } = renderWithTheme(<Text>Texte par défaut</Text>);
    expect(getByText('Texte par défaut')).toBeTruthy();
  });

  it('renders display variant', () => {
    const { getByText } = renderWithTheme(<Text variant="display">Titre affichage</Text>);
    expect(getByText('Titre affichage')).toBeTruthy();
  });

  it('renders title variant', () => {
    const { getByText } = renderWithTheme(<Text variant="title">Titre section</Text>);
    expect(getByText('Titre section')).toBeTruthy();
  });

  it('renders caption variant', () => {
    const { getByText } = renderWithTheme(<Text variant="caption">Légende</Text>);
    expect(getByText('Légende')).toBeTruthy();
  });

  it('renders mono variant', () => {
    const { getByText } = renderWithTheme(<Text variant="mono">01:30:00</Text>);
    expect(getByText('01:30:00')).toBeTruthy();
  });

  it('accepts color prop without crash', () => {
    const { getByText } = renderWithTheme(
      <Text color="#10b981">Texte coloré</Text>
    );
    expect(getByText('Texte coloré')).toBeTruthy();
  });

  it('accepts numberOfLines prop', () => {
    const { getByText } = renderWithTheme(
      <Text numberOfLines={2}>Texte tronqué</Text>
    );
    expect(getByText('Texte tronqué')).toBeTruthy();
  });

  it('all 5 variants render without crash', () => {
    const variants = ['display', 'title', 'body', 'caption', 'mono'] as const;
    for (const variant of variants) {
      expect(() =>
        renderWithTheme(<Text variant={variant}>{variant}</Text>)
      ).not.toThrow();
    }
  });
});
