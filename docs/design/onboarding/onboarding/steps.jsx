// Resilio+ Onboarding — 5 steps, React components
// Depends on window.TOKENS

const { useState, useMemo } = React;

// ─────────────────────────────────────────────────────────────
// Shared primitives
// ─────────────────────────────────────────────────────────────
function ProgressDots({ step, total = 5, t }) {
  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      {Array.from({ length: total }).map((_, i) => {
        const active = i <= step;
        return (
          <div key={i} style={{
            height: 3,
            width: 28,
            borderRadius: 2,
            background: active ? t.accent : t.border,
            transition: 'background 0.2s ease',
          }} />
        );
      })}
    </div>
  );
}

function TopBar({ step, total, onBack, onSkip, showSkip, t }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '14px 20px 10px',
    }}>
      <button onClick={onBack} disabled={step === 0} style={{
        background: 'transparent', border: 'none', padding: '8px 2px',
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 14,
        fontWeight: 400, color: step === 0 ? t.border : t.textSub,
        cursor: step === 0 ? 'default' : 'pointer', letterSpacing: -0.1,
      }}>← Retour</button>
      <ProgressDots step={step} total={total} t={t} />
      <button onClick={onSkip} style={{
        background: 'transparent', border: 'none', padding: '8px 2px',
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 14,
        fontWeight: 400, color: showSkip ? t.textSub : 'transparent',
        cursor: showSkip ? 'pointer' : 'default', letterSpacing: -0.1,
        pointerEvents: showSkip ? 'auto' : 'none',
      }}>Passer</button>
    </div>
  );
}

function Header({ title, sub, t, stepLabel }) {
  return (
    <div style={{ padding: '28px 24px 24px' }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
        color: t.textMuted, letterSpacing: 0.8, textTransform: 'uppercase',
        marginBottom: 14,
      }}>{stepLabel}</div>
      <h1 style={{
        fontFamily: 'Space Grotesk, sans-serif',
        fontSize: 30, fontWeight: 500, lineHeight: 1.08,
        letterSpacing: -0.8, color: t.text, margin: 0,
      }}>{title}</h1>
      {sub && <p style={{
        fontFamily: 'Space Grotesk, sans-serif',
        fontSize: 15, lineHeight: 1.42, color: t.textSub,
        margin: '10px 0 0', letterSpacing: -0.2, maxWidth: 320,
      }}>{sub}</p>}
    </div>
  );
}

function PrimaryButton({ children, onClick, disabled, t }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      width: '100%', height: 54, borderRadius: 14,
      background: disabled ? t.border : t.accent,
      color: disabled ? t.textMuted : t.accentText,
      fontFamily: 'Space Grotesk, sans-serif',
      fontSize: 16, fontWeight: 500, letterSpacing: -0.2,
      border: 'none', cursor: disabled ? 'default' : 'pointer',
      transition: 'background 0.15s ease',
    }}>{children}</button>
  );
}

function BottomBar({ children, t }) {
  return (
    <div style={{
      padding: '14px 20px 28px',
      borderTop: `1px solid ${t.border}`,
      background: t.bg,
    }}>{children}</div>
  );
}

// Field label + input
function Field({ label, hint, children, t }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <label style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5,
        color: t.textMuted, letterSpacing: 0.8, textTransform: 'uppercase',
      }}>{label}</label>
      {children}
      {hint && <div style={{
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 12,
        color: t.textMuted, lineHeight: 1.4, letterSpacing: -0.1,
      }}>{hint}</div>}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, suffix, t, numeric }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      height: 52, borderRadius: 12,
      background: t.surface,
      border: `1px solid ${t.border}`,
      padding: '0 14px',
    }}>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        inputMode={numeric ? 'decimal' : 'text'}
        style={{
          flex: 1, background: 'transparent', border: 'none', outline: 'none',
          fontFamily: numeric ? 'JetBrains Mono, monospace' : 'Space Grotesk, sans-serif',
          fontSize: 17, fontWeight: 400, color: t.text, letterSpacing: -0.2,
          fontVariantNumeric: 'tabular-nums',
        }}
      />
      {suffix && <span style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 13,
        color: t.textMuted, marginLeft: 6,
      }}>{suffix}</span>}
    </div>
  );
}

