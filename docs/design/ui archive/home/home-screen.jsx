// Resilio+ Home screen — hybrid athlete wellness dashboard
// Clinical + warm. Light/dark parity. Accent color via --accent CSS var.

// ─────────────────────────────────────────────────────────────
// Theme tokens — warm off-white / warm near-black
// ─────────────────────────────────────────────────────────────
const themeTokens = (dark) => dark ? {
  bg:        '#131210',                           // warm near-black
  surface:   '#1C1B18',                           // card
  surface2:  '#232120',                           // inner metric
  text:      '#EDE9E2',                           // warm off-white
  textSec:   'rgba(237,233,226,0.62)',
  textTer:   'rgba(237,233,226,0.38)',
  hairline:  'rgba(237,233,226,0.08)',
  track:     'rgba(237,233,226,0.08)',
  shadow:    '0 1px 2px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.25)',
  // semantic — muted/desaturated warm
  warn:      '#D6A24A',   // warm amber (nutrition caution)
  ok:        '#7DA66A',   // sage green
  okStrong:  '#6B9259',   // darker sage for sleep
  caution:   '#C79140',   // prudent state
  btnText:   '#131210',
} : {
  bg:        '#F7F4EE',                           // warm off-white
  surface:   '#FDFBF7',                           // card
  surface2:  '#F3EFE8',
  text:      '#2B2824',                           // warm charcoal
  textSec:   'rgba(43,40,36,0.62)',
  textTer:   'rgba(43,40,36,0.38)',
  hairline:  'rgba(43,40,36,0.08)',
  track:     'rgba(43,40,36,0.08)',
  shadow:    '0 1px 2px rgba(43,28,0,0.04), 0 8px 24px rgba(43,28,0,0.06)',
  warn:      '#B8863A',
  ok:        '#6B9259',
  okStrong:  '#5C8250',
  caution:   '#A6762E',
  btnText:   '#FDFBF7',
};

// accent choices — muted, premium
const ACCENTS = {
  clinical:  '#3B74C9',   // apple-health-like blue, desaturated
  emerald:   '#2F7D5B',   // emerald green, clinical
  indigo:    '#5B5BAF',   // soft indigo
};

// ─────────────────────────────────────────────────────────────
// Building blocks
// ─────────────────────────────────────────────────────────────
function Card({ children, t, style = {} }) {
  return (
    <div style={{
      background: t.surface,
      borderRadius: 22,
      boxShadow: t.shadow,
      border: `0.5px solid ${t.hairline}`,
      ...style,
    }}>{children}</div>
  );
}

// big center readiness ring
function ReadinessRing({ value = 72, t, accent }) {
  const size = 216;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = value / 100;
  // readiness color gradient breakpoints — use caution for 60-75
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '8px 0 4px',
    }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          {/* track */}
          <circle cx={size/2} cy={size/2} r={r}
            fill="none" stroke={t.track} strokeWidth={stroke}/>
          {/* value */}
          <circle cx={size/2} cy={size/2} r={r}
            fill="none" stroke={accent} strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${c*pct} ${c}`}/>
        </svg>
        {/* center stack */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase',
            color: t.textTer, fontWeight: 500, marginBottom: 4,
          }}>Readiness</div>
          <div style={{
            fontSize: 72, fontWeight: 300, color: t.text,
            fontVariantNumeric: 'tabular-nums', lineHeight: 1,
            letterSpacing: -2,
          }}>{value}</div>
        </div>
      </div>
      {/* state badge */}
      <div style={{
        marginTop: 18, display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '6px 14px 6px 12px',
        background: t.surface,
        border: `0.5px solid ${t.hairline}`,
        borderRadius: 999,
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: t.caution,
        }}/>
        <span style={{
          fontSize: 13, fontWeight: 500, color: t.text, letterSpacing: -0.1,
        }}>Prudent</span>
      </div>
    </div>
  );
}

// small metric ring (nutrition / strain / sommeil)
function MetricRing({ label, value, color, t }) {
  const size = 68;
  const stroke = 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = value / 100;
  return (
    <div style={{
      flex: 1,
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      gap: 10, padding: '16px 4px 14px',
    }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size/2} cy={size/2} r={r}
            fill="none" stroke={t.track} strokeWidth={stroke}/>
          <circle cx={size/2} cy={size/2} r={r}
            fill="none" stroke={color} strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${c*pct} ${c}`}/>
        </svg>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, fontWeight: 500, color: t.text,
          fontVariantNumeric: 'tabular-nums', letterSpacing: -0.5,
        }}>{value}</div>
      </div>
      <div style={{
        fontSize: 12, color: t.textSec, letterSpacing: 0.1,
      }}>{label}</div>
    </div>
  );
}

