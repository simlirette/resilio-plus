import React from 'react';
import { renderWithTheme } from './helpers';
import { CognitiveLoadDial } from '../components/CognitiveLoadDial';

describe('CognitiveLoadDial', () => {
  it('renders value 0 without crashing', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={0} state="green" />
    );
    expect(getByText('0')).toBeTruthy();
  });

  it('renders value 50 without crashing', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={50} state="yellow" />
    );
    expect(getByText('50')).toBeTruthy();
  });

  it('renders value 100 without crashing', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={100} state="red" />
    );
    expect(getByText('100')).toBeTruthy();
  });

  it('clamps value above 100 to 100', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={150} state="green" />
    );
    expect(getByText('100')).toBeTruthy();
  });

  it('clamps value below 0 to 0', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={-10} state="green" />
    );
    expect(getByText('0')).toBeTruthy();
  });

  it('renders optional label when provided', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={42} state="yellow" label="Charge allostatique" />
    );
    expect(getByText('Charge allostatique')).toBeTruthy();
  });

  it('renders without label when not provided', () => {
    const { queryByText } = renderWithTheme(
      <CognitiveLoadDial value={42} state="green" />
    );
    expect(queryByText('Charge allostatique')).toBeNull();
  });

  it('accepts custom size prop', () => {
    const { getByText } = renderWithTheme(
      <CognitiveLoadDial value={75} state="red" size={150} />
    );
    expect(getByText('75')).toBeTruthy();
  });
});