function SegmentedControl({ options, value, onChange, t, compact }) {
  return (
    <div style={{
      display: 'flex', padding: 3, borderRadius: 10,
      background: t.overlay, border: `1px solid ${t.border}`,
      gap: 2,
    }}>
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button key={opt.value} onClick={() => onChange(opt.value)} style={{
            flex: 1, height: compact ? 34 : 40,
            borderRadius: 8, border: 'none', cursor: 'pointer',
            background: active ? t.surface : 'transparent',
            color: active ? t.text : t.textSub,
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: compact ? 13 : 14, fontWeight: active ? 500 : 400,
            letterSpacing: -0.1,
            boxShadow: active ? (t.bg === '#17161A' ? '0 1px 2px rgba(0,0,0,0.3)' : '0 1px 2px rgba(0,0,0,0.06)') : 'none',
            transition: 'all 0.15s ease',
          }}>{opt.label}</button>
        );
      })}
    </div>
  );
}

// Single-rectangle date input — 3 inline segments, no visible dividers, one rectangle
function DateSegmentedInput({ data, setData, t }) {
  const baseInput = {
    background: 'transparent', border: 'none', outline: 'none',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 17, fontWeight: 400, color: t.text,
    fontVariantNumeric: 'tabular-nums', textAlign: 'center',
    minWidth: 0,
  };
  const sepStyle = {
    fontFamily: 'JetBrains Mono, monospace', fontSize: 17,
    color: t.textMuted, userSelect: 'none',
  };
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      height: 52, borderRadius: 12,
      background: t.surface, border: `1px solid ${t.border}`,
      padding: '0 14px',
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
        color: t.textMuted, letterSpacing: 0.4, marginRight: 10, flexShrink: 0,
      }}>JJ/MM/AAAA</div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 2 }}>
        <input
          value={data.dobDay}
          onChange={(e) => setData({ ...data, dobDay: e.target.value.replace(/\D/g, '').slice(0, 2) })}
          placeholder="14" inputMode="numeric" maxLength={2}
          style={{ ...baseInput, width: 28 }}
        />
        <span style={sepStyle}>/</span>
        <input
          value={data.dobMonth}
          onChange={(e) => setData({ ...data, dobMonth: e.target.value.replace(/\D/g, '').slice(0, 2) })}
          placeholder="03" inputMode="numeric" maxLength={2}
          style={{ ...baseInput, width: 28 }}
        />
        <span style={sepStyle}>/</span>
        <input
          value={data.dobYear}
          onChange={(e) => setData({ ...data, dobYear: e.target.value.replace(/\D/g, '').slice(0, 4) })}
          placeholder="1992" inputMode="numeric" maxLength={4}
          style={{ ...baseInput, width: 52 }}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 1 — Profil athlète
// ─────────────────────────────────────────────────────────────

// Unit toggle — tiny inline pill that swaps between two units
function UnitToggle({ value, options, onChange, t }) {
  return (
    <div style={{
      display: 'inline-flex', padding: 2, borderRadius: 7,
      background: t.overlay, border: `1px solid ${t.border}`, gap: 2,
    }}>
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button key={opt.value} onClick={() => onChange(opt.value)} style={{
            height: 22, padding: '0 8px', borderRadius: 5, border: 'none', cursor: 'pointer',
            background: active ? t.surface : 'transparent',
            color: active ? t.text : t.textMuted,
            fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5,
            fontWeight: active ? 500 : 400, letterSpacing: 0.3,
            boxShadow: active ? (t.bg === '#17161A' ? '0 1px 2px rgba(0,0,0,0.3)' : '0 1px 2px rgba(0,0,0,0.06)') : 'none',
            transition: 'all 0.12s ease',
          }}>{opt.label}</button>
        );
      })}
    </div>
  );
}

