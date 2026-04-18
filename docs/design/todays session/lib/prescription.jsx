// prescription.jsx — Mode A: séance prescrite, avant démarrage
// Header + bloc résumé + "pourquoi" + prescription détaillée + CTA fixe bas.

function HeaderBar({ theme, title, sub }) {
  return (
    <div style={{
      display:'flex', alignItems:'center', gap:8,
      padding:'12px 16px 6px',
    }}>
      <button style={{
        width:36, height:36, border:'none', background:'transparent',
        display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer',
        marginLeft:-8,
      }}>{Ico.back(theme.ink)}</button>
      <div style={{flex:1, textAlign:'center'}}>
        <div style={{
          ...T.smallcaps, color: theme.inkDim, fontFamily:T.font, marginBottom:1,
        }}>{sub}</div>
        <div style={{
          fontFamily:T.font, fontSize:15, fontWeight:500, color:theme.ink,
          letterSpacing:-0.2,
        }}>{title}</div>
      </div>
      <button style={{
        width:36, height:36, border:'none', background:'transparent',
        display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer',
      }}>{Ico.dots(theme.inkMuted)}</button>
    </div>
  );
}

function Divider({ theme, inset = 0 }) {
  return <div style={{height:1, background:theme.hairline, marginLeft:inset}}/>;
}

// --- SHARED summary block + "pourquoi" ---

function SummaryBlock({ theme, sport, title, duration, load, zone }) {
  return (
    <div style={{padding:'16px 20px 22px'}}>
      <div style={{display:'flex', alignItems:'center', gap:10, marginBottom:14}}>
        <SportIcon sport={sport} color={theme.inkMuted} size={20}/>
        <span style={{
          ...T.smallcaps, color:theme.inkMuted, fontFamily:T.font,
        }}>Séance course · Z2</span>
      </div>
      <h1 style={{
        margin:0, fontFamily:T.font, fontSize:30, fontWeight:500,
        letterSpacing:-0.9, color:theme.ink, lineHeight:1.08,
      }}>{title}</h1>
      <div style={{
        display:'flex', gap:14, marginTop:18, flexWrap:'wrap',
        fontFamily:T.font, fontSize:13.5,
      }}>
        <Meta theme={theme} label="Durée" value={duration}/>
        <MetaSep theme={theme}/>
        <Meta theme={theme} label="Charge" value={load}/>
        <MetaSep theme={theme}/>
        <Meta theme={theme} label="Intensité" value={zone}/>
      </div>
    </div>
  );
}
function Meta({theme, label, value}) {
  return (
    <div>
      <div style={{
        ...T.smallcaps, fontSize:10, color:theme.inkDim, marginBottom:3, fontFamily:T.font,
      }}>{label}</div>
      <div style={{
        color:theme.ink, fontWeight:500, ...T.tabular,
      }}>{value}</div>
    </div>
  );
}
function MetaSep({theme}) {
  return <div style={{width:1, background:theme.hairline, alignSelf:'stretch'}}/>;
}

function WhyCard({ theme, children }) {
  return (
    <div style={{
      margin:'0 20px 24px', padding:'14px 16px',
      background: theme.bgElev2, borderRadius:14,
      borderLeft: `2px solid ${theme.accent}`,
    }}>
      <div style={{
        ...T.smallcaps, color:theme.inkMuted, marginBottom:8, fontFamily:T.font, fontSize:10,
      }}>Pourquoi cette séance</div>
      <div style={{
        fontFamily:T.font, fontSize:14, lineHeight:1.55, color:theme.ink, fontWeight:400,
      }}>{children}</div>
    </div>
  );
}

// --- RUN prescription rows ---

