// execution.jsx — Mode B: séance en cours, layout task-focused.

function ExecHeader({ theme, title, elapsed, total }) {
  return (
    <div style={{
      display:'flex', alignItems:'center', gap:12,
      padding:'14px 16px 6px',
    }}>
      <div style={{flex:1, minWidth:0}}>
        <div style={{
          ...T.smallcaps, color:theme.inkMuted, fontFamily:T.font, fontSize:10,
          marginBottom:2,
        }}>En cours</div>
        <div style={{
          fontFamily:T.font, fontSize:14, fontWeight:500, color:theme.ink,
          whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
          letterSpacing:-0.2,
        }}>{title}</div>
        <div style={{
          fontFamily:T.font, fontSize:12, color:theme.inkMuted, marginTop:3,
          ...T.tabular,
        }}>{elapsed} <span style={{color:theme.inkDim}}>/ {total}</span></div>
      </div>
      <button style={{
        width:40, height:40, borderRadius:20, border:`1px solid ${theme.hairlineStrong}`,
        background:'transparent', cursor:'pointer',
        display:'flex', alignItems:'center', justifyContent:'center',
      }}>{Ico.pause(theme.ink, 14)}</button>
    </div>
  );
}

// --- RUN execution ---

function RunExecution({ theme }) {
  return (
    <div style={{
      height:'100%', background:theme.bg, color:theme.ink,
      display:'flex', flexDirection:'column', fontFamily:T.font, position:'relative',
    }}>
      <ExecHeader theme={theme} title="Endurance fondamentale Z2" elapsed="12:34" total="52:00"/>

      {/* Phase chip row */}
      <div style={{padding:'10px 20px 4px', display:'flex', alignItems:'center', gap:8}}>
        <div style={{
          width:8, height:8, borderRadius:4, background:theme.accent,
        }}/>
        <div style={{
          ...T.smallcaps, color:theme.inkMuted, fontFamily:T.font, fontSize:10.5,
        }}>Main — Z2 · 2/3</div>
      </div>

      {/* XL target */}
      <div style={{padding:'12px 20px 0'}}>
        <div style={{
          ...T.smallcaps, color:theme.inkDim, fontFamily:T.font, fontSize:10, marginBottom:10,
        }}>Allure cible</div>
        <div style={{
          fontFamily:T.font, fontSize:88, fontWeight:500,
          letterSpacing:-3.6, lineHeight:0.95, color:theme.ink,
          ...T.tabular,
        }}>5:42<span style={{fontSize:32, color:theme.inkMuted, letterSpacing:-0.8, marginLeft:4, fontWeight:400}}>/km</span></div>
        <div style={{
          fontFamily:T.font, fontSize:12.5, color:theme.inkMuted, marginTop:8,
          ...T.tabular,
        }}>Fenêtre 5:32 – 5:52</div>
        <div style={{
          marginTop:6, display:'flex', alignItems:'baseline', gap:8,
          fontFamily:T.font, fontSize:12.5, color:theme.inkDim,
        }}>
          <span style={{
            ...T.smallcaps, fontSize:10, color:theme.inkDim,
          }}>Projection séance</span>
          <span style={{
            color:theme.inkMuted, fontWeight:500, ...T.tabular,
          }}>≈ 9,1 km</span>
          <span style={{color:theme.inkFaint}}>·</span>
          <span style={{
            color:theme.inkMuted, fontWeight:500, ...T.tabular,
          }}>52:00</span>
        </div>
      </div>

      {/* Live chips: pace + HR */}
      <div style={{
        margin:'22px 16px 18px',
        display:'grid', gridTemplateColumns:'1fr 1fr', gap:10,
      }}>
        <LiveTile theme={theme} label="Allure live" value="5:39" sub="dans la cible" status="ok"/>
        <LiveTile theme={theme} label="FC" value="148" sub="Z2 · 74% FCM" status="ok" icon={Ico.heart(theme.inkMuted, 12)}/>
      </div>

      {/* segment progress */}
      <div style={{padding:'0 20px'}}>
        <div style={{
          display:'flex', justifyContent:'space-between', alignItems:'baseline',
          fontFamily:T.font, fontSize:11, color:theme.inkMuted,
          ...T.smallcaps, marginBottom:8,
        }}>
          <span>Bloc courant</span>
          <span style={{...T.tabular, color:theme.ink, fontWeight:500}}>22:26 restant</span>
        </div>
        <SegBar theme={theme} pct={0.36}/>
      </div>

      {/* next up */}
      <div style={{margin:'20px 16px 0'}}>
        <div style={{
          padding:'14px 16px', background:theme.bgElev2, borderRadius:14,
          display:'flex', alignItems:'center', gap:14,
        }}>
          <div style={{
            ...T.smallcaps, color:theme.inkDim, fontFamily:T.font, fontSize:10,
          }}>Suivant</div>
          <div style={{flex:1, fontFamily:T.font, fontSize:13, color:theme.ink}}>
            Cool-down · <span style={{...T.tabular}}>7 min</span> · Z1
          </div>
        </div>
      </div>

      <div style={{flex:1}}/>
      <ExecFooter theme={theme}/>
    </div>
  );
}

