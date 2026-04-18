// Resilio+ — Home / Dashboard
// 6 states across light/dark × normal/ideal/recovery

// ─── Tokens ──────────────────────────────────────────────────
const T = {
  light: {
    bg: '#F5F5F2',
    surface: '#FAFAF7',
    surfaceAlt: '#EFEEE9',
    border: 'rgba(40,30,20,0.08)',
    borderStrong: 'rgba(40,30,20,0.14)',
    text: '#1A1815',
    textMuted: '#6B655D',
    textFaint: '#9A958C',
    accent: 'oklch(0.62 0.14 55)',           // warm amber, single accent
    accentText: '#FAFAF7',
    track: 'rgba(40,30,20,0.06)',
    tabBar: 'rgba(250,250,247,0.85)',
  },
  dark: {
    bg: '#161412',
    surface: '#1F1D1A',
    surfaceAlt: '#282622',
    border: 'rgba(255,248,235,0.07)',
    borderStrong: 'rgba(255,248,235,0.12)',
    text: '#EDEAE3',
    textMuted: '#9A948A',
    textFaint: '#5E584F',
    accent: 'oklch(0.72 0.14 65)',
    accentText: '#161412',
    track: 'rgba(255,248,235,0.06)',
    tabBar: 'rgba(31,29,26,0.85)',
  },
};

// Physiological palette — ONLY used for Readiness/Strain/Sleep/HRV
const SEM = {
  green: 'oklch(0.68 0.15 145)',
  yellow: 'oklch(0.78 0.14 85)',
  red: 'oklch(0.62 0.19 25)',
};

const tone = (readiness) => readiness >= 80 ? SEM.green : readiness >= 60 ? SEM.yellow : SEM.red;

// ─── Primitives ──────────────────────────────────────────────
const SC = ({ children, style }) => (
  <span style={{ fontVariantNumeric: 'tabular-nums', ...style }}>{children}</span>
);

const Divider = ({ t, vertical }) => (
  <div style={{
    background: t.border,
    ...(vertical
      ? { width: 1, alignSelf: 'stretch', margin: '2px 0' }
      : { height: 1, width: '100%' }),
  }} />
);

// ─── Readiness Ring ──────────────────────────────────────────
function ReadinessRing({ value, delta, t, size = 196 }) {
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = tone(value);
  const offset = c * (1 - value / 100);
  const deltaSign = delta > 0 ? '+' : '';
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r}
          stroke={t.track} strokeWidth={stroke} fill="none" />
        <circle cx={size/2} cy={size/2} r={r}
          stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={c} strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 800ms cubic-bezier(.4,0,.2,1)' }} />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <SC style={{
          fontSize: 72, fontWeight: 500, color: t.text,
          letterSpacing: -3.5, lineHeight: 1,
          fontFeatureSettings: '"tnum"',
        }}>{value}</SC>
        <div style={{
          fontSize: 11, fontWeight: 500, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: 1.8,
          marginTop: 6,
        }}>Readiness</div>
        <SC style={{
          fontSize: 12, color: color,
          marginTop: 4, fontWeight: 500,
        }}>{deltaSign}{delta} vs hier</SC>
      </div>
    </div>
  );
}

