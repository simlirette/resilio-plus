import React from 'react';
import { renderWithTheme } from './helpers';
import { ProgressDots } from '../components/ProgressDots';

describe('ProgressDots', () => {
  it('renders correct number of segments', () => {
    const { getAllByTestId } = renderWithTheme(
      <ProgressDots step={0} total={5} />
    );
    expect(getAllByTestId('progress-dot')).toHaveLength(5);
  });

  it('renders with default total=5', () => {
    const { getAllByTestId } = renderWithTheme(
      <ProgressDots step={2} />
    );
    expect(getAllByTestId('progress-dot')).toHaveLength(5);
  });

  it('renders custom total', () => {
    const { getAllByTestId } = renderWithTheme(
      <ProgressDots step={1} total={3} />
    );
    expect(getAllByTestId('progress-dot')).toHaveLength(3);
  });

  it('renders without crash at step 0', () => {
    expect(() => renderWithTheme(<ProgressDots step={0} />)).not.toThrow();
  });

  it('renders without crash at last step', () => {
    expect(() => renderWithTheme(<ProgressDots step={4} total={5} />)).not.toThrow();
  });
});
