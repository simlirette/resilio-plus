// Resilio+ tokens — warm neutrals, one accent, physiological semantics reserved.
// Never apply semantic green/yellow/red to non-physiological UI.

window.THEMES = {
  light: {
    bg:        '#F5F5F2',  // off-white, warm
    surface:   '#FAFAF7',  // cards / drawer
    surface2:  '#EDECE6',  // subtle block fill (completed day bg)
    hairline:  'rgba(26,25,22,0.08)',
    hairline2: 'rgba(26,25,22,0.04)',

    text:      '#1A1916',
    textSec:   '#6B6862',
    textTer:   '#9A968E',
    textQuad:  '#C2BEB6',

    accent:    '#A85A2F',  // warm amber-terracotta, used sparingly
    accentSoft:'rgba(168,90,47,0.10)',

    // Physiological palette — reserved
    physioGreen:  '#4F7A43',
    physioYellow: '#A68A2E',
    physioRed:    '#9C4A32',

    // Discipline marks — VALUE-based, not color-based
    // Run = solid dark, Lift = solid mid, Bike = outline, Swim = half
    disc: {
      run:  { fill: '#1A1916', stroke: '#1A1916', type: 'solid' },
      lift: { fill: '#6B6862', stroke: '#6B6862', type: 'solid' },
      bike: { fill: 'transparent', stroke: '#1A1916', type: 'outline' },
      swim: { fill: '#1A1916', stroke: '#1A1916', type: 'half' },
    },
  },
  dark: {
    bg:        '#1C1A17',  // warm charcoal — NOT #08080e
    surface:   '#242220',
    surface2:  '#2B2926',
    hairline:  'rgba(232,228,220,0.09)',
    hairline2: 'rgba(232,228,220,0.04)',

    text:      '#E8E4DC',
    textSec:   '#9A968E',
    textTer:   '#6B6862',
    textQuad:  '#3E3C38',

    accent:    '#D98E5E',
    accentSoft:'rgba(217,142,94,0.14)',

    physioGreen:  '#7FAD6B',
    physioYellow: '#D4B34D',
    physioRed:    '#C47A5A',

    disc: {
      run:  { fill: '#E8E4DC', stroke: '#E8E4DC', type: 'solid' },
      lift: { fill: '#9A968E', stroke: '#9A968E', type: 'solid' },
      bike: { fill: 'transparent', stroke: '#E8E4DC', type: 'outline' },
      swim: { fill: '#E8E4DC', stroke: '#E8E4DC', type: 'half' },
    },
  },
};