// Field variant with a trailing control (unit toggle) aligned to the label row
function FieldWithControl({ label, control, hint, children, t }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <label style={{
          fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5,
          color: t.textMuted, letterSpacing: 0.8, textTransform: 'uppercase',
        }}>{label}</label>
        {control}
      </div>
      {children}
      {hint && <div style={{
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 12,
        color: t.textMuted, lineHeight: 1.4, letterSpacing: -0.1,
      }}>{hint}</div>}
    </div>
  );
}

function Step1({ data, setData, t }) {
  return (
    <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <Field label="Prénom" t={t}>
        <TextInput value={data.firstName} onChange={(v) => setData({ ...data, firstName: v })} placeholder="Julien" t={t} />
      </Field>

      <Field label="Date de naissance" t={t}>
        <DateSegmentedInput data={data} setData={setData} t={t} />
      </Field>

      <Field label="Genre biologique" hint="Utilisé pour calibrer les calculs énergétiques (DEJ, EA, seuils)." t={t}>
        <SegmentedControl
          options={[{ value: 'F', label: 'Femme' }, { value: 'M', label: 'Homme' }]}
          value={data.sex}
          onChange={(v) => setData({ ...data, sex: v })}
          t={t}
        />
      </Field>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <FieldWithControl
          label="Taille"
          control={
            <UnitToggle
              value={data.heightUnit}
              options={[{ value: 'cm', label: 'cm' }, { value: 'ft', label: 'ft·in' }]}
              onChange={(u) => setData({ ...data, heightUnit: u })}
              t={t}
            />
          }
          t={t}
        >
          {data.heightUnit === 'cm' ? (
            <TextInput
              value={data.height}
              onChange={(v) => setData({ ...data, height: v })}
              placeholder="178"
              suffix="cm"
              t={t}
              numeric
            />
          ) : (
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <TextInput
                  value={data.heightFt}
                  onChange={(v) => setData({ ...data, heightFt: v })}
                  placeholder="5"
                  suffix="ft"
                  t={t}
                  numeric
                />
              </div>
              <div style={{ flex: 1 }}>
                <TextInput
                  value={data.heightIn}
                  onChange={(v) => setData({ ...data, heightIn: v })}
                  placeholder="10"
                  suffix="in"
                  t={t}
                  numeric
                />
              </div>
            </div>
          )}
        </FieldWithControl>

        <FieldWithControl
          label="Poids"
          control={
            <UnitToggle
              value={data.weightUnit}
              options={[{ value: 'kg', label: 'kg' }, { value: 'lbs', label: 'lbs' }]}
              onChange={(u) => setData({ ...data, weightUnit: u })}
              t={t}
            />
          }
          t={t}
        >
          <TextInput
            value={data.weight}
            onChange={(v) => setData({ ...data, weight: v })}
            placeholder={data.weightUnit === 'kg' ? '72' : '159'}
            suffix={data.weightUnit}
            t={t}
            numeric
          />
        </FieldWithControl>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 2 — Sports
// ─────────────────────────────────────────────────────────────
const SPORTS = [
  { id: 'run', name: 'Course', meta: 'Running · Trail' },
  { id: 'lift', name: 'Musculation', meta: 'Force · Hypertrophie' },
  { id: 'bike', name: 'Vélo', meta: 'Route · Gravel · Home trainer' },
  { id: 'swim', name: 'Natation', meta: 'Piscine · Eau libre' },
];

function SportGlyph({ id, t, selected }) {
  const c = selected ? t.accent : t.textSub;
  const sw = 1.6;
  const common = { fill: 'none', stroke: c, strokeWidth: sw, strokeLinecap: 'round', strokeLinejoin: 'round' };
  if (id === 'run') return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <circle cx="16" cy="4.5" r="1.8" {...common} />
      <path d="M8 21l3-5 3 2 2-4-3-3 3-3 3 2" {...common} />
      <path d="M4 14l3-1 2 3" {...common} />
    </svg>
  );
  if (id === 'lift') return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <path d="M3 12h2M19 12h2" {...common} />
      <rect x="5" y="8" width="2.5" height="8" rx="0.6" {...common} />
      <rect x="16.5" y="8" width="2.5" height="8" rx="0.6" {...common} />
      <path d="M7.5 12h9" {...common} />
    </svg>
  );
  if (id === 'bike') return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <circle cx="5.5" cy="17" r="3.5" {...common} />
      <circle cx="18.5" cy="17" r="3.5" {...common} />
      <path d="M5.5 17l4-7h6l3 7M9.5 10l3 5M15 5h-2l2.5 5" {...common} />
    </svg>
  );
  if (id === 'swim') return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      <circle cx="7" cy="7.5" r="1.8" {...common} />
      <path d="M2 18c2 0 2-1.5 4-1.5s2 1.5 4 1.5 2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5" {...common} />
      <path d="M9 13l3-2 4 2.5 4-4" {...common} />
    </svg>
  );
}

