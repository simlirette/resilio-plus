// Resilio+ — Calendar + List views + Day detail drawer

// ─────── Calendar grid ───────
function CalendarView({ theme, monthOffset, onSelectDay, selectedDayKey }) {
  const { byDate, today, todayKey, fmt } = window.TRAINING_DATA;

  const viewDate = new Date(today.getFullYear(), today.getMonth() + monthOffset, 1);
  const monthLabel = viewDate.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

  // Lundi = 0 (French week)
  const firstDow = (viewDate.getDay() + 6) % 7;
  const daysInMonth = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 0).getDate();

  const weekdays = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];

  // Build cells (6 rows × 7 = 42)
  const cells = [];
  for (let i = 0; i < firstDow; i++) cells.push({ blank: true, key: `b${i}` });
  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(viewDate.getFullYear(), viewDate.getMonth(), d);
    const key = fmt(date);
    cells.push({ day: d, key, dateKey: key, isToday: key === todayKey, isFuture: date > today });
  }
  while (cells.length % 7 !== 0) cells.push({ blank: true, key: `b${cells.length}` });

  return (
    <div style={{ padding: '16px 12px 20px' }}>
      {/* Month header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '0 8px 14px',
      }}>
        <div style={{
          fontFamily: 'Space Grotesk', fontSize: 17, fontWeight: 500,
          color: theme.text, letterSpacing: -0.3,
          textTransform: 'capitalize',
        }}>{monthLabel}</div>
        <div style={{ display: 'flex', gap: 4 }}>
          <NavBtn theme={theme} dir="prev" />
          <NavBtn theme={theme} dir="next" />
        </div>
      </div>

      {/* Weekday header */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)',
        padding: '0 2px 8px',
      }}>
        {weekdays.map((w, i) => (
          <div key={i} style={{
            textAlign: 'center',
            fontFamily: 'Space Grotesk', fontSize: 11,
            fontWeight: 500, letterSpacing: 0.6,
            color: theme.textTer,
          }}>{w}</div>
        ))}
      </div>

      {/* Grid */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 4,
      }}>
        {cells.map(c => (
          <DayCell
            key={c.key}
            cell={c}
            sessions={c.dateKey ? (byDate[c.dateKey] || []) : []}
            theme={theme}
            onClick={() => c.dateKey && !c.isFuture && onSelectDay(c.dateKey)}
            selected={selectedDayKey === c.dateKey}
          />
        ))}
      </div>
    </div>
  );
}

function NavBtn({ theme, dir }) {
  return (
    <button style={{
      width: 32, height: 32, border: 'none', cursor: 'pointer',
      background: 'transparent', borderRadius: 8,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: theme.textSec,
    }}>
      <svg width="10" height="16" viewBox="0 0 10 16" fill="none">
        {dir === 'prev'
          ? <path d="M7 2L2 8l5 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          : <path d="M3 2l5 6-5 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        }
      </svg>
    </button>
  );
}

function DayCell({ cell, sessions, theme, onClick, selected }) {
  if (cell.blank) {
    return <div style={{ aspectRatio: '1 / 1.1' }} />;
  }

  const hasSession = sessions.length > 0;
  const isToday = cell.isToday;
  const isFuture = cell.isFuture;

  // Dedup types for dots (max 3)
  const types = [];
  sessions.forEach(s => { if (!types.includes(s.type)) types.push(s.type); });
  const displayTypes = types.slice(0, 3);

  const bg = selected
    ? theme.accentSoft
    : hasSession && !isFuture
      ? theme.surface2
      : 'transparent';

  const border = isToday
    ? `1.5px solid ${theme.accent}`
    : `0.5px solid ${selected ? theme.accent : 'transparent'}`;

  return (
    <button
      onClick={onClick}
      disabled={isFuture}
      style={{
        aspectRatio: '1 / 1.1',
        background: bg,
        border,
        borderRadius: 8,
        cursor: isFuture ? 'default' : 'pointer',
        padding: '6px 6px 5px',
        display: 'flex', flexDirection: 'column',
        justifyContent: 'space-between',
        opacity: isFuture ? 0.3 : 1,
        transition: 'background 120ms',
        fontFamily: 'Space Grotesk',
        position: 'relative',
      }}
    >
      <div style={{
        fontSize: 12, fontWeight: isToday ? 600 : 400,
        color: isToday ? theme.accent : theme.text,
        letterSpacing: -0.2,
        fontVariantNumeric: 'tabular-nums',
        textAlign: 'left',
        lineHeight: 1,
      }}>{cell.day}</div>
      <div style={{
        display: 'flex', gap: 3, justifyContent: 'flex-start',
        alignItems: 'center', minHeight: 10,
      }}>
        {displayTypes.map(t => (
          <DiscDot key={t} type={t} theme={theme} size={7} />
        ))}
      </div>
    </button>
  );
}

