// CoachChat — Head Coach chat screen for Resilio+
// HITL modal bottom sheet replaces inline option cards

const TOKENS = {
  light: {
    bg: '#F5F5F2',
    bgElev: '#FBFBF9',
    surface: '#FFFFFF',
    surfaceMuted: '#EDEBE5',
    surfaceSubtle: '#E8E5DE',
    border: 'rgba(40,32,20,0.08)',
    borderStrong: 'rgba(40,32,20,0.18)',
    text: '#1A1612',
    textMuted: '#6B645A',
    textDim: '#9B948A',
    accent: '#B8552E',
    accentSoft: 'rgba(184,85,46,0.08)',
    accentBorder: 'rgba(184,85,46,0.28)',
    online: '#3C9A5F',
    userBubble: 'rgba(184,85,46,0.10)',
    userBubbleText: '#1A1612',
  },
  dark: {
    bg: '#1A1715',
    bgElev: '#211E1B',
    surface: '#26231F',
    surfaceMuted: '#2C2824',
    surfaceSubtle: '#332E29',
    border: 'rgba(245,240,230,0.08)',
    borderStrong: 'rgba(245,240,230,0.18)',
    text: '#F2EFE9',
    textMuted: '#A39B90',
    textDim: '#6B645A',
    accent: '#D97A52',
    accentSoft: 'rgba(217,122,82,0.12)',
    accentBorder: 'rgba(217,122,82,0.32)',
    online: '#4FB874',
    userBubble: '#3A3530',
    userBubbleText: '#F2EFE9',
  },
};

const ChatIcon = {
  Back: ({ color }) => (
    <svg width="11" height="18" viewBox="0 0 11 18" fill="none">
      <path d="M9.5 1.5L2 9l7.5 7.5" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  More: ({ color }) => (
    <svg width="20" height="4" viewBox="0 0 20 4" fill="none">
      <circle cx="2" cy="2" r="2" fill={color}/>
      <circle cx="10" cy="2" r="2" fill={color}/>
      <circle cx="18" cy="2" r="2" fill={color}/>
    </svg>
  ),
  Send: ({ color }) => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M8 14V2M8 2L2.5 7.5M8 2l5.5 5.5" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
};

function ChatHeader({ t }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      padding: '6px 8px 12px',
      borderBottom: `0.5px solid ${t.border}`,
      background: t.bg,
    }}>
      <button style={{
        width: 40, height: 40, border: 'none', background: 'transparent',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer', padding: 0,
      }}><ChatIcon.Back color={t.textMuted} /></button>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{
          fontSize: 16, fontWeight: 600, color: t.text,
          letterSpacing: -0.2, fontFamily: 'Space Grotesk',
        }}>Head Coach</div>
      </div>
      <button style={{
        width: 40, height: 40, border: 'none', background: 'transparent',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer', padding: 0,
      }}><ChatIcon.More color={t.textMuted} /></button>
    </div>
  );
}