function LiveTile({ theme, label, value, sub, status, icon }) {
  const statusColor = status === 'ok' ? theme.green : status === 'drift' ? theme.yellow : theme.red;
  return (
    <div style={{
      padding:'13px 15px 15px', background:theme.bgElev, borderRadius:14,
      border:`1px solid ${theme.hairline}`,
    }}>
      <div style={{
        display:'flex', alignItems:'center', gap:6, marginBottom:6,
        ...T.smallcaps, color:theme.inkDim, fontFamily:T.font, fontSize:10,
      }}>
        {icon}
        <span>{label}</span>
      </div>
      <div style={{
        fontFamily:T.font, fontSize:28, fontWeight:500, color:theme.ink,
        letterSpacing:-0.8, ...T.tabular, lineHeight:1,
      }}>{value}</div>
      <div style={{
        marginTop:6, fontFamily:T.font, fontSize:11.5,
        color: statusColor, fontWeight:500,
        display:'flex', alignItems:'center', gap:5,
      }}>
        <span style={{
          width:6, height:6, borderRadius:3, background: statusColor,
        }}/>
        {sub}
      </div>
    </div>
  );
}

function SegBar({ theme, pct }) {
  return (
    <div style={{
      height:4, background:theme.hairline, borderRadius:2, overflow:'hidden',
    }}>
      <div style={{
        width:`${pct*100}%`, height:'100%', background:theme.ink,
      }}/>
    </div>
  );
}

// --- LIFT execution ---

function LiftExecution({ theme }) {
  return (
    <div style={{
      height:'100%', background:theme.bg, color:theme.ink,
      display:'flex', flexDirection:'column', fontFamily:T.font, position:'relative',
    }}>
      <ExecHeader theme={theme} title="Force — haut du corps A" elapsed="18:47" total="≈ 48:00"/>

      {/* exercise label */}
      <div style={{padding:'14px 20px 0'}}>
        <div style={{
          display:'flex', alignItems:'center', gap:8, marginBottom:12,
        }}>
          <div style={{
            ...T.smallcaps, color:theme.inkMuted, fontFamily:T.font, fontSize:10.5,
          }}>Exercice 02 / 05</div>
        </div>
        <div style={{
          fontFamily:T.font, fontSize:36, fontWeight:500, color:theme.ink,
          letterSpacing:-1.1, lineHeight:1.02,
        }}>Développé couché</div>
        <div style={{
          marginTop:8, fontFamily:T.font, fontSize:13, color:theme.inkMuted,
          ...T.tabular,
        }}>
          4 × 6 @ RPE 8 · Tempo 3-0-1-0
        </div>
      </div>

      {/* set marker + weight */}
      <div style={{
        margin:'22px 16px 0', padding:'18px 18px 16px',
        background:theme.bgElev, borderRadius:18, border:`1px solid ${theme.hairline}`,
      }}>
        <div style={{
          display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:14,
        }}>
          <div style={{...T.smallcaps, color:theme.inkMuted, fontFamily:T.font, fontSize:10.5}}>
            Set courant
          </div>
          <div style={{
            fontFamily:T.font, fontSize:13, color:theme.ink, fontWeight:500,
            ...T.tabular,
          }}>Set 2 / 4</div>
        </div>
        <SetDots theme={theme} total={4} done={1} current={1}/>
        <div style={{
          marginTop:18, display:'flex', gap:24, alignItems:'baseline',
        }}>
          <div>
            <div style={{...T.smallcaps, fontSize:10, color:theme.inkDim, marginBottom:3}}>Charge</div>
            <div style={{
              fontFamily:T.font, fontSize:40, fontWeight:500, color:theme.ink,
              letterSpacing:-1.2, ...T.tabular, lineHeight:1,
            }}>72<span style={{fontSize:18, color:theme.inkMuted, marginLeft:2, fontWeight:400, letterSpacing:0}}>kg</span></div>
          </div>
          <div>
            <div style={{...T.smallcaps, fontSize:10, color:theme.inkDim, marginBottom:3}}>Répétitions</div>
            <div style={{
              fontFamily:T.font, fontSize:40, fontWeight:500, color:theme.ink,
              letterSpacing:-1.2, ...T.tabular, lineHeight:1,
            }}>6</div>
          </div>
        </div>
      </div>

      {/* RPE quick segmented */}
      <div style={{margin:'18px 16px 0'}}>
        <div style={{...T.smallcaps, fontSize:10, color:theme.inkDim, marginBottom:8, fontFamily:T.font}}>
          RPE du set précédent
        </div>
        <div style={{
          display:'grid', gridTemplateColumns:'repeat(5, 1fr)', gap:6,
        }}>
          {[6,7,8,9,10].map(n=>(
            <button key={n} style={{
              height:42, borderRadius:10,
              background: n===8 ? theme.ink : 'transparent',
              color: n===8 ? theme.bg : theme.inkMuted,
              border: `1px solid ${n===8 ? theme.ink : theme.hairlineStrong}`,
              fontFamily:T.font, fontSize:14, fontWeight: n===8 ? 600 : 500,
              ...T.tabular, cursor:'pointer',
            }}>{n}</button>
          ))}
        </div>
      </div>

      {/* Rest timer card */}
      <div style={{margin:'20px 16px 0'}}>
        <div style={{
          padding:'14px 18px', background:theme.bgElev2, borderRadius:14,
          display:'flex', alignItems:'center', gap:16,
        }}>
          <div style={{
            ...T.smallcaps, color:theme.inkDim, fontFamily:T.font, fontSize:10,
          }}>Repos</div>
          <div style={{
            fontFamily:T.font, fontSize:22, fontWeight:500, color:theme.ink,
            ...T.tabular, letterSpacing:-0.4, lineHeight:1,
          }}>01:47<span style={{fontSize:12, color:theme.inkDim, fontWeight:400, marginLeft:6}}>/ 02:30</span></div>
          <div style={{flex:1}}/>
          <div style={{
            fontFamily:T.font, fontSize:11.5, color:theme.inkMuted,
            ...T.smallcaps,
          }}>auto</div>
        </div>
      </div>

      <div style={{flex:1}}/>
      <LiftFooter theme={theme}/>
    </div>
  );
}

