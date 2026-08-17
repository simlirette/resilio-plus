import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TappableOptions } from '@resilio/ui-web';

describe('TappableOptions', () => {
  it('renders all axes as buttons', () => {
    render(
      <TappableOptions
        axes={['Plan de course', 'Nutrition', 'Récupération']}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText('Plan de course')).toBeDefined();
    expect(screen.getByText('Nutrition')).toBeDefined();
    expect(screen.getByText('Récupération')).toBeDefined();
  });

  it('calls onSelect with the clicked axis', () => {
    const onSelect = vi.fn();
    render(
      <TappableOptions
        axes={['Option A', 'Option B']}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText('Option A'));
    expect(onSelect).toHaveBeenCalledWith('Option A');
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it('disappears after one selection', () => {
    render(
      <TappableOptions
        axes={['Axe 1', 'Axe 2']}
        onSelect={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText('Axe 1'));
    // After click, options should no longer be rendered
    expect(screen.queryByText('Axe 1')).toBeNull();
    expect(screen.queryByText('Axe 2')).toBeNull();
  });
});