// ─────── List View ───────
function ListView({ theme, onSelectSession }) {
  const { byDate, today, todayKey, fmt } = window.TRAINING_DATA;

  // Build last ~50 days from today backwards
  const rows = [];
  for (let i = 0; i < 56; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = fmt(d);
    rows.push({
      dateKey: key,
      date: d,
      sessions: byDate[key] || [],
      isToday: key === todayKey,
    });
  }

  // Group into weeks for soft separator
  const weeks = [];
  let currentWeek = null;
  rows.forEach(r => {
    // ISO week starting Monday
    const weekStart = new Date(r.date);
    const dow = (weekStart.getDay() + 6) % 7;
    weekStart.setDate(weekStart.getDate() - dow);
    const weekKey = fmt(weekStart);
    if (!currentWeek || currentWeek.key !== weekKey) {
      currentWeek = { key: weekKey, start: weekStart, rows: [] };
      weeks.push(currentWeek);
    }
    currentWeek.rows.push(r);
  });

  return (
    <div style={{ paddingBottom: 40 }}>
      {weeks.map((w, wi) => (
        <WeekBlock key={w.key} week={w} theme={theme} onSelectSession={onSelectSession} isFirst={wi === 0} />
      ))}
    </div>
  );
}

function WeekBlock({ week, theme, onSelectSession, isFirst }) {
  const { fmt } = window.TRAINING_DATA;
  // Week summary: total sessions, total volume, total load
  let ses = 0, vol = 0, load = 0;
  week.rows.forEach(r => {
    ses += r.sessions.length;
    r.sessions.forEach(s => { vol += s.dur; load += s.load; });
  });
  const end = new Date(week.start); end.setDate(end.getDate() + 6);
  const weekLabel = `Sem. du ${week.start.getDate()} ${week.start.toLocaleDateString('fr-FR',{month:'short'}).replace('.','')}`;

  const hours = (m) => `${Math.floor(m/60)}h${String(m%60).padStart(2,'0')}`;

  return (
    <div>
      {/* Week header strip */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        padding: `${isFirst ? 14 : 22}px 20px 8px`,
        background: theme.bg,
      }}>
        <div style={{
          fontFamily: 'Space Grotesk', fontSize: 11,
          fontWeight: 500, color: theme.textTer,
          letterSpacing: 0.6, textTransform: 'uppercase',
        }}>{weekLabel}</div>
        <div style={{
          fontFamily: 'Space Grotesk', fontSize: 11,
          fontWeight: 500, color: theme.textTer,
          letterSpacing: 0.2,
          fontVariantNumeric: 'tabular-nums',
        }}>
          {ses} séances · {hours(vol)} · {load} charge
        </div>
      </div>
      {week.rows.map(r => (
        <DayRow key={r.dateKey} row={r} theme={theme} onSelectSession={onSelectSession} />
      ))}
    </div>
  );
}