function SportCard({ sport, selected, onToggle, t }) {
  return (
    <button onClick={onToggle} style={{
      width: '100%', textAlign: 'left', cursor: 'pointer',
      background: selected ? t.accentSoft : t.surface,
      border: `1px solid ${selected ? t.accent : t.border}`,
      borderRadius: 14, padding: '16px 16px',
      display: 'flex', alignItems: 'center', gap: 14,
      transition: 'all 0.15s ease',
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10,
        background: selected ? t.surface : t.bg,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: `1px solid ${t.border}`,
      }}>
        <SportGlyph id={sport.id} t={t} selected={selected} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{
          fontFamily: 'Space Grotesk, sans-serif', fontSize: 16,
          fontWeight: 500, color: t.text, letterSpacing: -0.2,
        }}>{sport.name}</div>
        <div style={{
          fontFamily: 'Space Grotesk, sans-serif', fontSize: 12.5,
          color: t.textMuted, marginTop: 2, letterSpacing: -0.1,
        }}>{sport.meta}</div>
      </div>
      <Checkbox checked={selected} t={t} />
    </button>
  );
}

function Checkbox({ checked, t }) {
  return (
    <div style={{
      width: 22, height: 22, borderRadius: 6,
      background: checked ? t.accent : 'transparent',
      border: `1.5px solid ${checked ? t.accent : t.borderStrong}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      transition: 'all 0.15s ease',
    }}>
      {checked && (
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path d="M2.5 6.5l2.5 2.5 5-5.5" fill="none" stroke={t.accentText} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      )}
    </div>
  );
}

function Step2({ data, setData, t }) {
  const toggle = (id) => {
    const has = data.sports.includes(id);
    if (has) setData({ ...data, sports: data.sports.filter((s) => s !== id) });
    else setData({ ...data, sports: [...data.sports, id] });
  };
  return (
    <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      {SPORTS.map((s) => (
        <SportCard key={s.id} sport={s} selected={data.sports.includes(s.id)} onToggle={() => toggle(s.id)} t={t} />
      ))}
      <div style={{
        marginTop: 6,
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 12,
        color: t.textMuted, letterSpacing: -0.1,
      }}>
        {data.sports.length} sélectionné{data.sports.length > 1 ? 's' : ''} · minimum 1
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 3 — Niveau
// ─────────────────────────────────────────────────────────────
const LEVELS = [
  { value: 'beg', label: 'Débutant' },
  { value: 'int', label: 'Inter.' },
  { value: 'adv', label: 'Avancé' },
  { value: 'eli', label: 'Élite' },
];

function Step3({ data, setData, t }) {
  const selected = data.sports.length ? data.sports : ['run'];
  return (
    <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 22 }}>
      {selected.map((id) => {
        const sport = SPORTS.find((s) => s.id === id);
        const level = data.levels[id] || 'int';
        const years = data.years[id] || '';
        return (
          <div key={id} style={{
            background: t.surface,
            border: `1px solid ${t.border}`,
            borderRadius: 14, padding: '16px 16px 18px',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              marginBottom: 14,
            }}>
              <SportGlyph id={id} t={t} selected={false} />
              <div style={{
                fontFamily: 'Space Grotesk, sans-serif', fontSize: 16,
                fontWeight: 500, color: t.text, letterSpacing: -0.2,
              }}>{sport.name}</div>
            </div>
            <SegmentedControl
              options={LEVELS}
              value={level}
              onChange={(v) => setData({ ...data, levels: { ...data.levels, [id]: v } })}
              t={t}
              compact
            />
            <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                fontFamily: 'JetBrains Mono, monospace', fontSize: 10.5,
                color: t.textMuted, letterSpacing: 0.8, textTransform: 'uppercase',
                flex: 1,
              }}>Années de pratique <span style={{ textTransform: 'none', letterSpacing: 0 }}>— optionnel</span></div>
              <div style={{ width: 90 }}>
                <TextInput
                  value={years}
                  onChange={(v) => setData({ ...data, years: { ...data.years, [id]: v } })}
                  placeholder="—"
                  suffix="ans"
                  t={t}
                  numeric
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 4 — Objectif
// ─────────────────────────────────────────────────────────────
const GOALS = [
  { id: 'perf', title: 'Performance compétitive', meta: 'Pic de forme sur objectif daté' },
  { id: 'hypertrophy', title: 'Hypertrophie et force', meta: 'Masse musculaire, 1RM, volume' },
  { id: 'endurance', title: 'Endurance et VO2max', meta: 'Seuils, économie, TID' },
  { id: 'health', title: 'Santé et longévité', meta: 'HRV, sommeil, charge soutenable' },
  { id: 'body', title: 'Composition corporelle', meta: 'Déficit maîtrisé, EA préservée' },
];

function RadioCard({ goal, selected, onSelect, t }) {
  return (
    <button onClick={onSelect} style={{
      width: '100%', textAlign: 'left', cursor: 'pointer',
      background: selected ? t.accentSoft : t.surface,
      border: `1px solid ${selected ? t.accent : t.border}`,
      borderRadius: 14, padding: '16px 16px',
      display: 'flex', alignItems: 'center', gap: 14,
      transition: 'all 0.15s ease',
    }}>
      <div style={{ flex: 1 }}>
        <div style={{
          fontFamily: 'Space Grotesk, sans-serif', fontSize: 16,
          fontWeight: 500, color: t.text, letterSpacing: -0.2,
        }}>{goal.title}</div>
        <div style={{
          fontFamily: 'Space Grotesk, sans-serif', fontSize: 12.5,
          color: t.textMuted, marginTop: 3, letterSpacing: -0.1,
        }}>{goal.meta}</div>
      </div>
      <div style={{
        width: 22, height: 22, borderRadius: '50%',
        border: `1.5px solid ${selected ? t.accent : t.borderStrong}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all 0.15s ease',
      }}>
        {selected && <div style={{ width: 10, height: 10, borderRadius: '50%', background: t.accent }} />}
      </div>
    </button>
  );
}

