// app.jsx — design canvas assembly for Resilio+ Séance du jour.
// One viewport, 8 artboards: {Prescription, Exécution} × {Course, Lifting} × {Light, Dark}

const FRAME_W = 390;
const FRAME_H = 844;

function PhoneFrame({ theme, children }) {
  // custom bezel — darker/lighter depending on theme, status bar + home bar baked in
  const bezel = theme.dark ? '#0A0908' : '#1A1613';
  const island = '#000';
  return (
    <div style={{
      width: FRAME_W + 14, height: FRAME_H + 14,
      borderRadius: 56, padding: 7, background: bezel,
      boxShadow: theme.dark
        ? '0 30px 60px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.04)'
        : '0 30px 60px rgba(28,22,12,0.16), 0 0 0 1px rgba(0,0,0,0.08)',
      position: 'relative',
    }}>
      <div style={{
        width: FRAME_W, height: FRAME_H, borderRadius: 50, overflow: 'hidden',
        background: theme.bg, position: 'relative',
      }}>
        {/* status bar */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: 44,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 28px', zIndex: 10, pointerEvents: 'none',
        }}>
          <span style={{
            fontFamily: T.font, fontSize: 14, fontWeight: 600,
            color: theme.ink, ...T.tabular,
          }}>9:41</span>
          <div style={{display:'flex', gap:5, alignItems:'center'}}>
            {/* signal */}
            <svg width="17" height="11" viewBox="0 0 17 11"><rect x="0" y="7" width="3" height="4" rx="0.5" fill={theme.ink}/><rect x="4.5" y="4.5" width="3" height="6.5" rx="0.5" fill={theme.ink}/><rect x="9" y="2" width="3" height="9" rx="0.5" fill={theme.ink}/><rect x="13.5" y="0" width="3" height="11" rx="0.5" fill={theme.ink}/></svg>
            {/* battery */}
            <svg width="25" height="12" viewBox="0 0 25 12"><rect x="0.5" y="0.5" width="21" height="11" rx="3" fill="none" stroke={theme.ink} strokeOpacity="0.4"/><rect x="2" y="2" width="18" height="8" rx="1.8" fill={theme.ink}/><path d="M23 4v4c0.7-0.2 1.2-1 1.2-2S23.7 4.2 23 4Z" fill={theme.ink} fillOpacity="0.4"/></svg>
          </div>
        </div>
        {/* dynamic island */}
        <div style={{
          position:'absolute', top: 11, left:'50%', transform:'translateX(-50%)',
          width: 116, height: 34, borderRadius: 20, background: island, zIndex: 11,
        }}/>
        {/* screen content (offset for status bar) */}
        <div style={{paddingTop: 44, height: '100%', boxSizing:'border-box'}}>
          {children}
        </div>
        {/* home indicator */}
        <div style={{
          position:'absolute', left:'50%', bottom:8, transform:'translateX(-50%)',
          width: 134, height: 5, borderRadius: 3,
          background: theme.dark ? 'rgba(243,239,230,0.7)' : 'rgba(24,22,19,0.3)',
          zIndex: 20,
        }}/>
      </div>
    </div>
  );
}

function ScreenCell({ label, theme, children }) {
  return (
    <div style={{flexShrink:0}} data-screen-label={label}>
      <div style={{
        fontFamily: "'Space Grotesk', sans-serif", fontSize: 11,
        color: 'rgba(40,30,20,0.6)',
        textTransform:'uppercase', letterSpacing:'0.16em',
        marginBottom:14, fontWeight:500,
      }}>{label}</div>
      <PhoneFrame theme={theme}>{children}</PhoneFrame>
    </div>
  );
}