// ─── Metrics Strip ───────────────────────────────────────────
function MetricsStrip({ t, nutrition, strain, sleep }) {
  const nutritionPct = Math.min(100, (nutrition.kcal / nutrition.target) * 100);
  const strainColor = strain.value >= 18 ? SEM.red : strain.value >= 14 ? SEM.yellow : SEM.green;
  const sleepColor = sleep.score >= 80 ? SEM.green : sleep.score >= 65 ? SEM.yellow : SEM.red;

  const Item = ({ label, children, last }) => (
    <div style={{
      flex: 1, padding: '16px 14px',
      borderRight: last ? 'none' : `1px solid ${t.border}`,
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, color: t.textMuted,
        textTransform: 'uppercase', letterSpacing: 1.4,
      }}>{label}</div>
      {children}
    </div>
  );

  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 14,
      display: 'flex',
      overflow: 'hidden',
    }}>
      <Item label="Nutrition">
        <SC style={{ fontSize: 17, fontWeight: 500, color: t.text, letterSpacing: -0.4 }}>
          {nutrition.kcal}<span style={{ color: t.textFaint }}> / {nutrition.target}</span>
        </SC>
        <div style={{ fontSize: 11, color: t.textMuted }}>kcal</div>
        <div style={{
          height: 3, background: t.track, borderRadius: 2,
          overflow: 'hidden', marginTop: 2,
        }}>
          <div style={{
            height: '100%', width: `${nutritionPct}%`,
            background: t.text, opacity: 0.85,
          }} />
        </div>
      </Item>
      <Item label="Strain">
        <SC style={{ fontSize: 17, fontWeight: 500, color: strainColor, letterSpacing: -0.4 }}>
          {strain.value.toFixed(1)}
        </SC>
        <div style={{ fontSize: 11, color: t.textMuted, lineHeight: 1.35 }}>
          Fatigue musculaire
        </div>
      </Item>
      <Item label="Sommeil" last>
        <SC style={{ fontSize: 17, fontWeight: 500, color: t.text, letterSpacing: -0.4 }}>
          {sleep.duration}
        </SC>
        <div style={{ fontSize: 11, color: t.textMuted }}>
          Score <SC style={{ color: sleepColor, fontWeight: 500 }}>{sleep.score}</SC>
        </div>
      </Item>
    </div>
  );
}

// ─── Session Card ────────────────────────────────────────────
function SessionCard({ t, session }) {
  const isOff = session.type === 'recovery';
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 14,
      padding: '18px 18px 0',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 14,
      }}>
        <div style={{
          fontSize: 10, fontWeight: 600, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: 1.4,
        }}>{isOff ? 'Récupération' : 'Séance du jour'}</div>
        <div style={{
          fontSize: 11, color: t.textFaint,
          fontVariantNumeric: 'tabular-nums',
        }}>{session.time}</div>
      </div>

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 8,
      }}>
        <div style={{
          fontSize: 22, fontWeight: 500, color: t.text,
          letterSpacing: -0.5,
        }}>{session.discipline}</div>
        <SC style={{
          fontSize: 15, color: t.textMuted, fontWeight: 500,
        }}>{session.duration}</SC>
      </div>

      <div style={{
        fontSize: 14, color: t.textMuted, lineHeight: 1.5,
        marginBottom: 16,
      }}>{session.brief}</div>

      {!isOff && (
        <div style={{
          display: 'flex', gap: 12, marginBottom: 16,
          padding: '12px 0',
          borderTop: `1px solid ${t.border}`,
        }}>
          {session.targets.map((target, i) => (
            <div key={i} style={{ flex: 1 }}>
              <div style={{
                fontSize: 10, color: t.textFaint, fontWeight: 500,
                textTransform: 'uppercase', letterSpacing: 1.2,
                marginBottom: 3,
              }}>{target.label}</div>
              <SC style={{
                fontSize: 14, color: t.text, fontWeight: 500,
                letterSpacing: -0.2,
              }}>{target.value}</SC>
            </div>
          ))}
        </div>
      )}

      <button style={{
        width: 'calc(100% + 36px)',
        marginLeft: -18, marginRight: -18,
        background: isOff ? t.surfaceAlt : t.accent,
        color: isOff ? t.text : t.accentText,
        border: 'none',
        borderTop: `1px solid ${isOff ? t.border : 'transparent'}`,
        padding: '16px 18px',
        fontSize: 15, fontWeight: 500,
        fontFamily: 'inherit',
        letterSpacing: -0.2,
        cursor: 'pointer',
        borderRadius: '0 0 13px 13px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 6,
      }}>
        {isOff ? 'Voir le protocole' : 'Démarrer la séance'}
        <svg width="14" height="14" viewBox="0 0 14 14" style={{ marginLeft: 2 }}>
          <path d="M3 7h8m-3-3l3 3-3 3" stroke="currentColor" strokeWidth="1.6"
            fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
    </div>
  );
}

