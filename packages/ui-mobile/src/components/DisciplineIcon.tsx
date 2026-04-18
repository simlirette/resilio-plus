import React from 'react';
import { IconComponent } from '../Icon';
import type { IconName } from '../Icon';
import type { SportType } from './SessionCard';

interface DisciplineIconProps {
  sport: SportType;
  size?: number;
  color?: string;
}

const SPORT_ICON: Record<SportType, IconName> = {
  running:  'Activity',
  lifting:  'Lifting',
  swimming: 'Swimming',
  cycling:  'Biking',
  rest:     'DarkMode',
};

export function DisciplineIcon({ sport, size = 18, color }: DisciplineIconProps): React.JSX.Element {
  return (
    <IconComponent
      name={SPORT_ICON[sport] ?? 'Activity'}
      size={size}
      color={color}
    />
  );
}