function App() {
  const [tweaks, setTweaks] = React.useState(window.__RESILIO_TWEAKS);
  React.useEffect(() => {
    const h = e => setTweaks({...window.__RESILIO_TWEAKS});
    window.addEventListener('resilio-tweak', h);
    return () => window.removeEventListener('resilio-tweak', h);
  }, []);

  const themes = {
    light: makeTheme(false, tweaks.accent),
    dark:  makeTheme(true,  tweaks.accent),
  };
  const activeThemes = tweaks.theme === 'light' ? ['light']
                    : tweaks.theme === 'dark' ? ['dark']
                    : ['light', 'dark'];
  const activeSports = tweaks.sport === 'run' ? ['run']
                    : tweaks.sport === 'lift' ? ['lift']
                    : ['run', 'lift'];
  const activeModes  = tweaks.mode  === 'A'   ? ['A']
                    : tweaks.mode  === 'B'   ? ['B']
                    : ['A', 'B'];

  const sportLabel = s => s === 'run' ? 'Course' : 'Musculation';
  const themeLabel = t => t === 'light' ? 'Light' : 'Dark';

  return (
    <DesignCanvas minScale={0.08} maxScale={2}>
      {/* Title header */}
      <div style={{padding:'0 60px 18px'}}>
        <div style={{
          fontFamily: "'Space Grotesk', sans-serif", fontSize:10, fontWeight:500,
          textTransform:'uppercase', letterSpacing:'0.2em',
          color:'rgba(40,30,20,0.5)', marginBottom:8,
        }}>Resilio+ · v0.3 exploration</div>
        <div style={{
          fontFamily: "'Space Grotesk', sans-serif", fontSize:32, fontWeight:500,
          letterSpacing:-0.8, color:'rgba(20,15,10,0.9)',
        }}>Séance du jour</div>
        <div style={{
          fontFamily: "'Space Grotesk', sans-serif", fontSize:14, fontWeight:400,
          color:'rgba(40,30,20,0.6)', marginTop:4, maxWidth:720,
        }}>Deux modes, même ancre visuelle. Prescription : lecture +
        justification coach. Exécution : tâche unique, grosses cibles
        tabular, feedback en temps réel. Accent unique réservé à l'action primaire.</div>
      </div>

      {/* Mode A sections */}
      {activeModes.includes('A') && (
        <DCSection title="Mode A — Prescription" subtitle="Avant démarrage : pourquoi, quoi, combien.">
          {activeSports.flatMap(sport =>
            activeThemes.map(themeKey => (
              <ScreenCell
                key={`A-${sport}-${themeKey}`}
                label={`${sportLabel(sport)} · ${themeLabel(themeKey)}`}
                theme={themes[themeKey]}
              >
                <PrescriptionScreen theme={themes[themeKey]} sport={sport}/>
              </ScreenCell>
            ))
          )}
        </DCSection>
      )}

      {/* Mode B sections */}
      {activeModes.includes('B') && (
        <DCSection title="Mode B — Exécution live" subtitle="Pendant la séance : une info, une action, zéro chrome.">
          {activeSports.flatMap(sport =>
            activeThemes.map(themeKey => (
              <ScreenCell
                key={`B-${sport}-${themeKey}`}
                label={`${sportLabel(sport)} · ${themeLabel(themeKey)}`}
                theme={themes[themeKey]}
              >
                <ExecutionScreen theme={themes[themeKey]} sport={sport}/>
              </ScreenCell>
            ))
          )}
        </DCSection>
      )}

      {/* Principles post-its */}
      <div style={{padding:'0 60px 40px', maxWidth:920, position:'relative'}}>
        <div style={{
          fontFamily: "'Space Grotesk', sans-serif", fontSize:14, fontWeight:500,
          color:'rgba(40,30,20,0.75)', marginBottom:10,
        }}>Règles que j'ai suivies</div>
        <ul style={{
          margin:0, padding:0, listStyle:'none',
          display:'grid', gridTemplateColumns:'1fr 1fr', gap:10,
          fontFamily: "'Space Grotesk', sans-serif", fontSize:13, lineHeight:1.5,
          color:'rgba(40,30,20,0.7)',
        }}>
          <li>· Accent (vert lime) uniquement sur actions primaires. Jamais décoratif.</li>
          <li>· Sémantique green/yellow/red limitée au live physiologique (FC, allure vs cible).</li>
          <li>· Chiffres tabulaires + tracking resserré pour la lecture rapide.</li>
          <li>· Dark = charbon chaud (#141311), pas clinique. Hairlines warm-tinted.</li>
          <li>· Pas d'icône décorative. Glyphes sport monoline, 1.5px stroke.</li>
          <li>· Radius 14–18px sur cards, 10px sur inputs, jamais pill 50%.</li>
        </ul>
      </div>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
