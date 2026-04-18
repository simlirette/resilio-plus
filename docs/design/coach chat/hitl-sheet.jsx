// HITL Bottom Sheet — Claude-inspired question modal
// Supports: single_select, multi_select, rank_priorities
// Slides up from bottom, replaces input, per-question skip, "something else"

function SheetIcon({ name, color, size = 14 }) {
  if (name === 'arrow-right') return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M3 8h10M9 4l4 4-4 4" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
  if (name === 'chev-l') return (
    <svg width="8" height="12" viewBox="0 0 8 12" fill="none">
      <path d="M6 1L1 6l5 5" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
  if (name === 'chev-r') return (
    <svg width="8" height="12" viewBox="0 0 8 12" fill="none">
      <path d="M2 1l5 5-5 5" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
  if (name === 'x') return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M2 2l8 8M10 2l-8 8" stroke={color} strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
  if (name === 'check') return (
    <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
      <path d="M2.5 6.5L5 9l4.5-5" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
  if (name === 'edit') return (
    <svg width="12" height="12" viewBox="0 0 13 13" fill="none">
      <path d="M9 2l2 2-7 7H2v-2l7-7z" stroke={color} strokeWidth="1.4" strokeLinejoin="round"/>
    </svg>
  );
  if (name === 'drag') return (
    <svg width="10" height="14" viewBox="0 0 10 14" fill="none">
      <circle cx="3" cy="3" r="1" fill={color}/>
      <circle cx="7" cy="3" r="1" fill={color}/>
      <circle cx="3" cy="7" r="1" fill={color}/>
      <circle cx="7" cy="7" r="1" fill={color}/>
      <circle cx="3" cy="11" r="1" fill={color}/>
      <circle cx="7" cy="11" r="1" fill={color}/>
    </svg>
  );
  return null;
}

// ─────────────────────────────────────────────────────────────
// Row primitive — numbered or checkbox, selectable
// ─────────────────────────────────────────────────────────────
function OptionRow({ t, index, label, kind, selected, onClick, isLast }) {
  // kind: 'single' | 'multi' | 'rank'
  const numeral = (
    <div style={{
      width: 28, height: 28, borderRadius: 7,
      background: selected && kind === 'single' ? t.text : 'transparent',
      border: `1px solid ${selected && kind === 'single' ? t.text : t.borderStrong}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12, fontWeight: 500,
      color: selected && kind === 'single' ? t.bg : t.textMuted,
      fontFeatureSettings: '"tnum"',
      flexShrink: 0,
    }}>{index + 1}</div>
  );

  const check = (
    <div style={{
      width: 22, height: 22, borderRadius: 6,
      background: selected ? t.accent : 'transparent',
      border: `1.5px solid ${selected ? t.accent : t.borderStrong}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      {selected && <SheetIcon name="check" color="#FBFBF9" />}
    </div>
  );

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '14px 4px',
        cursor: 'pointer',
        borderBottom: isLast ? 'none' : `0.5px solid ${t.border}`,
        background: selected && kind === 'single' ? t.surfaceMuted : 'transparent',
        borderRadius: selected && kind === 'single' ? 10 : 0,
        margin: selected && kind === 'single' ? '0 -8px' : 0,
        paddingLeft: selected && kind === 'single' ? 12 : 4,
        paddingRight: selected && kind === 'single' ? 12 : 4,
        transition: 'background 120ms ease',
      }}
    >
      {kind === 'multi' ? check : numeral}
      <div style={{
        flex: 1, fontSize: 15, color: t.text,
        fontWeight: selected && kind === 'single' ? 600 : 500,
        letterSpacing: -0.1,
        fontFamily: 'Space Grotesk',
      }}>{label}</div>
      {kind === 'single' && selected && (
        <SheetIcon name="arrow-right" color={t.text} size={14} />
      )}
      {kind === 'rank' && (
        <SheetIcon name="drag" color={t.textDim} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// "Something else" input row
// ─────────────────────────────────────────────────────────────
function SomethingElseRow({ t, kind, value, onChange, selected, onSelect }) {
  const showCheck = kind === 'multi';
  return (
    <div
      onClick={onSelect}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '14px 12px',
        marginTop: 4,
        borderTop: `0.5px solid ${t.border}`,
        background: selected ? t.surfaceMuted : 'transparent',
        borderRadius: 10,
        marginLeft: -8, marginRight: -8,
        transition: 'background 120ms ease',
      }}
    >
      {showCheck ? (
        <div style={{
          width: 22, height: 22, borderRadius: 6,
          background: selected && value.trim() ? t.accent : 'transparent',
          border: `1.5px solid ${selected && value.trim() ? t.accent : t.borderStrong}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {selected && value.trim() && <SheetIcon name="check" color="#FBFBF9" />}
        </div>
      ) : (
        <div style={{ width: 28, display: 'flex', justifyContent: 'center' }}>
          <SheetIcon name="edit" color={t.textDim} />
        </div>
      )}
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={onSelect}
        placeholder="Autre chose"
        style={{
          flex: 1, border: 'none', outline: 'none',
          background: 'transparent', color: t.text,
          fontSize: 15, fontFamily: 'Space Grotesk',
          letterSpacing: -0.1,
        }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Rank row — drag handle + up/down arrows fallback
// ─────────────────────────────────────────────────────────────
function RankRow({ t, index, total, label, onMove, isDragging, onDragStart, onDragEnter, onDragEnd }) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnter={onDragEnter}
      onDragEnd={onDragEnd}
      onDragOver={e => e.preventDefault()}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '14px 4px',
        borderBottom: index === total - 1 ? 'none' : `0.5px solid ${t.border}`,
        cursor: 'grab',
        background: isDragging ? t.surfaceMuted : 'transparent',
        borderRadius: isDragging ? 10 : 0,
        opacity: isDragging ? 0.7 : 1,
        transition: 'background 120ms ease',
      }}
    >
      <div style={{
        width: 28, height: 28, borderRadius: 7,
        border: `1px solid ${t.borderStrong}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 500, color: t.textMuted,
        fontFeatureSettings: '"tnum"',
        flexShrink: 0,
      }}>{index + 1}</div>
      <div style={{
        flex: 1, fontSize: 15, color: t.text,
        fontWeight: 500, letterSpacing: -0.1,
        fontFamily: 'Space Grotesk',
      }}>{label}</div>
      <div style={{ padding: 6, cursor: 'grab' }}>
        <SheetIcon name="drag" color={t.textDim} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Single question body
// ─────────────────────────────────────────────────────────────
function QuestionBody({ t, q, answer, setAnswer }) {
  const [rankOrder, setRankOrder] = React.useState(
    answer && answer.order ? answer.order : q.options.map((_, i) => i)
  );
  const [dragIdx, setDragIdx] = React.useState(null);

  React.useEffect(() => {
    if (q.type === 'rank') {
      setAnswer({ order: rankOrder });
    }
  }, [rankOrder]);

  if (q.type === 'single') {
    const selIdx = answer?.index ?? null;
    const otherText = answer?.other ?? '';
    return (
      <div>
        {q.options.map((opt, i) => (
          <OptionRow
            key={i} t={t} index={i} label={opt} kind="single"
            selected={selIdx === i}
            onClick={() => setAnswer({ index: i, other: '' })}
            isLast={i === q.options.length - 1 && !q.allowOther}
          />
        ))}
        {q.allowOther && (
          <SomethingElseRow
            t={t} kind="single" value={otherText}
            selected={selIdx === -1}
            onSelect={() => setAnswer({ index: -1, other: otherText })}
            onChange={v => setAnswer({ index: -1, other: v })}
          />
        )}
      </div>
    );
  }

  if (q.type === 'multi') {
    const sel = answer?.indices ?? [];
    const otherSel = answer?.otherSelected ?? false;
    const otherText = answer?.other ?? '';
    const toggle = (i) => {
      const next = sel.includes(i) ? sel.filter(x => x !== i) : [...sel, i];
      setAnswer({ indices: next, otherSelected: otherSel, other: otherText });
    };
    return (
      <div>
        {q.options.map((opt, i) => (
          <OptionRow
            key={i} t={t} index={i} label={opt} kind="multi"
            selected={sel.includes(i)}
            onClick={() => toggle(i)}
            isLast={i === q.options.length - 1 && !q.allowOther}
          />
        ))}
        {q.allowOther && (
          <SomethingElseRow
            t={t} kind="multi" value={otherText}
            selected={otherSel}
            onSelect={() => setAnswer({ indices: sel, otherSelected: !otherSel, other: otherText })}
            onChange={v => setAnswer({ indices: sel, otherSelected: true, other: v })}
          />
        )}
      </div>
    );
  }

  if (q.type === 'rank') {
    const handleDragStart = (i) => setDragIdx(i);
    const handleDragEnter = (i) => {
      if (dragIdx === null || dragIdx === i) return;
      const next = [...rankOrder];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(i, 0, moved);
      setRankOrder(next);
      setDragIdx(i);
    };
    const handleDragEnd = () => setDragIdx(null);

    return (
      <div>
        {rankOrder.map((optIdx, i) => (
          <RankRow
            key={optIdx} t={t}
            index={i} total={rankOrder.length}
            label={q.options[optIdx]}
            isDragging={dragIdx === i}
            onDragStart={() => handleDragStart(i)}
            onDragEnter={() => handleDragEnter(i)}
            onDragEnd={handleDragEnd}
          />
        ))}
      </div>
    );
  }

  return null;
}

// ─────────────────────────────────────────────────────────────
// Main sheet
// ─────────────────────────────────────────────────────────────
function HITLSheet({ t, dark, open, questions, onSubmit, onClose }) {
  const [step, setStep] = React.useState(0);
  const [answers, setAnswers] = React.useState({});
  const [skipped, setSkipped] = React.useState({});

  React.useEffect(() => {
    if (open) {
      setStep(0);
      setAnswers({});
      setSkipped({});
    }
  }, [open]);

  if (!questions || questions.length === 0) return null;

  const q = questions[step];
  const total = questions.length;
  const answer = answers[q.id];
  const isSkipped = skipped[q.id];

  const canAdvance = (() => {
    if (isSkipped) return true;
    if (!answer) return false;
    if (q.type === 'single') {
      if (answer.index === -1) return answer.other?.trim().length > 0;
      return typeof answer.index === 'number' && answer.index >= 0;
    }
    if (q.type === 'multi') {
      const hasSel = (answer.indices || []).length > 0;
      const hasOther = answer.otherSelected && answer.other?.trim().length > 0;
      return hasSel || hasOther;
    }
    if (q.type === 'rank') return true;
    return false;
  })();

  const goNext = () => {
    if (step < total - 1) setStep(step + 1);
    else finalSubmit();
  };
  const goPrev = () => { if (step > 0) setStep(step - 1); };
  const skipOne = () => {
    setSkipped(s => ({ ...s, [q.id]: true }));
    setAnswers(a => {
      const next = { ...a };
      delete next[q.id];
      return next;
    });
    setTimeout(() => goNext(), 60);
  };
  const finalSubmit = () => {
    const result = questions.map(qq => ({
      question: qq,
      skipped: !!skipped[qq.id],
      answer: answers[qq.id],
    }));
    onSubmit(result);
  };

  const setAnswer = (v) => {
    setAnswers(a => ({ ...a, [q.id]: v }));
    setSkipped(s => {
      if (!s[q.id]) return s;
      const next = { ...s };
      delete next[q.id];
      return next;
    });
  };

  // Multi-select count for footer
  const multiCount = q.type === 'multi'
    ? (answer?.indices?.length || 0) + (answer?.otherSelected && answer?.other?.trim() ? 1 : 0)
    : null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'absolute', inset: 0,
          background: dark ? 'rgba(0,0,0,0.55)' : 'rgba(26,22,18,0.45)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 260ms ease',
          zIndex: 70,
          backdropFilter: 'blur(2px)',
        }}
      />
      {/* Sheet */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        background: t.bgElev,
        borderTopLeftRadius: 20, borderTopRightRadius: 20,
        transform: open ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 340ms cubic-bezier(0.32, 0.72, 0, 1)',
        zIndex: 80,
        boxShadow: '0 -10px 40px rgba(0,0,0,0.18)',
        display: 'flex', flexDirection: 'column',
        maxHeight: '78%',
        paddingBottom: 34, // home indicator
        fontFamily: 'Space Grotesk',
      }}>
        {/* Grabber */}
        <div style={{
          display: 'flex', justifyContent: 'center', padding: '8px 0 4px',
        }}>
          <div style={{
            width: 36, height: 5, borderRadius: 999,
            background: t.borderStrong,
          }} />
        </div>

        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 16px 12px',
        }}>
          <div style={{
            flex: 1, fontSize: 17, fontWeight: 600,
            color: t.text, letterSpacing: -0.2, lineHeight: '22px',
          }}>{q.title}</div>
          {total > 1 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              color: t.textMuted, fontSize: 12,
              fontFeatureSettings: '"tnum"', letterSpacing: 0.2,
            }}>
              <button onClick={goPrev} disabled={step === 0} style={{
                background: 'transparent', border: 'none', padding: 4,
                cursor: step === 0 ? 'default' : 'pointer', opacity: step === 0 ? 0.3 : 1,
                display: 'flex', alignItems: 'center',
              }}>
                <SheetIcon name="chev-l" color={t.textMuted} />
              </button>
              <span>{step + 1} / {total}</span>
              <button onClick={canAdvance ? goNext : undefined} disabled={!canAdvance || step === total - 1} style={{
                background: 'transparent', border: 'none', padding: 4,
                cursor: (!canAdvance || step === total - 1) ? 'default' : 'pointer',
                opacity: (!canAdvance || step === total - 1) ? 0.3 : 1,
                display: 'flex', alignItems: 'center',
              }}>
                <SheetIcon name="chev-r" color={t.textMuted} />
              </button>
            </div>
          )}
          <button onClick={onClose} style={{
            width: 28, height: 28, borderRadius: 999,
            background: t.surfaceMuted, border: 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', padding: 0,
          }}>
            <SheetIcon name="x" color={t.textMuted} />
          </button>
        </div>

        {/* Subtitle if present */}
        {q.subtitle && (
          <div style={{
            padding: '0 16px 12px',
            fontSize: 13, color: t.textMuted,
            lineHeight: '18px', letterSpacing: -0.05,
          }}>{q.subtitle}</div>
        )}

        {/* Body */}
        <div style={{
          flex: 1, overflowY: 'auto',
          padding: '4px 16px 12px',
        }}>
          <QuestionBody t={t} q={q} answer={answer} setAnswer={setAnswer} />
          {q.type === 'rank' && (
            <div style={{
              fontSize: 11, color: t.textDim,
              marginTop: 10, letterSpacing: 0.2,
              textTransform: 'uppercase',
            }}>Glisse pour réordonner</div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 16px 6px',
          borderTop: `0.5px solid ${t.border}`,
        }}>
          <div style={{
            flex: 1, fontSize: 12, color: t.textMuted,
            fontFeatureSettings: '"tnum"', letterSpacing: 0.2,
          }}>
            {q.type === 'multi' && multiCount > 0 && `${multiCount} sélectionné${multiCount > 1 ? 's' : ''}`}
          </div>
          <button onClick={skipOne} style={{
            background: 'transparent',
            border: `1px solid ${t.borderStrong}`,
            borderRadius: 10,
            padding: '8px 16px',
            fontSize: 13, fontWeight: 500,
            color: t.textMuted,
            fontFamily: 'Space Grotesk',
            cursor: 'pointer', letterSpacing: -0.05,
          }}>Passer</button>
          <button
            onClick={canAdvance ? goNext : undefined}
            disabled={!canAdvance}
            style={{
              width: 40, height: 36, borderRadius: 10,
              background: canAdvance ? t.accent : t.surfaceMuted,
              border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: canAdvance ? 'pointer' : 'default',
              transition: 'background 160ms ease',
            }}
          >
            <SheetIcon
              name="arrow-right"
              color={canAdvance ? '#FBFBF9' : t.textDim}
              size={16}
            />
          </button>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { HITLSheet });