function Step4({ data, setData, t }) {
  return (
    <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 8 }}>
      {GOALS.map((g) => (
        <RadioCard key={g.id} goal={g} selected={data.goal === g.id} onSelect={() => setData({ ...data, goal: g.id })} t={t} />
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// STEP 5 — Connecteurs
// ─────────────────────────────────────────────────────────────
function ServiceGlyph({ id, t }) {
  const c = t.text;
  const common = { fill: 'none', stroke: c, strokeWidth: 1.5, strokeLinecap: 'round', strokeLinejoin: 'round' };
  if (id === 'apple') return (
    <svg width="22" height="22" viewBox="0 0 22 22">
      <path d="M11 6c0-2 1.5-3.5 3.5-3.8C14.3 4 13 5.5 11 6z" fill={c} />
      <path d="M15 8.2c-1.2-.6-2.3-.6-3 0-.6.4-1.3.5-2 0-1.2-.9-3.4-.8-4.6 1C3.8 11.5 4.5 15 6 17.5c.7 1.2 1.7 2.5 3 2.5 1 0 1.4-.6 2.5-.6s1.5.6 2.5.6c1.3 0 2.2-1.2 3-2.4.9-1.4 1.3-2.7 1.3-2.8-.1 0-2.5-1-2.3-3.8z" fill={c} />
    </svg>
  );
  if (id === 'strava') return (
    <svg width="22" height="22" viewBox="0 0 22 22">
      <path d="M9 3l-5 10h3l2-4 2 4h3L9 3z" {...common} />
      <path d="M12 13l2 4 2-4h-1.5L14 14.8 12.5 13H12z" {...common} />
    </svg>
  );
  if (id === 'hevy') return (
    <svg width="22" height="22" viewBox="0 0 22 22">
      <rect x="3" y="9" width="2" height="4" rx="0.5" {...common} />
      <rect x="17" y="9" width="2" height="4" rx="0.5" {...common} />
      <rect x="6" y="7" width="2" height="8" rx="0.6" {...common} />
      <rect x="14" y="7" width="2" height="8" rx="0.6" {...common} />
      <path d="M8 11h6" {...common} />
    </svg>
  );
}

const SERVICES = [
  { id: 'apple', name: 'Apple Health', meta: 'Sommeil, HRV, FC, activité' },
  { id: 'strava', name: 'Strava', meta: 'Sorties course et vélo' },
  { id: 'hevy', name: 'Hevy', meta: 'Sessions musculation' },
];

function ConnectorCard({ service, connected, onToggle, t }) {
  return (
    <div style={{
      background: t.surface,
      border: `1px solid ${connected ? t.accent : t.border}`,
      borderRadius: 14, padding: '16px 16px',
      display: 'flex', alignItems: 'center', gap: 14,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10,
        background: t.bg,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: `1px solid ${t.border}`,
      }}>
        <ServiceGlyph id={service.id} t={t} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontFamily: 'Space Grotesk, sans-serif', fontSize: 15.5,
          fontWeight: 500, color: t.text, letterSpacing: -0.2,
        }}>{service.name}</div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, marginTop: 3,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: connected ? t.accent : t.textMuted,
          }} />
          <div style={{
            fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
            color: connected ? t.textSub : t.textMuted, letterSpacing: 0.3,
          }}>{connected ? 'Connecté' : 'Non connecté'}</div>
        </div>
      </div>
      <button onClick={onToggle} style={{
        height: 36, padding: '0 14px', borderRadius: 10,
        background: connected ? 'transparent' : t.surface,
        border: `1px solid ${connected ? t.border : t.borderStrong}`,
        color: connected ? t.textSub : t.text,
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 13.5, fontWeight: 500,
        cursor: 'pointer', letterSpacing: -0.1,
        transition: 'all 0.15s ease',
      }}>{connected ? 'Déconnecter' : 'Connecter'}</button>
    </div>
  );
}