// ─── Cognitive Load Card ─────────────────────────────────────
function CognitiveLoadCard({ t, value, label, context }) {
  // Horizontal segmented dial — deliberately different from Readiness ring
  const segments = 24;
  const filled = Math.round((value / 100) * segments);
  // Allostatic load uses semantic colors since it IS a physiological metric
  const color = value >= 70 ? SEM.red : value >= 45 ? SEM.yellow : SEM.green;

  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 14,
      padding: 18,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 4,
      }}>
        <div style={{
          fontSize: 10, fontWeight: 600, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: 1.4,
        }}>Charge cognitive</div>
        <div style={{ fontSize: 11, color: t.textFaint }}>7j</div>
      </div>
      <div style={{
        fontSize: 13, color: t.textFaint, marginBottom: 14,
      }}>Charge allostatique</div>

      {/* Segmented bar */}
      <div style={{
        display: 'flex', gap: 2, marginBottom: 12,
        height: 28, alignItems: 'stretch',
      }}>
        {Array.from({ length: segments }).map((_, i) => (
          <div key={i} style={{
            flex: 1,
            background: i < filled ? color : t.track,
            opacity: i < filled ? (0.35 + (i / segments) * 0.65) : 1,
            borderRadius: 1,
          }} />
        ))}
      </div>

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      }}>
        <SC style={{ fontSize: 18, fontWeight: 500, color: t.text, letterSpacing: -0.4 }}>
          {label}
        </SC>
        <SC style={{ fontSize: 13, color: t.textMuted }}>{context}</SC>
      </div>
    </div>
  );
}