function SetDots({ theme, total, done, current }) {
  return (
    <div style={{display:'flex', gap:8}}>
      {Array.from({length:total}).map((_,i)=>{
        let bg, border, ink;
        if (i < done) { bg = theme.ink; border = theme.ink; ink = theme.bg; }
        else if (i === current) { bg = 'transparent'; border = theme.ink; ink = theme.ink; }
        else { bg = 'transparent'; border = theme.hairlineStrong; ink = theme.inkDim; }
        return (
          <div key={i} style={{
            flex:1, height:44, borderRadius:10,
            background:bg, border:`1px solid ${border}`,
            display:'flex', alignItems:'center', justifyContent:'center', gap:4,
            fontFamily:T.font, fontSize:13, fontWeight:500, color:ink,
            ...T.tabular,
          }}>
            {i < done ? Ico.check(ink, 12) : `Set ${i+1}`}
          </div>
        );
      })}
    </div>
  );
}

// --- Footers ---

function ExecFooter({ theme }) {
  return (
    <div style={{
      padding:'12px 16px 30px', display:'flex', gap:10,
    }}>
      <button style={{
        flex:1, height:52, border:`1px solid ${theme.hairlineStrong}`,
        background:'transparent', color:theme.inkMuted,
        fontFamily:T.font, fontSize:14, fontWeight:500,
        borderRadius:14, cursor:'pointer',
      }}>Terminer la séance</button>
      <button style={{
        width:52, height:52, border:`1px solid ${theme.hairlineStrong}`,
        background:'transparent', color:theme.ink,
        borderRadius:14, cursor:'pointer',
        display:'flex', alignItems:'center', justifyContent:'center',
      }}>{Ico.pause(theme.ink, 14)}</button>
    </div>
  );
}

function LiftFooter({ theme }) {
  return (
    <div style={{padding:'12px 16px 30px'}}>
      <div style={{display:'flex', gap:10}}>
        <button style={{
          flex:6, height:56, border:'none',
          background: theme.accent, color: theme.accentInk,
          fontFamily:T.font, fontSize:16, fontWeight:600, letterSpacing:-0.2,
          borderRadius:16, cursor:'pointer',
          display:'flex', alignItems:'center', justifyContent:'center', gap:8,
        }}>
          {Ico.check(theme.accentInk, 14)}
          <span>Set terminé</span>
        </button>
        <button style={{
          flex:2, height:56, border:`1px solid ${theme.hairlineStrong}`,
          background:'transparent', color:theme.inkMuted,
          fontFamily:T.font, fontSize:13, fontWeight:500,
          borderRadius:16, cursor:'pointer',
        }}>Skip</button>
      </div>
      <button style={{
        marginTop:8, width:'100%', height:40, background:'transparent',
        border:'none', color:theme.inkMuted,
        fontFamily:T.font, fontSize:12.5, letterSpacing:'0.12em',
        textTransform:'uppercase', fontWeight:500, cursor:'pointer',
      }}>Terminer la séance</button>
    </div>
  );
}

function ExecutionScreen({ theme, sport }) {
  return sport === 'run' ? <RunExecution theme={theme}/> : <LiftExecution theme={theme}/>;
}

Object.assign(window, { ExecutionScreen });