function Step5({ data, setData, t }) {
  const toggle = (id) => {
    const has = data.connectors.includes(id);
    if (has) setData({ ...data, connectors: data.connectors.filter((s) => s !== id) });
    else setData({ ...data, connectors: [...data.connectors, id] });
  };
  return (
    <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      {SERVICES.map((s) => (
        <ConnectorCard key={s.id} service={s} connected={data.connectors.includes(s.id)} onToggle={() => toggle(s.id)} t={t} />
      ))}
      <div style={{
        marginTop: 10, padding: '12px 14px',
        borderRadius: 10,
        background: t.overlay,
        border: `1px solid ${t.border}`,
        fontFamily: 'Space Grotesk, sans-serif', fontSize: 12.5,
        color: t.textSub, letterSpacing: -0.1, lineHeight: 1.45,
      }}>
        Tu pourras connecter plus tard depuis les réglages. Les données historiques seront importées rétroactivement sur 90 jours.
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Orchestrator
// ─────────────────────────────────────────────────────────────
const DEFAULT_DATA = {
  firstName: '',
  dobDay: '', dobMonth: '', dobYear: '',
  sex: 'M',
  weight: '', weightUnit: 'kg',
  height: '', heightUnit: 'cm',
  heightFt: '', heightIn: '',
  sports: ['run', 'lift'],
  levels: { run: 'int', lift: 'adv', bike: 'beg', swim: 'beg' },
  years: { run: '6', lift: '4' },
  goal: 'endurance',
  connectors: ['apple'],
};

const STEP_CONFIG = [
  { title: 'Parle-nous de toi.', sub: 'Données nécessaires pour calibrer ton profil physiologique et tes cibles d\'entraînement.', label: 'Étape 01 · Profil' },
  { title: 'Quelles disciplines ?', sub: 'Tes sports actifs. Tu pourras en ajouter ou en retirer plus tard.', label: 'Étape 02 · Sports' },
  { title: 'Ton niveau.', sub: 'Sert à ajuster les volumes de base et les zones de travail.', label: 'Étape 03 · Niveau' },
  { title: 'Ton objectif dominant ?', sub: 'Un seul objectif principal. Les agents équilibreront les disciplines autour de ce cap.', label: 'Étape 04 · Objectif' },
  { title: 'Connecte tes sources de données.', sub: 'Plus de données, plus de précision. Aucune source n\'est obligatoire.', label: 'Étape 05 · Connecteurs' },
];

function OnboardingFlow({ mode = 'light', initialStep = 0 }) {
  const t = window.TOKENS[mode];
  const [step, setStep] = useState(initialStep);
  const [data, setData] = useState(DEFAULT_DATA);

  const canProceed = useMemo(() => {
    if (step === 0) {
      const hasHeight = data.heightUnit === 'cm' ? data.height : (data.heightFt && data.heightIn);
      return data.firstName && data.weight && hasHeight && data.dobYear;
    }
    if (step === 1) return data.sports.length >= 1;
    if (step === 2) return true;
    if (step === 3) return !!data.goal;
    if (step === 4) return true;
    return true;
  }, [step, data]);

  const next = () => setStep((s) => Math.min(s + 1, 4));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  const cfg = STEP_CONFIG[step];
  const isLast = step === 4;
  const showSkip = step === 4; // skip on connectors only

  return (
    <div style={{
      width: '100%', height: '100%', background: t.bg,
      display: 'flex', flexDirection: 'column',
      paddingTop: 58, // below status bar
      WebkitFontSmoothing: 'antialiased',
    }}>
      <TopBar step={step} total={5} onBack={back} onSkip={next} showSkip={showSkip} t={t} />
      <Header title={cfg.title} sub={cfg.sub} stepLabel={cfg.label} t={t} />
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {step === 0 && <Step1 data={data} setData={setData} t={t} />}
        {step === 1 && <Step2 data={data} setData={setData} t={t} />}
        {step === 2 && <Step3 data={data} setData={setData} t={t} />}
        {step === 3 && <Step4 data={data} setData={setData} t={t} />}
        {step === 4 && <Step5 data={data} setData={setData} t={t} />}
      </div>
      <BottomBar t={t}>
        <PrimaryButton onClick={next} disabled={!canProceed && !isLast} t={t}>
          {isLast ? 'Terminer' : 'Suivant'}
        </PrimaryButton>
      </BottomBar>
    </div>
  );
}

Object.assign(window, { OnboardingFlow, STEP_CONFIG });