// ─── Week Strip ──────────────────────────────────────────────
function WeekStrip({ t, days }) {
  // Discipline colors — these are training type markers, not physiological.
  // Use text tones only (no green/yellow/red) to respect the rule.
  return (
    <div>
      <div style={{
        fontSize: 10, fontWeight: 600, color: t.textMuted,
        textTransform: 'uppercase', letterSpacing: 1.4,
        marginBottom: 10, padding: '0 2px',
      }}>Semaine</div>
      <div style={{
        display: 'flex', gap: 6,
      }}>
        {days.map((d, i) => {
          const isToday = d.today;
          const isPast = d.past;
          return (
            <div key={i} style={{
              flex: 1,
              background: isToday ? t.surface : 'transparent',
              border: `1px solid ${isToday ? t.borderStrong : t.border}`,
              borderRadius: 10,
              padding: '10px 4px',
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              gap: 8,
              opacity: isPast && !isToday ? 0.55 : 1,
            }}>
              <div style={{
                fontSize: 10, fontWeight: 600,
                color: isToday ? t.accent : t.textMuted,
                textTransform: 'uppercase', letterSpacing: 0.8,
              }}>{d.dow}</div>
              <SC style={{
                fontSize: 15, fontWeight: 500,
                color: isToday ? t.text : t.textMuted,
                letterSpacing: -0.3,
              }}>{d.date}</SC>
              <DisciplineMark type={d.type} t={t} today={isToday} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DisciplineMark({ type, t, today }) {
  const size = 6;
  // run=filled circle, lift=square, swim=horizontal bar, bike=diamond, off=empty ring
  const base = { width: size, height: size };
  if (type === 'off') {
    return <div style={{ ...base, border: `1.5px solid ${t.textFaint}`, borderRadius: '50%' }} />;
  }
  const fill = today ? t.accent : t.text;
  if (type === 'run') return <div style={{ ...base, background: fill, borderRadius: '50%' }} />;
  if (type === 'lift') return <div style={{ ...base, background: fill, borderRadius: 1 }} />;
  if (type === 'swim') return <div style={{ width: size+2, height: 2, background: fill }} />;
  if (type === 'bike') return <div style={{ ...base, background: fill, transform: 'rotate(45deg)' }} />;
  return null;
}

// ─── Session Breakdown ───────────────────────────────────────
function SessionBreakdown({ t, blocks }) {
  if (!blocks || blocks.length === 0) return null;
  const totalDur = blocks.reduce((s, b) => s + b.min, 0);
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 14,
      padding: 18,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 14,
      }}>
        <div style={{
          fontSize: 10, fontWeight: 600, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: 1.4,
        }}>Structure</div>
        <SC style={{ fontSize: 11, color: t.textFaint }}>{totalDur} min</SC>
      </div>

      {/* Intensity bar */}
      <div style={{
        display: 'flex', gap: 2, height: 6,
        marginBottom: 14, borderRadius: 2, overflow: 'hidden',
      }}>
        {blocks.map((b, i) => (
          <div key={i} style={{
            flex: b.min,
            background: t.text,
            opacity: 0.15 + (b.intensity / 10) * 0.75,
          }} />
        ))}
      </div>

      {/* Block list */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {blocks.map((b, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'baseline', gap: 14,
            padding: '10px 0',
            borderTop: i > 0 ? `1px solid ${t.border}` : 'none',
          }}>
            <SC style={{
              fontSize: 11, color: t.textFaint, fontWeight: 500,
              width: 26, letterSpacing: 0.4,
            }}>{String(i+1).padStart(2,'0')}</SC>
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: 14, color: t.text, fontWeight: 500,
                letterSpacing: -0.2, marginBottom: 2,
              }}>{b.label}</div>
              <div style={{ fontSize: 12, color: t.textMuted }}>{b.detail}</div>
            </div>
            <SC style={{
              fontSize: 13, color: t.textMuted,
              fontWeight: 500, fontVariantNumeric: 'tabular-nums',
            }}>{b.min}′</SC>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Day Plan ────────────────────────────────────────────────
function DayPlan({ t, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 14,
      padding: 18,
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, color: t.textMuted,
        textTransform: 'uppercase', letterSpacing: 1.4,
        marginBottom: 14,
      }}>Journée</div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {items.map((it, i) => (
          <div key={i} style={{
            display: 'flex', gap: 14, alignItems: 'flex-start',
            padding: '10px 0',
            borderTop: i > 0 ? `1px solid ${t.border}` : 'none',
            opacity: it.done ? 0.5 : 1,
          }}>
            <SC style={{
              fontSize: 12, color: t.textMuted, fontWeight: 500,
              width: 44, paddingTop: 2, letterSpacing: 0.2,
              textDecoration: it.done ? 'line-through' : 'none',
            }}>{it.time}</SC>
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: 14, color: t.text, fontWeight: 500,
                letterSpacing: -0.2,
                textDecoration: it.done ? 'line-through' : 'none',
              }}>{it.title}</div>
              {it.meta && (
                <div style={{ fontSize: 12, color: t.textMuted, marginTop: 2 }}>{it.meta}</div>
              )}
            </div>
            {it.tag && (
              <div style={{
                fontSize: 10, fontWeight: 600, color: t.textMuted,
                textTransform: 'uppercase', letterSpacing: 1.2,
                padding: '3px 7px', borderRadius: 4,
                background: t.surfaceAlt,
                marginTop: 1,
              }}>{it.tag}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Coach Note ──────────────────────────────────────────────
function CoachNote({ t, note }) {
  if (!note) return null;
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${t.border}`,
      borderRadius: 14,
      padding: 18,
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: 12,
      }}>
        <div style={{
          fontSize: 10, fontWeight: 600, color: t.textMuted,
          textTransform: 'uppercase', letterSpacing: 1.4,
        }}>Note du coach</div>
        <div style={{ fontSize: 11, color: t.textFaint }}>{note.agent}</div>
      </div>
      <div style={{
        fontSize: 14, color: t.text, lineHeight: 1.55,
        letterSpacing: -0.1,
      }}>{note.body}</div>
    </div>
  );
}

// ─── Tab Bar ─────────────────────────────────────────────────
const tabIcons = {
  home: (
    <path d="M3 10L11 3l8 7v9a1 1 0 01-1 1h-4v-6H8v6H4a1 1 0 01-1-1v-9z"
      fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
  ),
  training: (
    <g fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
      <path d="M4 8v6M18 8v6M2 9v4M20 9v4"/>
      <rect x="6" y="6" width="10" height="10" rx="1.5"/>
    </g>
  ),
  coach: (
    <g fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M4 6a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2h-4l-3 3v-3H6a2 2 0 01-2-2V6z" strokeLinejoin="round"/>
      <circle cx="8.5" cy="10" r="0.7" fill="currentColor" stroke="none"/>
      <circle cx="11" cy="10" r="0.7" fill="currentColor" stroke="none"/>
      <circle cx="13.5" cy="10" r="0.7" fill="currentColor" stroke="none"/>
    </g>
  ),
  metrics: (
    <g fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 15l4-5 3 3 4-6 4 5"/>
      <path d="M3 19h16"/>
    </g>
  ),
  profile: (
    <g fill="none" stroke="currentColor" strokeWidth="1.4">
      <circle cx="11" cy="8" r="3.5"/>
      <path d="M4 19c0-3.5 3-6 7-6s7 2.5 7 6" strokeLinecap="round"/>
    </g>
  ),
};

function TabBar({ t, active = 'home', dark }) {
  // Liquid glass: floating pill (4 nav tabs) + trailing round button (profile)
  const navTabs = [
    { k: 'home', l: 'Home' },
    { k: 'training', l: 'Training' },
    { k: 'coach', l: 'Coach' },
    { k: 'metrics', l: 'Metrics' },
  ];

  const glassBg = dark ? 'rgba(40,38,34,0.55)' : 'rgba(250,250,247,0.58)';
  const glassBorder = dark ? 'rgba(255,248,235,0.12)' : 'rgba(40,30,20,0.08)';
  const shine = dark
    ? 'inset 1px 1px 0 rgba(255,255,255,0.1), inset -1px -1px 0 rgba(255,255,255,0.04)'
    : 'inset 1px 1px 0 rgba(255,255,255,0.7), inset -1px -1px 0 rgba(255,255,255,0.35)';
  const shadow = dark
    ? '0 8px 24px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.25)'
    : '0 8px 20px rgba(40,30,20,0.08), 0 2px 6px rgba(40,30,20,0.05)';

  const glassLayer = (radius) => (
    <>
      <div style={{
        position: 'absolute', inset: 0, borderRadius: radius,
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        background: glassBg,
      }} />
      <div style={{
        position: 'absolute', inset: 0, borderRadius: radius,
        boxShadow: shine,
        border: `0.5px solid ${glassBorder}`,
        pointerEvents: 'none',
      }} />
    </>
  );

  return (
    <div style={{
      position: 'absolute', bottom: 28, left: 16, right: 16,
      display: 'flex', gap: 10, alignItems: 'center',
      zIndex: 30,
    }}>
      {/* Main pill with 4 nav tabs */}
      <div style={{
        flex: 1, position: 'relative',
        borderRadius: 9999, height: 56,
        boxShadow: shadow,
      }}>
        {glassLayer(9999)}
        <div style={{
          position: 'relative', zIndex: 1, height: '100%',
          display: 'flex', alignItems: 'center',
          padding: '0 6px',
        }}>
          {navTabs.map(tab => {
            const isActive = tab.k === active;
            return (
              <div key={tab.k} style={{
                flex: 1, height: 44,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                gap: 2,
                color: isActive ? t.accent : t.textMuted,
                position: 'relative',
              }}>
                {isActive && (
                  <div style={{
                    position: 'absolute', inset: '2px 4px',
                    borderRadius: 9999,
                    background: dark
                      ? 'rgba(255,255,255,0.08)'
                      : 'rgba(40,30,20,0.06)',
                  }} />
                )}
                <div style={{ position: 'relative', zIndex: 1 }}>
                  <svg width="22" height="22" viewBox="0 0 22 22">{tabIcons[tab.k]}</svg>
                </div>
                <div style={{
                  position: 'relative', zIndex: 1,
                  fontSize: 9.5, fontWeight: isActive ? 600 : 500,
                  letterSpacing: 0.2,
                }}>{tab.l}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trailing round profile button */}
      <div style={{
        position: 'relative',
        width: 56, height: 56, borderRadius: '50%',
        boxShadow: shadow,
        color: t.textMuted,
      }}>
        {glassLayer('50%')}
        <div style={{
          position: 'relative', zIndex: 1,
          width: '100%', height: '100%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <svg width="22" height="22" viewBox="0 0 22 22">{tabIcons.profile}</svg>
        </div>
      </div>
    </div>
  );
}

// ─── Screen ──────────────────────────────────────────────────
function DashboardScreen({ state, dark = false }) {
  const t = dark ? T.dark : T.light;
  const d = DATA[state];

  return (
    <div style={{
      width: '100%', height: '100%',
      background: t.bg,
      color: t.text,
      fontFamily: '"Space Grotesk", -apple-system, system-ui, sans-serif',
      fontFeatureSettings: '"ss01", "ss02", "tnum"',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Scrollable content */}
      <div style={{
        height: '100%',
        overflowY: 'auto',
        paddingTop: 60,    // under status bar
        paddingBottom: 130, // above floating glass tab bar
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '14px 20px 24px',
        }}>
          <div>
            <div style={{
              fontSize: 22, fontWeight: 500, color: t.text,
              letterSpacing: -0.6, lineHeight: 1.1,
            }}>Bonjour Simon</div>
            <div style={{
              fontSize: 11, fontWeight: 600, color: t.textMuted,
              textTransform: 'uppercase', letterSpacing: 1.5,
              marginTop: 4,
              fontVariantNumeric: 'tabular-nums',
            }}>{d.date}</div>
          </div>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: t.surfaceAlt,
            border: `1px solid ${t.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 500, color: t.text,
            letterSpacing: 0.4,
          }}>SR</div>
        </div>

        {/* Readiness Hero */}
        <div style={{
          display: 'flex', justifyContent: 'center',
          padding: '8px 20px 28px',
        }}>
          <ReadinessRing value={d.readiness.value} delta={d.readiness.delta} t={t} />
        </div>

        {/* Metrics strip */}
        <div style={{ padding: '0 20px 16px' }}>
          <MetricsStrip t={t} {...d.metrics} />
        </div>

        {/* Session card */}
        <div style={{ padding: '0 20px 16px' }}>
          <SessionCard t={t} session={d.session} />
        </div>

        {/* Cognitive Load card */}
        <div style={{ padding: '0 20px 20px' }}>
          <CognitiveLoadCard t={t} {...d.cognitive} />
        </div>

        {/* Week */}
        <div style={{ padding: '4px 20px 20px' }}>
          <WeekStrip t={t} days={d.week} />
        </div>

        {/* Session breakdown */}
        <div style={{ padding: '0 20px 16px' }}>
          <SessionBreakdown t={t} blocks={d.sessionBlocks} />
        </div>

        {/* Day plan */}
        <div style={{ padding: '0 20px 16px' }}>
          <DayPlan t={t} items={d.dayPlan} />
        </div>

        {/* Coach note */}
        <div style={{ padding: '0 20px 24px' }}>
          <CoachNote t={t} note={d.coachNote} />
        </div>
      </div>

      {/* Status bar overlay */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10,
      }}>
        <IOSStatusBar dark={dark} />
      </div>

      {/* Tab bar */}
      <TabBar t={t} active="home" dark={dark} />
    </div>
  );
}

// ─── Data for 3 states ───────────────────────────────────────
const WEEK_BASE = [
  { dow: 'Lun', date: '13', type: 'run',  past: true },
  { dow: 'Mar', date: '14', type: 'lift', past: true },
  { dow: 'Mer', date: '15', type: 'swim', past: true },
  { dow: 'Jeu', date: '16', type: 'bike', past: true },
  { dow: 'Ven', date: '17', type: 'lift', past: true },
  { dow: 'Sam', date: '18', type: 'run',  today: true },
  { dow: 'Dim', date: '19', type: 'off' },
];

const DATA = {
  normal: {
    date: 'SAM. 18 AVR.',
    readiness: { value: 78, delta: 4 },
    metrics: {
      nutrition: { kcal: 2140, target: 2600 },
      strain: { value: 14.2 },
      sleep: { duration: '7h32', score: 82 },
    },
    session: {
      type: 'run',
      time: '09:00',
      discipline: 'Course',
      duration: '52 min',
      brief: 'Endurance fondamentale. Zone 2 stricte. Respiration nasale privilégiée.',
      targets: [
        { label: 'Allure', value: '5:42/km' },
        { label: 'FC cible', value: '142 bpm' },
        { label: 'TSS', value: '58' },
      ],
    },
    cognitive: { value: 52, label: 'Modérée', context: '62 / 100' },
    week: WEEK_BASE,
    sessionBlocks: [
      { label: 'Échauffement', detail: 'Z1, allure libre, mobilité', min: 10, intensity: 2 },
      { label: 'Corps principal', detail: 'Z2 continu, allure 5:42/km', min: 32, intensity: 5 },
      { label: 'Retour au calme', detail: 'Z1, décontraction, étirements', min: 10, intensity: 1 },
    ],
    dayPlan: [
      { time: '07:30', title: 'Réveil + HRV', meta: 'Mesure du matin', done: true },
      { time: '08:15', title: 'Petit-déjeuner', meta: '640 kcal · 52g glucides', done: true, tag: 'Pré' },
      { time: '09:00', title: 'Course 52 min', meta: 'Zone 2, allure 5:42/km', tag: 'Séance' },
      { time: '10:15', title: 'Récup + protéines', meta: '30g whey · 250ml eau' },
      { time: '13:00', title: 'Déjeuner', meta: 'Cible 780 kcal · 45g prot' },
      { time: '22:30', title: 'Coucher', meta: 'Fenêtre sommeil 7h30' },
    ],
    coachNote: {
      agent: 'Agent Endurance',
      body: 'Tu sors d\'un bloc de 3 jours en Z2. ACWR à 1.08, confortable. Maintien de l\'allure prioritaire sur le volume aujourd\'hui. Si FC dérive >146 bpm, coupe court.',
    },
  },
  ideal: {
    date: 'DIM. 19 AVR.',
    readiness: { value: 92, delta: 7 },
    metrics: {
      nutrition: { kcal: 2480, target: 2600 },
      strain: { value: 8.6 },
      sleep: { duration: '8h14', score: 94 },
    },
    session: {
      type: 'bike',
      time: '07:30',
      discipline: 'Vélo',
      duration: '2h10',
      brief: 'Sortie sweet-spot. 3×15 min à 88% FTP. Fenêtre physiologique ouverte.',
      targets: [
        { label: 'Puissance', value: '265 W' },
        { label: 'NP', value: '248 W' },
        { label: 'TSS', value: '124' },
      ],
    },
    cognitive: { value: 28, label: 'Basse', context: '34 / 100' },
    week: WEEK_BASE.map((d, i) =>
      i === 5 ? { ...d, today: false, past: true } :
      i === 6 ? { ...d, type: 'bike', today: true, past: false } : d
    ),
    sessionBlocks: [
      { label: 'Échauffement progressif', detail: 'Z1→Z2, 3×30s activation', min: 20, intensity: 3 },
      { label: 'Bloc sweet-spot', detail: '3×15 min @ 88% FTP · récup 5 min', min: 60, intensity: 8 },
      { label: 'Endurance', detail: 'Z2 stable, cadence 88-92', min: 40, intensity: 5 },
      { label: 'Retour au calme', detail: 'Z1, moulinage', min: 10, intensity: 1 },
    ],
    dayPlan: [
      { time: '06:15', title: 'Réveil + HRV', meta: 'rMSSD 68ms · +12%', done: true, tag: 'Idéal' },
      { time: '06:45', title: 'Petit-déjeuner complet', meta: '720 kcal · 95g glucides', done: true },
      { time: '07:30', title: 'Vélo sweet-spot 2h10', meta: '3×15 min @ 88% FTP' },
      { time: '10:00', title: 'Récup + repas', meta: 'Fenêtre anabolique 45 min' },
      { time: '14:00', title: 'Sieste 20 min', meta: 'Consolidation' },
      { time: '19:30', title: 'Dîner', meta: 'Cible 820 kcal' },
      { time: '22:00', title: 'Coucher', meta: 'Fenêtre sommeil 8h' },
    ],
    coachNote: {
      agent: 'Agent Endurance',
      body: 'Signaux verts sur toute la ligne. HRV +12% sur 7j, Strain accumulé bas. Fenêtre idéale pour pousser le seuil. Respecte les intervalles, ne dépasse pas 92% FTP.',
    },
  },
  recovery: {
    date: 'SAM. 18 AVR.',
    readiness: { value: 45, delta: -18 },
    metrics: {
      nutrition: { kcal: 1820, target: 2400 },
      strain: { value: 19.8 },
      sleep: { duration: '5h48', score: 54 },
    },
    session: {
      type: 'recovery',
      time: 'Aujourd\'hui',
      discipline: 'Récupération active',
      duration: '20–30 min',
      brief: 'Séance prescrite annulée. HRV en baisse, Strain cumulé élevé. Mobilité, marche, sauna si dispo. Hydratation +500ml.',
      targets: [],
    },
    cognitive: { value: 82, label: 'Élevée', context: '88 / 100' },
    week: WEEK_BASE.map((d, i) => i === 5 ? { ...d, type: 'off', today: true } : d),
    sessionBlocks: [
      { label: 'Mobilité articulaire', detail: 'Hanches, épaules, colonne', min: 10, intensity: 1 },
      { label: 'Marche Z1', detail: 'Extérieur, respiration nasale', min: 15, intensity: 2 },
      { label: 'Sauna ou bain chaud', detail: 'Optionnel · 10-15 min', min: 15, intensity: 1 },
    ],
    dayPlan: [
      { time: '08:20', title: 'Réveil', meta: 'HRV 31ms · -38% vs baseline', done: true, tag: 'Alerte' },
      { time: '09:00', title: 'Hydratation +500ml', meta: 'Électrolytes, pas de café', done: true },
      { time: '10:00', title: 'Récupération active', meta: 'Mobilité + marche' },
      { time: '13:00', title: 'Déjeuner riche en prot', meta: 'Cible 45g prot · micronutriments' },
      { time: '17:00', title: 'Étirements doux', meta: '15 min, respiration' },
      { time: '21:30', title: 'Coucher anticipé', meta: 'Viser 9h · obscurité totale' },
    ],
    coachNote: {
      agent: 'Agent Récupération',
      body: 'Trois signaux d\'alerte convergent : HRV -38%, sommeil 5h48, Strain cumulé 19.8. La séance de course est annulée. Pas de négociation. Objectif du jour : dormir, manger, respirer.',
    },
  },
};

Object.assign(window, { DashboardScreen, DATA });