function RunPhaseRow({ theme, phase, time, zone, pace, isLast }) {
  const zoneColor = zone === 'Z1' ? theme.inkMuted : zone === 'Z2' ? theme.ink : theme.ink;
  return (
    <div>
      <div style={{
        display:'grid', gridTemplateColumns:'56px 1fr auto', gap:14, alignItems:'baseline',
        padding:'18px 20px',
      }}>
        <div style={{
          fontFamily:T.font, fontSize:11, fontWeight:500,
          color:theme.inkDim, textTransform:'uppercase', letterSpacing:'0.14em',
          ...T.tabular,
        }}>{phase}</div>
        <div>
          <div style={{
            fontFamily:T.font, fontSize:16, fontWeight:500, color:theme.ink,
            letterSpacing:-0.2,
          }}>{pace}</div>
          <div style={{
            fontFamily:T.font, fontSize:12.5, color:theme.inkMuted, marginTop:2,
          }}>{zone === 'Z1' ? 'Allure libre · échauffement' :
               zone === 'Z2' ? 'Fondamentale · rester sous seuil' :
                                'Retour calme'}</div>
        </div>
        <div style={{
          fontFamily:T.font, fontSize:20, fontWeight:400, color:theme.ink,
          ...T.tabular, letterSpacing:-0.4,
        }}>{time}</div>
      </div>
      {!isLast && <Divider theme={theme} inset={20}/>}
    </div>
  );
}

function RunPrescription({ theme }) {
  return (
    <div>
      <SectionLabel theme={theme} title="Prescription" right="3 phases"/>
      <div style={{margin:'0 16px', background:theme.bgElev, borderRadius:18, overflow:'hidden', border:`1px solid ${theme.hairline}`}}>
        <RunPhaseRow theme={theme} phase="Warm-up" time="10 min" zone="Z1" pace="Allure libre"/>
        <RunPhaseRow theme={theme} phase="Main"    time="35 min" zone="Z2" pace="5:42/km · ±10 sec"/>
        <RunPhaseRow theme={theme} phase="Cool-down" time="7 min" zone="Z1" pace="Retour calme" isLast/>
      </div>
    </div>
  );
}

// --- LIFT prescription rows ---

function LiftExercise({ theme, index, name, scheme, tempo, note, isLast }) {
  return (
    <div>
      <div style={{padding:'16px 20px', display:'flex', gap:14}}>
        <div style={{
          width:22, textAlign:'left',
          fontFamily:T.font, fontSize:12, color:theme.inkDim, fontWeight:500,
          ...T.tabular, paddingTop:3,
        }}>{String(index).padStart(2,'0')}</div>
        <div style={{flex:1, minWidth:0}}>
          <div style={{
            fontFamily:T.font, fontSize:16, fontWeight:500, color:theme.ink,
            letterSpacing:-0.2, marginBottom:5,
          }}>{name}</div>
          <div style={{
            display:'flex', gap:16, alignItems:'center',
            fontFamily:T.font, ...T.tabular, fontSize:13, color:theme.inkMuted,
            marginBottom: note ? 8 : 0,
          }}>
            <span style={{color:theme.ink, fontWeight:500}}>{scheme}</span>
            {tempo && <span>Tempo {tempo}</span>}
          </div>
          {note && <div style={{
            fontFamily:T.font, fontSize:12.5, color:theme.inkMuted,
            lineHeight:1.45,
          }}>{note}</div>}
        </div>
        <div style={{alignSelf:'center', opacity:0.5}}>{Ico.arrowTiny(theme.inkDim)}</div>
      </div>
      {!isLast && <Divider theme={theme} inset={56}/>}
    </div>
  );
}

function LiftPrescription({ theme }) {
  const exs = [
    { name:'Squat arrière', scheme:'4 × 6 @ RPE 8', tempo:'3-1-1-0', note:'Reste sur les talons, genoux alignés.' },
    { name:'Développé couché', scheme:'4 × 6 @ RPE 8', tempo:'3-0-1-0', note:'Garde les scapulas basses et resserrées.' },
    { name:'Soulevé de terre roumain', scheme:'3 × 8 @ RPE 7', tempo:'3-1-0-0' },
    { name:'Tirage poitrine', scheme:'3 × 10 @ RPE 7' },
    { name:'Gainage face', scheme:'3 × 45 sec' },
  ];
  return (
    <div>
      <SectionLabel theme={theme} title="Prescription" right={`${exs.length} exercices`}/>
      <div style={{margin:'0 16px', background:theme.bgElev, borderRadius:18, overflow:'hidden', border:`1px solid ${theme.hairline}`}}>
        {exs.map((e,i)=>(
          <LiftExercise key={i} theme={theme} index={i+1} {...e} isLast={i===exs.length-1}/>
        ))}
      </div>
    </div>
  );
}

