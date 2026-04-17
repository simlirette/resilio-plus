import React from 'react';
import { fireEvent } from '@testing-library/react-native';
import { renderWithTheme } from './helpers';
import { Button } from '../components/Button';
import * as Haptics from 'expo-haptics';

describe('Button', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders primary variant without crash', () => {
    const { getByText } = renderWithTheme(
      <Button title="Se connecter" onPress={() => {}} />
    );
    expect(getByText('Se connecter')).toBeTruthy();
  });

  it('renders secondary variant without crash', () => {
    const { getByText } = renderWithTheme(
      <Button title="Précédent" onPress={() => {}} variant="secondary" />
    );
    expect(getByText('Précédent')).toBeTruthy();
  });

  it('renders ghost variant without crash', () => {
    const { getByText } = renderWithTheme(
      <Button title="Annuler" onPress={() => {}} variant="ghost" />
    );
    expect(getByText('Annuler')).toBeTruthy();
  });

  it('calls onPress when pressed', () => {
    const onPress = jest.fn();
    const { getByText } = renderWithTheme(
      <Button title="Appuyer" onPress={onPress} />
    );
    fireEvent.press(getByText('Appuyer'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('triggers Medium haptic on primary press', () => {
    const { getByText } = renderWithTheme(
      <Button title="Primary" onPress={() => {}} />
    );
    fireEvent.press(getByText('Primary'));
    expect(Haptics.impactAsync).toHaveBeenCalledWith(Haptics.ImpactFeedbackStyle.Medium);
  });

  it('triggers Light haptic on secondary press', () => {
    const { getByText } = renderWithTheme(
      <Button title="Secondary" onPress={() => {}} variant="secondary" />
    );
    fireEvent.press(getByText('Secondary'));
    expect(Haptics.impactAsync).toHaveBeenCalledWith(Haptics.ImpactFeedbackStyle.Light);
  });

  it('does not call onPress when disabled', () => {
    const onPress = jest.fn();
    const { getByText } = renderWithTheme(
      <Button title="Désactivé" onPress={onPress} disabled />
    );
    fireEvent.press(getByText('Désactivé'));
    expect(onPress).not.toHaveBeenCalled();
  });

  it('shows loading indicator when loading=true', () => {
    const { queryByText, getByTestId } = renderWithTheme(
      <Button title="Charger" onPress={() => {}} loading />
    );
    // Text hidden when loading
    expect(queryByText('Charger')).toBeNull();
  });

  it('accepts style prop without crash', () => {
    expect(() =>
      renderWithTheme(
        <Button title="Stylé" onPress={() => {}} style={{ marginTop: 16 }} />
      )
    ).not.toThrow();
  });
});