function CoachAvatar({ t }) {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 999,
      background: t.surfaceSubtle,
      border: `0.5px solid ${t.borderStrong}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 10, fontWeight: 600, color: t.textMuted,
      letterSpacing: 0.3, fontFamily: 'Space Grotesk',
      flexShrink: 0,
    }}>HC</div>
  );
}

function CoachMessage({ t, children, time, showAvatar = true, continued = false }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', gap: 8,
      marginBottom: continued ? 4 : 14,
      paddingRight: 40,
    }}>
      <div style={{ width: 28, flexShrink: 0 }}>
        {showAvatar && <CoachAvatar t={t} />}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: '100%' }}>
        <div style={{
          background: t.surfaceMuted,
          color: t.text,
          padding: '10px 14px',
          borderRadius: 14,
          borderTopLeftRadius: showAvatar ? 4 : 14,
          fontSize: 15, lineHeight: '21px',
          fontFamily: 'Space Grotesk',
          letterSpacing: -0.1,
          fontFeatureSettings: '"tnum"',
        }}>{children}</div>
        {time && (
          <div style={{
            fontSize: 10.5, color: t.textDim, paddingLeft: 4,
            letterSpacing: 0.2, fontFamily: 'Space Grotesk',
          }}>{time}</div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ t, children, time }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'flex-end',
      marginBottom: 14, paddingLeft: 50,
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end', maxWidth: '100%' }}>
        <div style={{
          background: t.userBubble,
          color: t.userBubbleText,
          padding: '10px 14px',
          borderRadius: 14,
          borderBottomRightRadius: 4,
          fontSize: 15, lineHeight: '21px',
          fontFamily: 'Space Grotesk',
          letterSpacing: -0.1,
        }}>{children}</div>
        {time && (
          <div style={{
            fontSize: 10.5, color: t.textDim, paddingRight: 4,
            letterSpacing: 0.2, fontFamily: 'Space Grotesk',
          }}>{time}</div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Summary card — how answers come back into the chat
// ─────────────────────────────────────────────────────────────
function SummaryCard({ t, entries, time }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'flex-end',
      marginBottom: 14, paddingLeft: 30,
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end', maxWidth: '100%' }}>
        <div style={{
          background: t.surface,
          border: `1px solid ${t.accentBorder}`,
          borderRadius: 14,
          borderBottomRightRadius: 4,
          padding: '10px 12px 12px',
          minWidth: 220,
          fontFamily: 'Space Grotesk',
        }}>
          <div style={{
            fontSize: 10, fontWeight: 600,
            color: t.accent, letterSpacing: 0.6,
            textTransform: 'uppercase',
            marginBottom: 8,
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <svg width="10" height="10" viewBox="0 0 12 12"><path d="M2.5 6.5L5 9l4.5-5" stroke={t.accent} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
            Réponses envoyées
          </div>
          {entries.map((e, i) => (
            <div key={i} style={{
              paddingTop: i === 0 ? 0 : 8,
              paddingBottom: i === entries.length - 1 ? 0 : 8,
              borderBottom: i === entries.length - 1 ? 'none' : `0.5px solid ${t.border}`,
            }}>
              <div style={{
                fontSize: 11, color: t.textMuted,
                letterSpacing: -0.05, marginBottom: 3,
                lineHeight: '14px',
              }}>{e.question}</div>
              <div style={{
                fontSize: 14, color: t.text,
                fontWeight: 500, letterSpacing: -0.1,
                lineHeight: '19px',
              }}>{e.answer}</div>
            </div>
          ))}
        </div>
        {time && (
          <div style={{
            fontSize: 10.5, color: t.textDim, paddingRight: 4,
            letterSpacing: 0.2, fontFamily: 'Space Grotesk',
          }}>{time}</div>
        )}
      </div>
    </div>
  );
}

function Typing({ t }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', gap: 8,
      marginBottom: 14, paddingRight: 40,
    }}>
      <CoachAvatar t={t} />
      <div style={{
        background: t.surfaceMuted,
        padding: '12px 14px',
        borderRadius: 14, borderTopLeftRadius: 4,
        display: 'flex', gap: 4, alignItems: 'center',
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 5, height: 5, borderRadius: 999,
            background: t.textDim,
            animation: `coachDot 1.2s ease-in-out ${i * 0.15}s infinite`,
          }} />
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Input bar
// ─────────────────────────────────────────────────────────────
function InputBar({ t, value, onChange, onSend, quickPrompts, onQuickPrompt, disabled }) {
  const ta = React.useRef(null);
  const canSend = !disabled && value.trim().length > 0;

  React.useEffect(() => {
    if (ta.current) {
      ta.current.style.height = 'auto';
      const h = Math.min(ta.current.scrollHeight, 4 * 20 + 20);
      ta.current.style.height = h + 'px';
    }
  }, [value]);

  return (
    <div style={{
      background: t.bg,
      borderTop: `0.5px solid ${t.border}`,
      padding: '10px 12px 8px',
      opacity: disabled ? 0.5 : 1,
      transition: 'opacity 200ms ease',
    }}>
      {quickPrompts.length > 0 && (
        <div style={{
          display: 'flex', gap: 8, overflowX: 'auto',
          paddingBottom: 10, marginLeft: -12, marginRight: -12,
          paddingLeft: 12, paddingRight: 12,
          scrollbarWidth: 'none',
        }}>
          {quickPrompts.map((qp, i) => (
            <button
              key={i}
              onClick={() => !disabled && onQuickPrompt(qp)}
              style={{
                flexShrink: 0,
                background: t.surface,
                border: `1px solid ${t.border}`,
                borderRadius: 999,
                padding: '7px 13px',
                fontSize: 12.5, color: t.text,
                fontFamily: 'Space Grotesk',
                fontWeight: 500,
                letterSpacing: -0.05,
                cursor: disabled ? 'default' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >{qp}</button>
          ))}
        </div>
      )}
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 8,
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: 22,
        padding: '6px 6px 6px 14px',
      }}>
        <textarea
          ref={ta}
          value={value}
          onChange={e => onChange(e.target.value)}
          disabled={disabled}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (canSend) onSend();
            }
          }}
          placeholder="Écris au coach…"
          rows={1}
          style={{
            flex: 1, border: 'none', outline: 'none', resize: 'none',
            background: 'transparent', color: t.text,
            fontSize: 15, fontFamily: 'Space Grotesk',
            lineHeight: '20px', padding: '7px 0',
            letterSpacing: -0.1,
            maxHeight: 100,
          }}
        />
        <button
          onClick={() => canSend && onSend()}
          disabled={!canSend}
          style={{
            width: 32, height: 32, borderRadius: 999,
            background: canSend ? t.accent : t.surfaceSubtle,
            border: 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: canSend ? 'pointer' : 'default',
            transition: 'background 160ms ease',
            flexShrink: 0,
          }}
        ><ChatIcon.Send color={canSend ? '#FBFBF9' : t.textDim} /></button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Scenarios
// ─────────────────────────────────────────────────────────────
const SCENARIOS = {
  hrv: {
    initialMessages: [
      { id: 'm1', role: 'coach', time: '08:42',
        text: "Ton HRV a chuté de 18% sur 24h. Ta séance de seuil prévue demain risque d'être contre-productive." },
      { id: 'm2', role: 'coach', time: '08:42', continued: true,
        text: "J'ai besoin de deux, trois précisions avant d'ajuster ta semaine." },
    ],
    questions: [
      { id: 'q1', type: 'single',
        title: "Comment tu veux gérer la séance de demain ?",
        allowOther: true,
        options: [
          "Remplacer par Z2 (50 min, récup active)",
          "Garder la séance mais baisser en Z3",
          "Repos complet demain",
          "Décaler la séance à jeudi",
        ] },
      { id: 'q2', type: 'multi',
        title: "Quels signaux tu ressens en ce moment ?",
        subtitle: "Plusieurs réponses possibles.",
        allowOther: true,
        options: [
          "Sommeil perturbé",
          "Jambes lourdes",
          "Stress pro/perso élevé",
          "Nutrition sous-optimale",
          "Aucun signal particulier",
        ] },
      { id: 'q3', type: 'rank',
        title: "Classe tes priorités cette semaine",
        options: [
          "Course à pied",
          "Musculation",
          "Récupération",
          "Vélo",
          "Natation",
        ] },
    ],
    coachReply: (answers) => {
      const a1 = answers[0];
      let line = "Noté.";
      if (!a1.skipped && a1.answer?.index === 0) line = "Noté. Sortie Z2 de 50 min demain, 6:10/km.";
      else if (!a1.skipped && a1.answer?.index === 1) line = "Noté. Ajusté pour 45 min Z3, allure 5:15/km.";
      else if (!a1.skipped && a1.answer?.index === 2) line = "Noté. Repos complet demain.";
      else if (!a1.skipped && a1.answer?.index === 3) line = "Noté. Seuil décalé à jeudi, recovery demain.";
      return line + " Je recalcule ta semaine en fonction de tes priorités. ACWR cible 1.1.";
    },
  },
  week: {
    initialMessages: [
      { id: 'm1', role: 'coach', time: '07:15',
        text: "Je planifie ta semaine. Quelques questions pour caler le mésocycle." },
    ],
    questions: [
      { id: 'w1', type: 'single',
        title: "Objectif principal cette semaine",
        options: [
          "Volume en Z2 (base aérobie)",
          "Qualité (seuil, VO2max)",
          "Force et puissance",
          "Semaine de décharge",
        ] },
      { id: 'w2', type: 'multi',
        title: "Disciplines à intégrer",
        allowOther: true,
        options: [
          "Course à pied",
          "Vélo",
          "Natation",
          "Musculation lourde",
          "Mobilité",
        ] },
      { id: 'w3', type: 'rank',
        title: "Contraintes à prioriser",
        options: [
          "Temps disponible",
          "Fatigue accumulée",
          "Récupération musculaire",
          "Sommeil",
        ] },
    ],
    coachReply: () => "Planning généré. 4 séances clés, 280 TSS, ACWR 1.08. Tu peux ouvrir le calendrier pour valider.",
  },
};

// ─────────────────────────────────────────────────────────────
// Answer formatters
// ─────────────────────────────────────────────────────────────
function formatAnswer(question, answer, skipped) {
  if (skipped || !answer) return { label: question.title, value: "— passé —" };
  if (question.type === 'single') {
    const val = answer.index === -1
      ? answer.other
      : question.options[answer.index];
    return { question: question.title, answer: val };
  }
  if (question.type === 'multi') {
    const picked = (answer.indices || []).map(i => question.options[i]);
    if (answer.otherSelected && answer.other?.trim()) picked.push(answer.other);
    return { question: question.title, answer: picked.join(' · ') };
  }
  if (question.type === 'rank') {
    const ordered = answer.order.map(i => question.options[i]);
    return { question: question.title, answer: ordered.map((o, i) => `${i + 1}. ${o}`).join('  ') };
  }
  return { question: question.title, answer: '—' };
}

// ─────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────
function CoachChat({ dark = false, initialScenario = 'hrv' }) {
  const t = dark ? TOKENS.dark : TOKENS.light;
  const scen = SCENARIOS[initialScenario] || SCENARIOS.hrv;

  const [messages, setMessages] = React.useState(scen.initialMessages);
  const [input, setInput] = React.useState('');
  const [typing, setTyping] = React.useState(false);
  const [sheetOpen, setSheetOpen] = React.useState(false);
  const [sheetDismissed, setSheetDismissed] = React.useState(false);
  const scrollerRef = React.useRef(null);

  // Auto-open sheet after initial coach messages
  React.useEffect(() => {
    const timer = setTimeout(() => {
      if (!sheetDismissed) setSheetOpen(true);
    }, 900);
    return () => clearTimeout(timer);
  }, []);

  React.useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [messages, typing]);

  const handleSheetSubmit = (results) => {
    setSheetOpen(false);
    setSheetDismissed(true);
    const entries = results
      .map(r => formatAnswer(r.question, r.answer, r.skipped))
      .filter(e => e.answer && e.answer !== "— passé —");

    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: 'summary-' + Date.now(), role: 'summary',
        entries, time: formatTime(new Date()),
      }]);
      setTyping(true);
    }, 260);

    setTimeout(() => {
      setTyping(false);
      setMessages(prev => [...prev, {
        id: 'c-' + Date.now(), role: 'coach', time: formatTime(new Date()),
        text: scen.coachReply(results),
      }]);
    }, 1700);
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    setMessages(prev => [...prev, {
      id: 'u' + Date.now(), role: 'user', time: formatTime(new Date()), text,
    }]);
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMessages(prev => [...prev, {
        id: 'c' + Date.now(), role: 'coach', time: formatTime(new Date()),
        text: canaryReply(text),
      }]);
    }, 1400);
  };

  const decoratedMessages = messages.map((m, i) => {
    if (m.role !== 'coach') return m;
    const prev = messages[i - 1];
    const showAvatar = !prev || prev.role !== 'coach';
    return { ...m, showAvatar };
  });

  const quickPrompts = ['Adapte ma semaine', 'Pourquoi cette séance ?', 'Je me sens fatigué'];

  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      background: t.bg, color: t.text,
      fontFamily: 'Space Grotesk',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <ChatHeader t={t} />

      <div
        ref={scrollerRef}
        style={{
          flex: 1, overflowY: 'auto',
          padding: '16px 16px 8px',
        }}
      >
        <div style={{
          textAlign: 'center', fontSize: 11, color: t.textDim,
          letterSpacing: 0.4, textTransform: 'uppercase',
          padding: '4px 0 16px',
        }}>Aujourd'hui</div>

        {decoratedMessages.map(m => {
          if (m.role === 'coach') {
            return (
              <CoachMessage key={m.id} t={t}
                time={m.time} showAvatar={m.showAvatar} continued={m.continued}
              >{m.text}</CoachMessage>
            );
          }
          if (m.role === 'user') {
            return <UserMessage key={m.id} t={t} time={m.time}>{m.text}</UserMessage>;
          }
          if (m.role === 'summary') {
            return <SummaryCard key={m.id} t={t} entries={m.entries} time={m.time} />;
          }
          return null;
        })}

        {typing && <Typing t={t} />}
      </div>

      <InputBar
        t={t}
        value={input}
        onChange={setInput}
        onSend={handleSend}
        quickPrompts={quickPrompts}
        onQuickPrompt={setInput}
        disabled={sheetOpen}
      />

      <HITLSheet
        t={t} dark={dark}
        open={sheetOpen}
        questions={scen.questions}
        onSubmit={handleSheetSubmit}
        onClose={() => { setSheetOpen(false); setSheetDismissed(true); }}
      />

      {/* Re-open button if dismissed */}
      {sheetDismissed && !sheetOpen && messages.every(m => m.role !== 'summary') && (
        <button
          onClick={() => setSheetOpen(true)}
          style={{
            position: 'absolute', right: 16, bottom: 140,
            background: t.accent, color: '#FBFBF9',
            border: 'none', borderRadius: 999,
            padding: '8px 14px',
            fontSize: 12, fontWeight: 600,
            fontFamily: 'Space Grotesk', letterSpacing: 0.2,
            cursor: 'pointer',
            boxShadow: '0 6px 20px rgba(0,0,0,0.18)',
          }}
        >Reprendre les questions</button>
      )}
    </div>
  );
}

function formatTime(d) {
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

function canaryReply(userText) {
  const lower = userText.toLowerCase();
  if (lower.includes('fatigué') || lower.includes('fatigue')) {
    return "Compris. Je baisse la charge des 48h à venir. TSS plafonné à 180, pas de séance > Z3.";
  }
  if (lower.includes('semaine') || lower.includes('adapte')) {
    return "Je recalcule ta semaine. Objectif ACWR autour de 1.1.";
  }
  if (lower.includes('pourquoi')) {
    return "Cette séance cible ton seuil lactique. Ton VDOT suggère 5:02/km pendant 4×8 min.";
  }
  return "Noté. Je regarde et je reviens vers toi.";
}

Object.assign(window, { CoachChat, TOKENS });
