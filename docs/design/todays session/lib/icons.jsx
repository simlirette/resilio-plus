// icons.jsx — minimal monoline iconography. 1.5px stroke, no fills, no decoration.

const Ico = {
  back: (c) => (
    <svg width="11" height="18" viewBox="0 0 11 18" fill="none">
      <path d="M9 1L2 9l7 8" stroke={c} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  dots: (c) => (
    <svg width="20" height="4" viewBox="0 0 20 4">
      <circle cx="2" cy="2" r="1.6" fill={c}/>
      <circle cx="10" cy="2" r="1.6" fill={c}/>
      <circle cx="18" cy="2" r="1.6" fill={c}/>
    </svg>
  ),
  // sport glyphs — abstract, not character art
  run: (c, size = 22) => (
    <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
      <path d="M3 19 L8 13 L10 15 L14 10 L19 13" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="14" cy="4.5" r="2" stroke={c} strokeWidth="1.5"/>
    </svg>
  ),
  lift: (c, size = 22) => (
    <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
      <rect x="1.5" y="8.5" width="2" height="5" rx="0.5" stroke={c} strokeWidth="1.5"/>
      <rect x="18.5" y="8.5" width="2" height="5" rx="0.5" stroke={c} strokeWidth="1.5"/>
      <rect x="4.5" y="6" width="2" height="10" rx="0.5" stroke={c} strokeWidth="1.5"/>
      <rect x="15.5" y="6" width="2" height="10" rx="0.5" stroke={c} strokeWidth="1.5"/>
      <line x1="6.5" y1="11" x2="15.5" y2="11" stroke={c} strokeWidth="1.5"/>
    </svg>
  ),
  bike: (c, size = 22) => (
    <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
      <circle cx="5" cy="15" r="4" stroke={c} strokeWidth="1.5"/>
      <circle cx="17" cy="15" r="4" stroke={c} strokeWidth="1.5"/>
      <path d="M5 15 L10 8 L15 15 M10 8 L13 8 M14 4 L17 4 L17 15" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  swim: (c, size = 22) => (
    <svg width={size} height={size} viewBox="0 0 22 22" fill="none">
      <path d="M2 14 Q5.5 11 9 14 T16 14 T22 14" stroke={c} strokeWidth="1.5" strokeLinecap="round" fill="none" transform="translate(-1 0)"/>
      <path d="M2 18 Q5.5 15 9 18 T16 18 T22 18" stroke={c} strokeWidth="1.5" strokeLinecap="round" fill="none" transform="translate(-1 0)"/>
      <circle cx="15" cy="5" r="1.8" stroke={c} strokeWidth="1.5"/>
      <path d="M13 7 L10 10" stroke={c} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  pause: (c, size = 16) => (
    <svg width={size} height={size} viewBox="0 0 16 16">
      <rect x="4" y="3" width="2.5" height="10" rx="0.5" fill={c}/>
      <rect x="9.5" y="3" width="2.5" height="10" rx="0.5" fill={c}/>
    </svg>
  ),
  play: (c, size = 14) => (
    <svg width={size} height={size} viewBox="0 0 14 14">
      <path d="M3 2 L12 7 L3 12 Z" fill={c}/>
    </svg>
  ),
  check: (c, size = 14) => (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path d="M2 7.5 L5.5 11 L12 3.5" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  heart: (c, size = 14) => (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none">
      <path d="M7 12 C 7 12 1.5 8.5 1.5 5 C 1.5 3.3 2.8 2 4.5 2 C 5.7 2 6.5 2.7 7 3.5 C 7.5 2.7 8.3 2 9.5 2 C 11.2 2 12.5 3.3 12.5 5 C 12.5 8.5 7 12 7 12 Z" stroke={c} strokeWidth="1.3" strokeLinejoin="round"/>
    </svg>
  ),
  arrowTiny: (c) => (
    <svg width="7" height="12" viewBox="0 0 7 12" fill="none">
      <path d="M1 1l5 5-5 5" stroke={c} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
};

function SportIcon({ sport, color, size }) {
  const map = { run: Ico.run, lift: Ico.lift, bike: Ico.bike, swim: Ico.swim };
  return (map[sport] || Ico.run)(color, size);
}

Object.assign(window, { Ico, SportIcon });
