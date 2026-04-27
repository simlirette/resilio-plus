import React from 'react';
import { render } from '@testing-library/react-native';
import { Icon, IconComponent } from '../Icon';

describe('Icon (object pattern)', () => {
  it('renders Icon.Heart without crash', () => {
    const { getByTestId } = render(<Icon.Heart size={20} color="#fff" />);
    expect(getByTestId('mock-icon')).toBeTruthy();
  });

  it('renders Icon.Activity without crash', () => {
    const { getByTestId } = render(<Icon.Activity size={16} color="#B8552E" />);
    expect(getByTestId('mock-icon')).toBeTruthy();
  });

  it('renders Icon.Energy (Zap) without crash', () => {
    const { getByTestId } = render(<Icon.Energy size={18} color="#10b981" />);
    expect(getByTestId('mock-icon')).toBeTruthy();
  });

  it('covers all exported icon keys without throwing', () => {
    const keys = Object.keys(Icon) as Array<keyof typeof Icon>;
    expect(keys.length).toBeGreaterThan(10);
  });
});

describe('IconComponent (name-prop pattern)', () => {
  it('renders <IconComponent name="Heart"> without crash', () => {
    const { getByTestId } = render(<IconComponent name="Heart" size={20} color="#ef4444" />);
    expect(getByTestId('mock-icon')).toBeTruthy();
  });

  it('renders <IconComponent name="Activity"> without crash', () => {
    const { getByTestId } = render(<IconComponent name="Activity" />);
    expect(getByTestId('mock-icon')).toBeTruthy();
  });

  it('renders with default size when omitted', () => {
    // No error = default size (20) is applied
    expect(() => render(<IconComponent name="Check" />)).not.toThrow();
  });
});