function DayRow({ row, theme, onSelectSession }) {
  const d = row.date;
  const weekday = d.toLocaleDateString('fr-FR', { weekday: 'short' }).replace('.','').toUpperCase();
  const day = d.getDate();
  const month = d.toLocaleDateString('fr-FR', { month: 'short' }).replace('.','').toUpperCase();

  // Rest day (empty)
  if (row.sessions.length === 0) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center',
        padding: '10px 20px',
        borderBottom: `0.5px solid ${theme.hairline2}`,
      }}>
        <div style={{ width: 58, flexShrink: 0 }}>
          <div style={{
            fontFamily: 'Space Grotesk', fontSize: 11,
            fontWeight: 500, color: theme.textTer,
            letterSpacing: 0.4,
            fontVariantNumeric: 'tabular-nums',
          }}>{weekday} {day}</div>
        </div>
        <div style={{ width: 24, flexShrink: 0, display: 'flex', justifyContent: 'center' }}>
          <div style={{ width: 12, height: 1, background: theme.textQuad }} />
        </div>
        <div style={{
          flex: 1,
          fontFamily: 'Space Grotesk', fontSize: 13,
          fontWeight: 400, color: theme.textTer,
          letterSpacing: -0.1, paddingLeft: 10,
        }}>Récupération</div>
      </div>
    );
  }

  return (
    <>
      {row.sessions.map((s, idx) => (
        <SessionRow
          key={s.id}
          session={s}
          date={d}
          weekday={weekday}
          day={day}
          showDate={idx === 0}
          theme={theme}
          onClick={() => onSelectSession(s)}
          isToday={row.isToday}
        />
      ))}
    </>
  );
}

function SessionRow({ session, date, weekday, day, showDate, theme, onClick, isToday }) {
  const hours = (m) => {
    const h = Math.floor(m/60); const r = m%60;
    return h > 0 ? `${h}h${String(r).padStart(2,'0')}` : `${r} min`;
  };

  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', width: '100%',
        padding: '13px 20px',
        background: 'transparent',
        border: 'none',
        borderBottom: `0.5px solid ${theme.hairline2}`,
        cursor: 'pointer',
        textAlign: 'left',
        fontFamily: 'Space Grotesk',
      }}
    >
      {/* Date column */}
      <div style={{ width: 58, flexShrink: 0 }}>
        {showDate && (
          <div style={{
            fontSize: 11, fontWeight: 500,
            color: isToday ? theme.accent : theme.textSec,
            letterSpacing: 0.4,
            fontVariantNumeric: 'tabular-nums',
            lineHeight: 1.4,
          }}>
            <div>{weekday}</div>
            <div style={{
              fontSize: 15, fontWeight: 500,
              color: isToday ? theme.accent : theme.text,
              letterSpacing: -0.3, marginTop: 1,
            }}>{day}</div>
          </div>
        )}
      </div>

      {/* Icon */}
      <div style={{
        width: 32, height: 32, flexShrink: 0,
        borderRadius: 8,
        background: theme.surface2,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginRight: 12,
      }}>
        <DiscIcon type={session.type} theme={theme} size={18} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 14, fontWeight: 500, color: theme.text,
          letterSpacing: -0.2, lineHeight: 1.25,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{session.name}</div>
        <div style={{
          fontSize: 11, fontWeight: 400, color: theme.textTer,
          letterSpacing: 0.2, textTransform: 'uppercase',
          marginTop: 2,
        }}>{typeLabel(session.type)}{session.dist ? ` · ${session.dist} km` : ''}</div>
      </div>

      {/* Metrics */}
      <div style={{
        textAlign: 'right', flexShrink: 0,
        fontVariantNumeric: 'tabular-nums',
      }}>
        <div style={{
          fontSize: 14, fontWeight: 500, color: theme.text,
          letterSpacing: -0.3, lineHeight: 1.25,
        }}>{hours(session.dur)}</div>
        <div style={{
          fontSize: 11, fontWeight: 400, color: theme.textTer,
          letterSpacing: 0.2, marginTop: 2,
        }}>{session.load} charge</div>
      </div>
    </button>
  );
}

function typeLabel(type) {
  return { run: 'Course', lift: 'Muscu', bike: 'Vélo', swim: 'Natation' }[type] || type;
}