function SectionLabel({theme, title, right}) {
  return (
    <div style={{
      display:'flex', alignItems:'baseline', justifyContent:'space-between',
      padding:'18px 20px 10px',
    }}>
      <div style={{
        ...T.smallcaps, color:theme.inkMuted, fontFamily:T.font, fontSize:10.5,
      }}>{title}</div>
      <div style={{
        fontFamily:T.font, fontSize:11.5, color:theme.inkDim, ...T.tabular,
      }}>{right}</div>
    </div>
  );
}

// --- CTA bottom-fixed ---

function BottomCTA({ theme, label = 'Démarrer' }) {
  return (
    <div style={{
      position:'absolute', left:0, right:0, bottom:0,
      padding:'14px 16px 34px',
      background: `linear-gradient(to top, ${theme.bg} 60%, ${theme.bg}00)`,
      pointerEvents:'none',
    }}>
      <button style={{
        width:'100%', height:56, border:'none',
        background: theme.accent, color: theme.accentInk,
        fontFamily:T.font, fontSize:17, fontWeight:600, letterSpacing:-0.3,
        borderRadius:16, cursor:'pointer', pointerEvents:'auto',
        display:'flex', alignItems:'center', justifyContent:'center', gap:8,
      }}>
        {Ico.play(theme.accentInk, 12)}
        <span>{label}</span>
      </button>
    </div>
  );
}

// --- Screen ---

function PrescriptionScreen({ theme, sport }) {
  const isRun = sport === 'run';
  return (
    <div style={{
      height:'100%', background:theme.bg, color:theme.ink,
      display:'flex', flexDirection:'column', position:'relative',
      fontFamily:T.font,
    }}>
      <HeaderBar theme={theme} title="Séance" sub="SAM. 18 AVR."/>
      <div style={{flex:1, overflow:'auto', paddingBottom:120}}>
        <SummaryBlock
          theme={theme}
          sport={sport}
          title={isRun ? 'Endurance fondamentale Z2' : 'Force — haut du corps A'}
          duration={isRun ? '52 min' : '48 min'}
          load={isRun ? 'TSS 68' : 'Vol. 14t'}
          zone={isRun ? 'Z2' : 'RPE 7–8'}
        />
        <WhyCard theme={theme}>
          {isRun
            ? <>Ton <b style={{fontWeight:500}}>ACWR est à 1.12</b> et ta Readiness baisse depuis 3 jours. Z2 pur aujourd'hui pour consolider la base aérobie sans ajouter de strain neuromusculaire.</>
            : <>Ta Readiness est à 78 et ton dernier bloc force date de 4 jours. Tu peux charger sur les multi-articulaires ; on garde 2 RIR en sécurité.</>
          }
        </WhyCard>
        {isRun ? <RunPrescription theme={theme}/> : <LiftPrescription theme={theme}/>}
        {isRun && <PaceGuide theme={theme}/>}
      </div>
      <BottomCTA theme={theme}/>
    </div>
  );
}

// small extra: pace band visual under run prescription (lightweight chart)
function PaceGuide({ theme }) {
  // 50 bars representing the run shape — WU (flat low), Main (plateau), CD (decline)
  const bars = Array.from({length: 52}, (_, i) => {
    if (i < 10) return 0.30;
    if (i < 45) return 0.72 + (Math.sin(i*0.9)*0.02);
    return 0.72 - (i-44)*0.06;
  });
  return (
    <div style={{margin:'22px 16px 0'}}>
      <SectionLabel theme={theme} title="Profil de zone" right="52 min"/>
      <div style={{
        background:theme.bgElev, borderRadius:18, padding:'18px 18px 16px',
        border:`1px solid ${theme.hairline}`,
      }}>
        <div style={{
          display:'flex', alignItems:'flex-end', gap:2, height:64,
        }}>
          {bars.map((v,i)=>(
            <div key={i} style={{
              flex:1, height:`${v*100}%`, borderRadius:1.5,
              background: i<10 || i>=45 ? theme.hairlineStrong : theme.ink,
              opacity: i<10 || i>=45 ? 1 : 0.85,
            }}/>
          ))}
        </div>
        <div style={{
          display:'flex', justifyContent:'space-between', marginTop:8,
          fontFamily:T.font, fontSize:10.5, color:theme.inkDim,
          ...T.smallcaps, letterSpacing:'0.1em',
        }}>
          <span>Z1 · WU</span><span>Z2 · Main</span><span>Z1 · CD</span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { PrescriptionScreen });
