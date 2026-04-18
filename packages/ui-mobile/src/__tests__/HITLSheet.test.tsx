import React from 'react';
import { fireEvent } from '@testing-library/react-native';
import { renderWithTheme } from './helpers';
import { HITLSheet } from '../components/HITLSheet';

const OPTIONS = [
  { id: 'a', label: 'Option A', description: 'Desc A' },
  { id: 'b', label: 'Option B' },
];

describe('HITLSheet', () => {
  it('renders title when visible', () => {
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="Choisir" options={OPTIONS} onSelect={() => {}} onDismiss={() => {}} />
    );
    expect(getByText('Choisir')).toBeTruthy();
  });

  it('renders all option labels', () => {
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="T" options={OPTIONS} onSelect={() => {}} onDismiss={() => {}} />
    );
    expect(getByText('Option A')).toBeTruthy();
    expect(getByText('Option B')).toBeTruthy();
  });

  it('calls onSelect with option id when pressed', () => {
    const onSelect = jest.fn();
    const onDismiss = jest.fn();
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="T" options={OPTIONS} onSelect={onSelect} onDismiss={onDismiss} />
    );
    fireEvent.press(getByText('Option A'));
    expect(onSelect).toHaveBeenCalledWith('a');
    expect(onDismiss).toHaveBeenCalled();
  });

  it('calls onDismiss when Annuler pressed', () => {
    const onDismiss = jest.fn();
    const { getByText } = renderWithTheme(
      <HITLSheet visible title="T" options={OPTIONS} onSelect={() => {}} onDismiss={onDismiss} />
    );
    fireEvent.press(getByText('Annuler'));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('renders without crash when not visible', () => {
    expect(() =>
      renderWithTheme(
        <HITLSheet visible={false} title="T" options={OPTIONS} onSelect={() => {}} onDismiss={() => {}} />
      )
    ).not.toThrow();
  });
});