// ─────── Day detail drawer (used from Calendar) ───────
function DayDetail({ dayKey, theme, onClose }) {
  if (!dayKey) return null;
  const { byDate, fmt, todayKey } = window.TRAINING_DATA;
  const sessions = byDate[dayKey] || [];
  const [y, m, d] = dayKey.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  const dayLabel = date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
  const isToday = dayKey === todayKey;

  // Totals
  let vol = 0, load = 0;
  sessions.forEach(s => { vol += s.dur; load += s.load; });
  const hours = (x) => x > 0 ? `${Math.floor(x/60)}h${String(x%60).padStart(2,'0')}` : '—';

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'absolute', inset: 0, zIndex: 100,
          background: 'rgba(0,0,0,0.25)',
          animation: 'fadeIn 160ms ease-out',
        }}
      />
      {/* Sheet */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 101,
        background: theme.surface,
        borderTopLeftRadius: 18, borderTopRightRadius: 18,
        padding: '10px 20px 28px',
        maxHeight: '72%',
        overflowY: 'auto',
        fontFamily: 'Space Grotesk',
        animation: 'slideUp 220ms cubic-bezier(0.2, 0.8, 0.2, 1)',
      }}>
        {/* Handle */}
        <div style={{
          width: 36, height: 4, background: theme.textQuad,
          borderRadius: 2, margin: '0 auto 16px',
        }} />

        {/* Title */}
        <div style={{ marginBottom: 18 }}>
          <div style={{
            fontSize: 11, fontWeight: 500, color: isToday ? theme.accent : theme.textTer,
            letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 4,
          }}>{isToday ? "Aujourd'hui" : 'Jour'}</div>
          <div style={{
            fontSize: 22, fontWeight: 500, color: theme.text,
            letterSpacing: -0.5, textTransform: 'capitalize',
          }}>{dayLabel}</div>
        </div>

        {/* Day totals */}
        {sessions.length > 0 && (
          <div style={{
            display: 'flex', gap: 0,
            padding: '14px 0',
            borderTop: `0.5px solid ${theme.hairline}`,
            borderBottom: `0.5px solid ${theme.hairline}`,
            marginBottom: 16,
          }}>
            <MiniStat label="Séances" value={sessions.length} theme={theme} />
            <div style={{ width: 0.5, background: theme.hairline }} />
            <MiniStat label="Volume" value={hours(vol)} theme={theme} />
            <div style={{ width: 0.5, background: theme.hairline }} />
            <MiniStat label="Charge" value={load} theme={theme} />
          </div>
        )}

        {/* Sessions */}
        {sessions.length === 0 ? (
          <div style={{
            padding: '24px 0',
            fontSize: 14, color: theme.textSec,
            letterSpacing: -0.1,
            textAlign: 'center',
          }}>
            Récupération. Pas de séance prévue.
          </div>
        ) : sessions.map(s => (
          <SessionDetail key={s.id} session={s} theme={theme} />
        ))}
      </div>
    </>
  );
}

function MiniStat({ label, value, theme }) {
  return (
    <div style={{ flex: 1, textAlign: 'center' }}>
      <div style={{
        fontSize: 10, fontWeight: 500, color: theme.textTer,
        letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 4,
      }}>{label}</div>
      <div style={{
        fontSize: 17, fontWeight: 500, color: theme.text,
        letterSpacing: -0.4,
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}

function SessionDetail({ session, theme }) {
  const hours = (m) => {
    const h = Math.floor(m/60); const r = m%60;
    return h > 0 ? `${h}h${String(r).padStart(2,'0')}` : `${r} min`;
  };

  return (
    <div style={{
      padding: '14px 0',
      borderBottom: `0.5px solid ${theme.hairline2}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 9,
          background: theme.surface2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <DiscIcon type={session.type} theme={theme} size={20} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 15, fontWeight: 500, color: theme.text,
            letterSpacing: -0.2,
          }}>{session.name}</div>
          <div style={{
            fontSize: 11, fontWeight: 400, color: theme.textTer,
            letterSpacing: 0.2, textTransform: 'uppercase', marginTop: 2,
          }}>{typeLabel(session.type)}</div>
        </div>
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0,
      }}>
        <MetricCell label="Durée" value={hours(session.dur)} theme={theme} />
        <MetricCell label="Charge" value={session.load} theme={theme} />
        <MetricCell label="RPE" value={`${session.rpe}/10`} theme={theme} />
        <MetricCell label="Distance" value={session.dist ? `${session.dist} km` : '—'} theme={theme} />
      </div>
    </div>
  );
}

function MetricCell({ label, value, theme }) {
  return (
    <div>
      <div style={{
        fontSize: 10, fontWeight: 500, color: theme.textTer,
        letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 3,
      }}>{label}</div>
      <div style={{
        fontSize: 14, fontWeight: 500, color: theme.text,
        letterSpacing: -0.2,
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}

Object.assign(window, { CalendarView, ListView, DayDetail });