// semi-arc dial for allostatic load
function AllostaticDial({ value = 28, t, accent }) {
  const w = 180, h = 96;
  const cx = w/2, cy = h - 6;
  const r = 76;
  const stroke = 9;
  // arc from 180deg (left) to 0deg (right)
  const arcPath = (start, end) => {
    const s = (Math.PI - start * Math.PI);
    const e = (Math.PI - end * Math.PI);
    const x1 = cx + r * Math.cos(s);
    const y1 = cy - r * Math.sin(s);
    const x2 = cx + r * Math.cos(e);
    const y2 = cy - r * Math.sin(e);
    return `M ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2}`;
  };
  const pct = value / 100;
  return (
    <div style={{ position: 'relative', width: w, height: h }}>
      <svg width={w} height={h}>
        {/* track */}
        <path d={arcPath(0, 1)} stroke={t.track} strokeWidth={stroke}
          fill="none" strokeLinecap="round"/>
        {/* tick marks to evoke clinical dial */}
        {[0.25, 0.5, 0.75].map(p => {
          const a = Math.PI - p * Math.PI;
          const x1 = cx + (r - stroke/2 - 2) * Math.cos(a);
          const y1 = cy - (r - stroke/2 - 2) * Math.sin(a);
          const x2 = cx + (r + stroke/2 + 2) * Math.cos(a);
          const y2 = cy - (r + stroke/2 + 2) * Math.sin(a);
          return <line key={p} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={t.hairline} strokeWidth={1}/>;
        })}
        <path d={arcPath(0, pct)} stroke={accent} strokeWidth={stroke}
          fill="none" strokeLinecap="round"/>
      </svg>
      {/* value centered under arc */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
      }}>
        <div style={{
          fontSize: 38, fontWeight: 300, color: t.text,
          fontVariantNumeric: 'tabular-nums', letterSpacing: -1.2,
          lineHeight: 1,
        }}>{value}</div>
        <div style={{
          fontSize: 10, letterSpacing: 0.6, color: t.textTer,
          textTransform: 'uppercase', marginTop: 4, fontWeight: 500,
        }}>/ 100</div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Bottom tab bar — Home, Check-in, Sessions, Health
// Filled iconography, label below. Active item sits in a soft pill.
// ─────────────────────────────────────────────────────────────
const TAB_ICONS = {
  home: (c) => (
    <svg width="22" height="22" viewBox="0 0 22 22" fill={c}>
      <path d="M11 2.3L2.5 9.2c-.3.3-.5.7-.5 1.1V19a1 1 0 001 1h5v-6a2 2 0 012-2h2a2 2 0 012 2v6h5a1 1 0 001-1v-8.7c0-.4-.2-.8-.5-1.1L11 2.3z"/>
    </svg>
  ),
  agenda: (c) => (
    <svg width="22" height="22" viewBox="0 0 22 22" fill={c}>
      <rect x="3.5" y="5" width="15" height="14" rx="2.5"/>
      <rect x="6" y="2.5" width="1.8" height="4" rx="0.9" fill={c}/>
      <rect x="14.2" y="2.5" width="1.8" height="4" rx="0.9" fill={c}/>
      <rect x="3.5" y="5" width="15" height="3.5" fill={c} opacity="0.6"/>
      <circle cx="8" cy="12.5" r="1.1" fill="#fff"/>
      <circle cx="11" cy="12.5" r="1.1" fill="#fff"/>
      <circle cx="14" cy="12.5" r="1.1" fill="#fff"/>
      <circle cx="8" cy="15.5" r="1.1" fill="#fff"/>
      <circle cx="11" cy="15.5" r="1.1" fill="#fff"/>
    </svg>
  ),
  coach: (c) => (
    <svg width="22" height="22" viewBox="0 0 22 22" fill={c}>
      {/* speech bubble with spark — AI coach */}
      <path d="M4 4h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-3.2 3a.7.7 0 01-1.2-.5V16H4a2 2 0 01-2-2V6a2 2 0 012-2z"/>
      <path d="M11 6.5l1 2.3 2.3 1-2.3 1-1 2.3-1-2.3-2.3-1 2.3-1z" fill="#fff"/>
    </svg>
  ),
  sessions: (c) => (
    <svg width="22" height="22" viewBox="0 0 22 22" fill={c}>
      <circle cx="15" cy="4.5" r="2"/>
      <path d="M13.5 8.2l-2.7 1.6c-.5.3-.8.8-.8 1.4v3.3l-2.6 3.7c-.3.4-.2 1 .2 1.3.4.3 1 .2 1.3-.2l2.9-4.1c.1-.2.2-.4.2-.6V11l1.6-.9 1.3 2.6c.1.3.4.5.7.6l2.9.7c.5.1 1-.2 1.1-.7.1-.5-.2-1-.7-1.1l-2.5-.6-1.9-3.8c-.3-.5-.9-.7-1.3-.4-.1 0-.1.1-.2.1z"/>
      <path d="M7 8.5l-1.7.6L4 7c-.2-.3-.5-.5-.9-.5-.5 0-1 .4-1 1 0 .1 0 .3.1.4l1.8 3c.2.3.6.5 1 .4l2-.6c.5-.2.8-.7.6-1.2-.1-.5-.6-.8-1.1-.7z"/>
    </svg>
  ),
  health: (c) => (
    <svg width="22" height="22" viewBox="0 0 22 22" fill={c}>
      <path d="M11 19.5s-7.5-4.3-7.5-10a4.5 4.5 0 018.1-2.7l.4.5.4-.5A4.5 4.5 0 0118.5 9.5c0 5.7-7.5 10-7.5 10z" opacity="0.25"/>
      <path d="M3.5 10.5h3l1.5-3 2 5 1.5-3h7" stroke={c} strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
};

function TabBar({ active = 'home', t, accent, dark }) {
  const tabs = [
    { key: 'home',     label: 'Home' },
    { key: 'agenda',   label: 'Agenda' },
    { key: 'coach',    label: 'Coach' },
    { key: 'sessions', label: 'Sessions' },
    { key: 'health',   label: 'Health' },
  ];
  return (
    <div style={{
      position: 'absolute', left: 14, right: 14, bottom: 28,
      height: 66, borderRadius: 33,
      overflow: 'hidden',
      boxShadow: dark
        ? '0 2px 6px rgba(0,0,0,0.4), 0 12px 36px rgba(0,0,0,0.35)'
        : '0 1px 3px rgba(43,28,0,0.06), 0 10px 30px rgba(43,28,0,0.10)',
    }}>
      {/* 1 — blur + tint layer */}
      <div style={{
        position: 'absolute', inset: 0,
        backdropFilter: 'blur(22px) saturate(180%)',
        WebkitBackdropFilter: 'blur(22px) saturate(180%)',
        background: dark
          ? 'rgba(40,38,36,0.55)'
          : 'rgba(253,251,247,0.62)',
      }} />
      {/* 2 — inner highlight + hairline edge (liquid glass shine) */}
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 33,
        boxShadow: dark
          ? 'inset 1px 1px 0.5px rgba(255,255,255,0.18), inset -1px -1px 0.5px rgba(255,255,255,0.06)'
          : 'inset 1px 1px 0.5px rgba(255,255,255,0.9), inset -1px -1px 0.5px rgba(255,255,255,0.5)',
        border: dark ? '0.5px solid rgba(255,255,255,0.14)' : '0.5px solid rgba(43,40,36,0.08)',
        pointerEvents: 'none',
      }} />
      {/* 3 — soft top gradient sheen */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '55%',
        background: dark
          ? 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0))'
          : 'linear-gradient(180deg, rgba(255,255,255,0.55), rgba(255,255,255,0))',
        pointerEvents: 'none',
      }} />

      {/* tabs */}
      <div style={{
        position: 'relative', display: 'flex',
        height: '100%', padding: '0 6px',
        alignItems: 'center', justifyContent: 'space-around',
      }}>
        {tabs.map(tab => {
          const isActive = tab.key === active;
          const c = isActive ? accent : t.textSec;
          return (
            <div key={tab.key} style={{
              position: 'relative',
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', gap: 3,
              padding: '8px 8px', borderRadius: 22,
              minWidth: 52,
            }}>
              {/* active pill — inner glass bubble */}
              {isActive && (
                <>
                  <div style={{
                    position: 'absolute', inset: 0, borderRadius: 22,
                    background: dark
                      ? `${accent}22`
                      : `${accent}14`,
                    border: `0.5px solid ${accent}33`,
                    boxShadow: dark
                      ? 'inset 1px 1px 0 rgba(255,255,255,0.08)'
                      : 'inset 1px 1px 0 rgba(255,255,255,0.6)',
                  }}/>
                </>
              )}
              <div style={{ position: 'relative', display: 'flex' }}>
                {TAB_ICONS[tab.key](c)}
              </div>
              <div style={{
                position: 'relative',
                fontSize: 10, fontWeight: isActive ? 600 : 500,
                letterSpacing: 0.1, color: c,
              }}>{tab.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Home screen
// ─────────────────────────────────────────────────────────────
function ResilioHome({ dark = false, accent = ACCENTS.clinical }) {
  const t = themeTokens(dark);
  return (
    <div style={{
      background: t.bg,
      minHeight: '100%',
      fontFamily: '"Inter", -apple-system, system-ui, sans-serif',
      color: t.text,
      paddingTop: 56, paddingBottom: 100,
      position: 'relative', minHeight: '100%',
    }}>
      {/* Greeting row */}
      <div style={{ padding: '14px 24px 20px' }}>
        <div style={{
          fontSize: 26, fontWeight: 500, color: t.text,
          letterSpacing: -0.6, lineHeight: 1.15,
        }}>
          Bonjour, Simon-Olivier
        </div>
        <div style={{
          marginTop: 6,
          fontSize: 13, color: t.textSec, letterSpacing: 0.1,
          fontVariantNumeric: 'tabular-nums',
        }}>
          Vendredi 17 avril
        </div>
      </div>

      {/* Readiness ring — dominant */}
      <div style={{ padding: '0 24px 20px' }}>
        <ReadinessRing value={72} t={t} accent={accent}/>
      </div>

      {/* Row of 3 metric rings */}
      <div style={{ padding: '0 20px 20px' }}>
        <Card t={t} style={{ display: 'flex', padding: '2px 4px' }}>
          <MetricRing label="Nutrition" value={65} color={t.warn} t={t}/>
          <div style={{ width: 0.5, background: t.hairline, margin: '14px 0' }}/>
          <MetricRing label="Strain" value={48} color={t.ok} t={t}/>
          <div style={{ width: 0.5, background: t.hairline, margin: '14px 0' }}/>
          <MetricRing label="Sommeil" value={81} color={t.okStrong} t={t}/>
        </Card>
      </div>

      {/* Allostatic load card */}
      <div style={{ padding: '0 20px 16px' }}>
        <Card t={t} style={{ padding: '20px 22px 18px' }}>
          <div style={{
            display: 'flex', alignItems: 'flex-start',
            justifyContent: 'space-between', marginBottom: 4,
          }}>
            <div>
              <div style={{
                fontSize: 11, textTransform: 'uppercase', letterSpacing: 1.2,
                color: t.textTer, fontWeight: 500,
              }}>Charge allostatique</div>
              <div style={{
                marginTop: 6,
                fontSize: 13, color: t.textSec, maxWidth: 170,
                lineHeight: 1.4, letterSpacing: -0.05,
              }}>
                Stress cumulé 7 jours. Faible.
              </div>
            </div>
            <AllostaticDial value={28} t={t} accent={accent}/>
          </div>
          {/* gradient legend */}
          <div style={{
            marginTop: 10,
            display: 'flex', justifyContent: 'space-between',
            fontSize: 10, color: t.textTer,
            textTransform: 'uppercase', letterSpacing: 0.8,
            fontVariantNumeric: 'tabular-nums',
          }}>
            <span>0</span><span>50</span><span>100</span>
          </div>
        </Card>
      </div>

      {/* Today's session card */}
      <div style={{ padding: '0 20px 24px' }}>
        <Card t={t} style={{ padding: '18px 20px' }}>
          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', gap: 12,
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                marginBottom: 8,
              }}>
                <span style={{
                  fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.2,
                  color: t.textTer, fontWeight: 500,
                }}>Séance du jour</span>
                <span style={{
                  fontSize: 10, letterSpacing: 0.4,
                  padding: '2px 7px', borderRadius: 4,
                  background: t.surface2, color: t.textSec,
                  fontWeight: 500, textTransform: 'uppercase',
                }}>Z1</span>
              </div>
              <div style={{
                fontSize: 17, fontWeight: 500, color: t.text,
                letterSpacing: -0.3, lineHeight: 1.25,
              }}>Course facile</div>
              <div style={{
                marginTop: 4,
                fontSize: 13, color: t.textSec, letterSpacing: -0.05,
                fontVariantNumeric: 'tabular-nums',
              }}>45 min · Zone 1 · 7,5 km</div>
            </div>
            {/* chevron */}
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: t.surface2, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <svg width="12" height="12" viewBox="0 0 12 12">
                <path d="M4 2l4 4-4 4" stroke={t.textSec}
                  strokeWidth="1.6" fill="none" strokeLinecap="round"
                  strokeLinejoin="round"/>
              </svg>
            </div>
          </div>
        </Card>
      </div>

      {/* Primary button */}
      <div style={{ padding: '0 20px' }}>
        <button style={{
          width: '100%', height: 54, border: 'none',
          borderRadius: 16,
          background: accent, color: '#fff',
          fontFamily: 'inherit', fontSize: 16, fontWeight: 500,
          letterSpacing: -0.1,
          boxShadow: `0 1px 0 rgba(255,255,255,0.12) inset, 0 6px 18px ${accent}33`,
          cursor: 'pointer',
        }}>
          Check-in quotidien
        </button>
      </div>

      <TabBar active="home" t={t} accent={accent} dark={dark}/>
    </div>
  );
}

Object.assign(window, { ResilioHome, ACCENTS });
