// Resilio+ — shared UI primitives + discipline marks

// ─────── Discipline dot ───────
// Value-based, not color-based. 10px default.
function DiscDot({ type, theme, size = 10 }) {
  const d = theme.disc[type];
  if (!d) return null;
  const s = size;
  const half = d.type === 'half';
  const outline = d.type === 'outline';
  return (
    <span style={{
      display: 'inline-block', width: s, height: s, flexShrink: 0,
      position: 'relative',
    }}>
      <svg width={s} height={s} viewBox="0 0 10 10">
        {outline && (
          <circle cx="5" cy="5" r="4" fill="none" stroke={d.stroke} strokeWidth="1.2" />
        )}
        {!outline && !half && (
          <circle cx="5" cy="5" r="4.5" fill={d.fill} />
        )}
        {half && (
          <>
            <circle cx="5" cy="5" r="4" fill="none" stroke={d.stroke} strokeWidth="1.2" />
            <path d="M5,1 A4,4 0 0,1 5,9 Z" fill={d.fill} />
          </>
        )}
      </svg>
    </span>
  );
}

// ─────── Discipline icon (larger, 18-22px) for list rows ───────
function DiscIcon({ type, theme, size = 20 }) {
  const color = theme.text;
  const strokeW = 1.6;
  const props = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: color, strokeWidth: strokeW, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch (type) {
    case 'run':
      return (
        <svg {...props}>
          <circle cx="15" cy="4.5" r="1.6" fill={color} stroke="none" />
          <path d="M7 21l3-6 3 2 2-4" />
          <path d="M5 13l3-3 4 1 3-3" />
          <path d="M15 10l2 2 3-1" />
        </svg>
      );
    case 'lift':
      return (
        <svg {...props}>
          <path d="M3 9v6" />
          <path d="M6 7v10" />
          <path d="M9 10v4" />
          <path d="M15 10v4" />
          <path d="M18 7v10" />
          <path d="M21 9v6" />
          <path d="M9 12h6" />
        </svg>
      );
    case 'bike':
      return (
        <svg {...props}>
          <circle cx="5.5" cy="17" r="3.5" />
          <circle cx="18.5" cy="17" r="3.5" />
          <path d="M5.5 17l4.5-7h5l3.5 7" />
          <path d="M10 10l-1.5-3H6" />
          <path d="M15 10l1-3h2" />
        </svg>
      );
    case 'swim':
      return (
        <svg {...props}>
          <path d="M2 17c1.5-1 3-1 4.5 0S9.5 18 11 17s3-1 4.5 0 3 1 4.5 0" />
          <path d="M2 13c1.5-1 3-1 4.5 0S9.5 14 11 13s3-1 4.5 0 3 1 4.5 0" />
          <circle cx="16" cy="7" r="1.8" fill={color} stroke="none" />
          <path d="M6 10l4-2 3 2" />
        </svg>
      );
    default:
      return null;
  }
}

// ─────── Number with delta (for stats strip) ───────
function StatBlock({ label, value, unit, delta, theme, align = 'left' }) {
  // Delta is neutral — no sem colors (accent for positive, textTer for negative/zero).
  // Per brief, sem palette is reserved for physio only.
  const dn = delta;
  const isPos = dn > 0;
  const isNeg = dn < 0;
  return (
    <div style={{ textAlign: align, flex: 1 }}>
      <div style={{
        fontSize: 11, fontWeight: 500, color: theme.textTer,
        letterSpacing: 0.6, textTransform: 'uppercase',
        marginBottom: 6,
      }}>{label}</div>
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 6,
        justifyContent: align === 'right' ? 'flex-end' : 'flex-start',
      }}>
        <span style={{
          fontFamily: 'Space Grotesk', fontSize: 26, fontWeight: 500,
          color: theme.text, letterSpacing: -0.8,
          fontVariantNumeric: 'tabular-nums',
        }}>{value}</span>
        {unit && (
          <span style={{
            fontSize: 12, fontWeight: 500, color: theme.textTer,
            letterSpacing: -0.1,
          }}>{unit}</span>
        )}
      </div>
      <div style={{
        marginTop: 4,
        display: 'flex', gap: 3, alignItems: 'center',
        fontSize: 11, fontWeight: 500, letterSpacing: -0.1,
        color: theme.textSec,
        fontVariantNumeric: 'tabular-nums',
        justifyContent: align === 'right' ? 'flex-end' : 'flex-start',
      }}>
        <span style={{ color: theme.textTer, fontSize: 10 }}>
          {isPos ? '↑' : isNeg ? '↓' : '–'}
        </span>
        <span>{isPos ? '+' : ''}{dn}{unit === '%' ? 'pt' : ''} vs 7j préc.</span>
      </div>
    </div>
  );
}

// ─────── Stats Strip ───────
function StatsStrip({ theme }) {
  const { byDate, today } = window.TRAINING_DATA;
  // Count sessions + sum volume (min) + sum load in last 7 days (incl today)
  const sumRange = (start, days) => {
    let ses = 0, vol = 0, load = 0;
    for (let i = 0; i < days; i++) {
      const d = new Date(start);
      d.setDate(d.getDate() - i);
      const k = window.TRAINING_DATA.fmt(d);
      const ss = byDate[k] || [];
      ses += ss.length;
      ss.forEach(s => { vol += s.dur; load += s.load; });
    }
    return { ses, vol, load };
  };
  const cur = sumRange(today, 7);
  const prevStart = new Date(today); prevStart.setDate(prevStart.getDate() - 7);
  const prev = sumRange(prevStart, 7);

  const hours = (m) => {
    const h = Math.floor(m / 60);
    const rem = m % 60;
    return `${h}h${String(rem).padStart(2, '0')}`;
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'stretch',
      padding: '16px 20px 20px',
      borderBottom: `0.5px solid ${theme.hairline}`,
      gap: 0,
    }}>
      <StatBlock
        label="Séances"
        value={cur.ses}
        delta={cur.ses - prev.ses}
        theme={theme}
      />
      <div style={{ width: 0.5, background: theme.hairline, margin: '4px 0' }} />
      <div style={{ flex: 1, paddingLeft: 20 }}>
        <StatBlock
          label="Volume"
          value={hours(cur.vol)}
          delta={Math.round((cur.vol - prev.vol) / 5) * 5}
          unit="min"
          theme={theme}
        />
      </div>
      <div style={{ width: 0.5, background: theme.hairline, margin: '4px 0' }} />
      <div style={{ flex: 1, paddingLeft: 20 }}>
        <StatBlock
          label="Charge"
          value={cur.load}
          delta={cur.load - prev.load}
          theme={theme}
        />
      </div>
    </div>
  );
}

// ─────── Segmented control ───────
function Segmented({ options, value, onChange, theme }) {
  return (
    <div style={{
      display: 'inline-flex',
      background: theme.surface2,
      borderRadius: 9,
      padding: 3,
      gap: 2,
      position: 'relative',
    }}>
      {options.map(opt => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              border: 'none',
              background: active ? theme.surface : 'transparent',
              color: active ? theme.text : theme.textSec,
              fontFamily: 'Space Grotesk',
              fontSize: 13,
              fontWeight: 500,
              letterSpacing: -0.1,
              padding: '7px 18px',
              borderRadius: 6,
              cursor: 'pointer',
              boxShadow: active ? `0 0.5px 0 ${theme.hairline}, 0 1px 2px rgba(0,0,0,0.04)` : 'none',
              transition: 'background 120ms, color 120ms',
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

Object.assign(window, { DiscDot, DiscIcon, StatBlock, StatsStrip, Segmented });
