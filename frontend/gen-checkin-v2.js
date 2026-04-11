const fs = require('fs');

const iconPath = 'C:/resilio-plus/frontend/icons/';
const settings = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'settings.png').toString('base64');
const runner   = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'runner.png').toString('base64');
const biker    = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'biker.png').toString('base64');
const swimmer  = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'swimmer.png').toString('base64');

const SIDEBAR = `<div class="sidebar">
  <div class="sidebar-logo">Resilio<span class="logo-plus">+</span></div>
  <div class="nav-section">
    <div class="nav-label">Principal</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="10" rx="8" ry="5" stroke="#52525b" stroke-width="1.5" fill="none"/><circle cx="10" cy="10" r="2.5" fill="#52525b"/><circle cx="10" cy="10" r="1" fill="white"/></svg></div>Aperçu</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="3" y="4" width="14" height="12" rx="1" stroke="#52525b" stroke-width="1.4" fill="none"/><line x1="6" y1="8" x2="14" y2="8" stroke="#52525b" stroke-width="1"/><line x1="6" y1="11" x2="14" y2="11" stroke="#52525b" stroke-width="1"/></svg></div>Plan</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M12 2L5.5 11H10L8 18L15.5 8H11Z" fill="#52525b"/></svg></div>Énergie</div>
    <div class="nav-item active"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M4 10C4 6.7 6.7 4 10 4" stroke="#09090b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 6.7 13.3 4 10 4" stroke="#09090b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M4 10C4 13.3 6.7 16 10 16" stroke="#09090b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 13.3 13.3 16 10 16" stroke="#09090b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M7.5 10L9.2 11.8L12.5 8.5" stroke="#09090b" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></div>Check-in</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Données</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><line x1="3" y1="3" x2="17" y2="3" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/><line x1="3" y1="17" x2="17" y2="17" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/><path d="M5 3L10 11L15 3" fill="#52525b" opacity="0.35"/><path d="M5 3L10 11L15 3M5 17L10 11L15 17" stroke="#52525b" stroke-width="1.2" fill="none"/><path d="M5 17L10 11L15 17" fill="#52525b" opacity="0.65"/></svg></div>Historique</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="2" y="2" width="16" height="16" rx="1.5" stroke="#52525b" stroke-width="1.3" fill="none"/><rect x="5" y="12" width="2.5" height="4" rx="0.5" fill="#52525b" opacity="0.4"/><rect x="8.8" y="9.5" width="2.5" height="6.5" rx="0.5" fill="#52525b" opacity="0.7"/><rect x="12.5" y="6" width="2.5" height="10" rx="0.5" fill="#52525b"/></svg></div>Analytiques</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Compte</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="2.8" stroke="#52525b" stroke-width="1.4"/><path d="M10 2v2.5M10 15.5V18M2 10h2.5M15.5 10H18M4.4 4.4l1.77 1.77M13.83 13.83l1.77 1.77M4.4 15.6l1.77-1.77M13.83 6.17l1.77-1.77" stroke="#52525b" stroke-width="1.4" stroke-linecap="round"/></svg></div>Paramètres</div>
  </div>
  <div class="sidebar-footer">
    <div class="avatar">S</div>
    <div><div class="avatar-name">Simon</div><div class="avatar-status">Récupération optimale</div></div>
  </div>
</div>`;

function slider(label, leftLabel, rightLabel, value, color='#18181b') {
  const pct = ((value - 1) / 4) * 100;
  return `<div class="slider-group">
    <div class="slider-header">
      <span class="slider-label">${label}</span>
      <span class="slider-val" style="color:${color}">${value}<span style="color:#a1a1aa;font-weight:400">/5</span></span>
    </div>
    <div class="slider-track">
      <div class="slider-fill" style="width:${pct}%;background:${color}"></div>
      <div class="slider-thumb" style="left:${pct}%;background:${color}"></div>
    </div>
    <div class="slider-ends"><span>${leftLabel}</span><span>${rightLabel}</span></div>
  </div>`;
}

// chevron arrow SVG
const chevL = `<svg viewBox="0 0 16 16" fill="none" width="16" height="16"><path d="M10 4L6 8L10 12" stroke="#09090b" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const chevR = `<svg viewBox="0 0 16 16" fill="none" width="16" height="16"><path d="M6 4L10 8L6 12" stroke="#09090b" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Check-in</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@400;600&display=swap" rel="stylesheet">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'DM Sans',system-ui; background:#e8e8e8; display:flex; align-items:center; justify-content:center; min-height:100vh; padding:32px; }
.frame { width:1280px; height:800px; background:#fafafa; border-radius:16px; box-shadow:0 12px 64px rgba(0,0,0,0.16); display:flex; overflow:hidden; }

/* ── SIDEBAR ── */
.sidebar { width:260px; min-width:260px; background:#fff; border-right:1px solid #e4e4e7; display:flex; flex-direction:column; padding:32px 0 24px; flex-shrink:0; }
.sidebar-logo { font-family:'Playfair Display',serif; font-size:24px; color:#09090b; padding:0 28px 28px; border-bottom:1px solid #e4e4e7; }
.logo-plus { color:#16a34a; }
.nav-section { padding:20px 16px 4px; }
.nav-label { font-size:10px; text-transform:uppercase; letter-spacing:0.12em; color:#a1a1aa; padding:0 8px; margin-bottom:4px; }
.nav-item { display:flex; align-items:center; gap:10px; padding:11px 12px; border-radius:8px; font-size:14px; color:#52525b; margin-bottom:2px; border-left:2px solid transparent; }
.nav-item.active { background:#f4f4f5; color:#09090b; border-left:2px solid #18181b; font-weight:500; }
.nav-icon { width:22px; height:22px; display:flex; align-items:center; justify-content:center; flex-shrink:0; opacity:0.45; }
.nav-item.active .nav-icon { opacity:1; }
.nav-icon svg, .nav-icon img { width:18px; height:18px; object-fit:contain; }
.sidebar-footer { margin-top:auto; padding:16px 20px 0; border-top:1px solid #e4e4e7; display:flex; align-items:center; gap:12px; }
.avatar { width:36px; height:36px; border-radius:50%; background:#18181b; color:white; font-size:13px; font-weight:600; display:flex; align-items:center; justify-content:center; }
.avatar-name { font-size:13px; font-weight:500; color:#09090b; }
.avatar-status { font-size:11px; color:#16a34a; display:flex; align-items:center; gap:4px; }
.avatar-status::before { content:''; width:6px; height:6px; background:#16a34a; border-radius:50%; display:inline-block; }

/* ── MAIN ── */
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; }

/* ── PAGE HEADER ── */
.page-header { padding:20px 28px 16px; border-bottom:1px solid #e4e4e7; flex-shrink:0; display:flex; align-items:center; justify-content:space-between; gap:24px; }
.page-title { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; letter-spacing:-0.02em; flex-shrink:0; }
.checkin-status { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:20px; background:#f0fdf4; border:1px solid #bbf7d0; font-size:11px; font-weight:500; color:#16a34a; white-space:nowrap; }

/* ── DAY NAV ── */
.day-nav { display:flex; align-items:center; gap:12px; }
.day-arrow { width:32px; height:32px; border-radius:8px; border:1px solid #e4e4e7; background:#fff; display:flex; align-items:center; justify-content:center; cursor:pointer; flex-shrink:0; transition:background 0.12s; }
.day-arrow:hover { background:#f4f4f5; }
.day-arrow:disabled { opacity:0.3; cursor:default; }
.day-label { display:flex; flex-direction:column; align-items:center; min-width:160px; gap:2px; }
.day-label-row { display:flex; align-items:baseline; gap:8px; }
.day-full-name { font-family:'Playfair Display',serif; font-size:18px; color:#09090b; }
.day-full-date { font-family:'DM Mono',monospace; font-size:13px; color:#71717a; }
.day-today-badge { font-size:10px; color:#a1a1aa; letter-spacing:0.04em; }

/* ── CONTENT ── */
.content-scroll { flex:1; overflow-y:auto; display:flex; }
.content-scroll::-webkit-scrollbar { width:4px; }
.content-scroll::-webkit-scrollbar-thumb { background:#e4e4e7; border-radius:2px; }

.left-panel  { width:440px; min-width:440px; padding:22px 26px; border-right:1px solid #e4e4e7; overflow-y:auto; display:flex; flex-direction:column; gap:18px; }
.right-panel { flex:1; padding:22px 26px; overflow-y:auto; display:flex; flex-direction:column; gap:16px; }

.section-title { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:10px; }
.divider { border:none; border-top:1px solid #f4f4f5; }

/* ── SESSION CARD ── */
.session-card { background:#fff; border:1px solid #e4e4e7; border-radius:10px; overflow:hidden; transition:border-color 0.2s; }
.session-card.is-done { border-color:#bbf7d0; }

.sc-header { display:flex; align-items:center; justify-content:space-between; padding:11px 13px 11px; }
.sc-sport { display:flex; align-items:center; gap:10px; }
.sc-icon { width:40px; height:40px; border-radius:10px; background:#e4e4e7; display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }
.sc-icon img { object-fit:contain; display:block; }
.sc-icon.sport-running img { width:82%; height:82%; }
.sc-icon.sport-bike    img { width:68%; height:68%; }
.sc-icon.sport-swim    img { width:92%; height:92%; }
.sc-name { font-size:13px; font-weight:500; color:#09090b; }
.sc-time { font-family:'DM Mono',monospace; font-size:12px; color:#09090b; }
.sc-time-h { color:#a1a1aa; }
.sc-dur  { font-size:11px; color:#71717a; }

.sc-complete-btn {
  font-size:11px; font-weight:500; padding:5px 11px; border-radius:7px;
  border:1px solid #e4e4e7; background:#fff; cursor:pointer; color:#71717a;
  white-space:nowrap; transition:all 0.15s; flex-shrink:0;
  display:flex; align-items:center; gap:5px; letter-spacing:0.01em;
}
.sc-complete-btn:hover { border-color:#a1a1aa; color:#09090b; }
.sc-complete-btn.done { background:#f0fdf4; border-color:#bbf7d0; color:#16a34a; font-weight:500; }
.sc-check-icon { width:12px; height:12px; flex-shrink:0; }

/* RPE row — always visible, dimmed when not done */
.sc-rpe { padding:8px 13px 11px; display:flex; align-items:center; justify-content:space-between; border-top:1px solid #f4f4f5; }
.rpe-label { font-size:11px; color:#71717a; }
.rpe-pills { display:flex; gap:3px; }
.rpe-pill { width:22px; height:22px; border-radius:5px; border:1px solid #e4e4e7; background:#fff; font-size:10px; font-weight:600; display:flex; align-items:center; justify-content:center; cursor:pointer; color:#71717a; transition:all 0.1s; }
.rpe-pill.selected { background:#18181b; color:#fff; border-color:#18181b; }
.session-card.is-done .rpe-pill { cursor:pointer; }
.session-card:not(.is-done) .rpe-pill { opacity:0.35; pointer-events:none; }
.session-card:not(.is-done) .sc-rpe { opacity:0.6; }

/* ── SLIDERS ── */
.slider-group { margin-bottom:4px; }
.slider-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:7px; }
.slider-label { font-size:13px; font-weight:500; color:#3f3f46; }
.slider-val { font-family:'DM Mono',monospace; font-size:12px; font-weight:600; }
.slider-track { position:relative; height:5px; background:#f0f0f0; border-radius:3px; margin:0 6px; }
.slider-fill { position:absolute; top:0; left:0; height:100%; border-radius:3px; }
.slider-thumb { position:absolute; top:50%; transform:translate(-50%,-50%); width:13px; height:13px; border-radius:50%; border:2px solid #fff; box-shadow:0 1px 4px rgba(0,0,0,0.2); }
.slider-ends { display:flex; justify-content:space-between; font-size:10px; color:#c4c4c4; margin-top:5px; }

/* ── NOTES ── */
.notes-area { width:100%; border:1px solid #e4e4e7; border-radius:10px; padding:11px 13px; font-family:'DM Sans',system-ui; font-size:13px; color:#3f3f46; resize:none; height:72px; outline:none; background:#fff; }
.notes-area:focus { border-color:#a1a1aa; }
.notes-area::placeholder { color:#d4d4d8; }

/* ── SUBMIT ── */
.submit-btn { background:#18181b; color:#fff; border:none; border-radius:10px; padding:12px 0; width:100%; font-family:'DM Sans',system-ui; font-size:14px; font-weight:500; cursor:pointer; }
.submit-btn:hover { background:#3f3f46; }

/* ── RIGHT PANEL ── */
.insight-card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:15px 17px; }
.insight-header { display:flex; align-items:center; gap:9px; margin-bottom:9px; }
.insight-icon { width:26px; height:26px; border-radius:7px; background:#f4f4f5; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.insight-icon svg { width:14px; height:14px; }
.insight-title { font-size:12px; font-weight:500; color:#09090b; }
.insight-sub   { font-size:10px; color:#a1a1aa; }
.insight-body  { font-size:12px; color:#52525b; line-height:1.65; }

.trend-row { display:flex; align-items:flex-end; gap:4px; height:36px; margin:9px 0 3px; }
.trend-bar { flex:1; border-radius:2px 2px 0 0; }
.trend-labels { display:flex; gap:4px; }
.trend-label { flex:1; text-align:center; font-size:9px; color:#a1a1aa; }

.muscle-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:5px; margin-top:2px; }
.muscle-chip { border-radius:6px; padding:5px 7px; text-align:center; }
.muscle-name { font-size:10px; font-weight:500; }
.muscle-lvl  { font-size:9px; margin-top:1px; }

/* ── NEXT SESSION CARD ── */
.plan-card { background:#f9f9f9; border:1px solid #f0f0f0; border-radius:12px; padding:14px 16px; }
.plan-metrics { display:flex; gap:8px; margin-top:10px; }
.plan-metric { flex:1; background:#fff; border-radius:8px; padding:7px 10px; text-align:center; }
.pm-label { font-size:10px; color:#a1a1aa; margin-bottom:2px; }
.pm-val   { font-family:'DM Mono',monospace; font-size:13px; font-weight:500; color:#09090b; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}
  <div class="main">

    <div class="page-header">
      <div class="page-title">Check-in</div>

      <!-- Single day navigator with arrows -->
      <div class="day-nav">
        <button class="day-arrow" id="btn-prev" onclick="changeDay(-1)">${chevL}</button>
        <div class="day-label">
          <div class="day-label-row">
            <span class="day-full-name" id="day-name">Jeudi</span>
            <span class="day-full-date" id="day-date">10 avril</span>
          </div>
          <span class="day-today-badge" id="today-badge">Aujourd'hui</span>
        </div>
        <button class="day-arrow" id="btn-next" onclick="changeDay(1)">${chevR}</button>
      </div>

      <div class="checkin-status">✓ Complété à 7h22</div>
    </div>

    <div class="content-scroll">

      <!-- LEFT: séances + ressenti -->
      <div class="left-panel">

        <div>
          <div class="section-title">Séances de la journée</div>
          <div style="display:flex;flex-direction:column;gap:8px">

            <!-- Session 1: Sortie facile 7h — completed -->
            <div class="session-card is-done" id="card-0">
              <div class="sc-header">
                <div class="sc-sport">
                  <div class="sc-icon sport-running"><img src="${runner}" alt=""></div>
                  <div>
                    <div class="sc-name">Sortie facile</div>
                    <div class="sc-dur"><span class="sc-time"><span>7</span><span class="sc-time-h">h00</span></span> · 45 min</div>
                  </div>
                </div>
                <button class="sc-complete-btn done" onclick="toggleDone(0)"><svg class="sc-check-icon" viewBox="0 0 12 12" fill="none"><path d="M2 6.5L4.5 9L10 3.5" stroke="#16a34a" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>Complété</button>
              </div>
              <div class="sc-rpe">
                <span class="rpe-label">Effort perçu (RPE)</span>
                <div class="rpe-pills" id="rpe-0">
                  ${[1,2,3,4,5,6,7,8,9,10].map(n=>`<div class="rpe-pill${n===4?' selected':''}" onclick="selectRpe(0,${n},this)">${n}</div>`).join('')}
                </div>
              </div>
            </div>

            <!-- Session 2: Tempo progressif 17h — upcoming -->
            <div class="session-card" id="card-1">
              <div class="sc-header">
                <div class="sc-sport">
                  <div class="sc-icon sport-running"><img src="${runner}" alt=""></div>
                  <div>
                    <div class="sc-name">Tempo progressif</div>
                    <div class="sc-dur"><span class="sc-time"><span>17</span><span class="sc-time-h">h00</span></span> · 55 min</div>
                  </div>
                </div>
                <button class="sc-complete-btn" onclick="toggleDone(1)"><svg class="sc-check-icon" viewBox="0 0 12 12" fill="none"><path d="M2 6.5L4.5 9L10 3.5" stroke="#d4d4d8" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>Marquer complété</button>
              </div>
              <div class="sc-rpe">
                <span class="rpe-label">Effort perçu (RPE)</span>
                <div class="rpe-pills" id="rpe-1">
                  ${[1,2,3,4,5,6,7,8,9,10].map(n=>`<div class="rpe-pill" onclick="selectRpe(1,${n},this)">${n}</div>`).join('')}
                </div>
              </div>
            </div>

          </div>
        </div>

        <hr class="divider">

        <!-- Ressenti subjectif -->
        <div>
          <div class="section-title">Comment tu te sens ce matin ?</div>
          <div style="display:flex;flex-direction:column;gap:13px">
            ${slider('Fatigue générale',    'Épuisé',  'Frais',    4, '#16a34a')}
            ${slider('Motivation',          'Nulle',   'Maximale', 4, '#3b82f6')}
            ${slider('Courbatures',         'Intenses','Aucune',   3, '#f59e0b')}
            ${slider('Stress / Quotidien',  'Élevé',   'Faible',   4, '#8b5cf6')}
          </div>
        </div>

        <hr class="divider">

        <div>
          <div class="section-title">Note libre (optionnel)</div>
          <textarea class="notes-area" placeholder="Ex : jambes lourdes au réveil, bonne énergie après le café..."></textarea>
        </div>

        <button class="submit-btn">Enregistrer le check-in →</button>

      </div>

      <!-- RIGHT: insights coach -->
      <div class="right-panel">

        <div class="insight-card">
          <div class="insight-header">
            <div class="insight-icon"><svg viewBox="0 0 14 14" fill="none"><path d="M7 1.5v2M7 10.5v2M1.5 7h2M10.5 7h2M3.2 3.2l1.4 1.4M9.4 9.4l1.4 1.4M9.4 4.6l1.4-1.4M3.2 10.8l1.4-1.4" stroke="#52525b" stroke-width="1.3" stroke-linecap="round"/><circle cx="7" cy="7" r="1.8" stroke="#52525b" stroke-width="1.3"/></svg></div>
            <div>
              <div class="insight-title">Analyse du coach IA</div>
              <div class="insight-sub">Basé sur tes données biologiques + subjectif</div>
            </div>
          </div>
          <div class="insight-body">
            HRV 68 ms et FC repos 48 bpm confirment une bonne récupération. Tes scores subjectifs sont cohérents avec tes biomarqueurs. <strong>Le Tempo de 17h00 est bien adapté.</strong> Prévois 12–15 min d'échauffement progressif avant les intervalles.
          </div>
        </div>

        <div class="insight-card">
          <div class="insight-header">
            <div class="insight-icon"><svg viewBox="0 0 14 14" fill="none"><polyline points="1,10 4,7 7,8.5 10,4 13,2" stroke="#52525b" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="13" cy="2" r="1.2" fill="#52525b"/></svg></div>
            <div>
              <div class="insight-title">Tendance fatigue subjective — 7 jours</div>
              <div class="insight-sub">Score moyen quotidien</div>
            </div>
          </div>
          <div class="trend-row">
            ${[3,2,4,3,4,3,4].map((v,i)=>{
              const h = Math.round(v/5*32);
              return `<div class="trend-bar" style="height:${h}px;background:${i===3?'#18181b':'#e4e4e7'}"></div>`;
            }).join('')}
          </div>
          <div class="trend-labels">
            ${['L','M','M','J','V','S','D'].map((l,i)=>`<div class="trend-label" style="${i===3?'color:#09090b;font-weight:600':''}">${l}</div>`).join('')}
          </div>
        </div>

        <div class="insight-card">
          <div class="insight-header">
            <div class="insight-icon"><svg viewBox="0 0 14 14" fill="none"><circle cx="7" cy="2.5" r="1.3" stroke="#52525b" stroke-width="1.3"/><path d="M7 4v3.5M7 7.5L5 10.5M7 7.5L9 10.5M5 5.5L3.5 8M8.5 5.5L10.5 8" stroke="#52525b" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
            <div>
              <div class="insight-title">État musculaire perçu</div>
              <div class="insight-sub">Zones de courbatures signalées</div>
            </div>
          </div>
          <div class="muscle-grid">
            ${[
              {z:'Quadriceps',l:2,bg:'#fef3c7',c:'#92400e'},
              {z:'Mollets',   l:1,bg:'#fefce8',c:'#ca8a04'},
              {z:'Ischio',    l:3,bg:'#fee2e2',c:'#dc2626'},
              {z:'Fessiers',  l:1,bg:'#fefce8',c:'#ca8a04'},
              {z:'Dos',       l:0,bg:'#f4f4f5',c:'#a1a1aa'},
              {z:'Épaules',   l:0,bg:'#f4f4f5',c:'#a1a1aa'},
              {z:'Abdos',     l:1,bg:'#fefce8',c:'#ca8a04'},
              {z:'Adducteurs',l:2,bg:'#fef3c7',c:'#92400e'},
            ].map(m=>`<div class="muscle-chip" style="background:${m.bg}">
              <div class="muscle-name" style="color:${m.c}">${m.z}</div>
              <div class="muscle-lvl"  style="color:${m.c}">${['OK','Léger','Moyen','Fort'][m.l]}</div>
            </div>`).join('')}
          </div>
        </div>

      </div>
    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 4/12 — /check-in · 1280×800px
</div>

<script>
// ── Day navigation ──
const DAYS = [
  {name:'Lundi',    date:'7 avril',  today:false, past:true},
  {name:'Mardi',    date:'8 avril',  today:false, past:true},
  {name:'Mercredi', date:'9 avril',  today:false, past:true},
  {name:'Jeudi',    date:'10 avril', today:true,  past:false},
  {name:'Vendredi', date:'11 avril', today:false, past:false},
  {name:'Samedi',   date:'12 avril', today:false, past:false},
  {name:'Dimanche', date:'13 avril', today:false, past:false},
];
let cur = 3;

function changeDay(dir) {
  const next = cur + dir;
  if (next < 0 || next >= DAYS.length) return;
  cur = next;
  const d = DAYS[cur];
  document.getElementById('day-name').textContent = d.name;
  document.getElementById('day-date').textContent = d.date;
  document.getElementById('today-badge').style.display = d.today ? '' : 'none';
  document.getElementById('btn-prev').disabled = cur === 0;
  document.getElementById('btn-next').disabled = cur === DAYS.length - 1;
}
document.getElementById('btn-prev').disabled = cur === 0;
document.getElementById('btn-next').disabled = cur === DAYS.length - 1;

// ── Session complete toggle ──
const CHECK_DONE = '<svg class="sc-check-icon" viewBox="0 0 12 12" fill="none"><path d="M2 6.5L4.5 9L10 3.5" stroke="#16a34a" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const CHECK_IDLE = '<svg class="sc-check-icon" viewBox="0 0 12 12" fill="none"><path d="M2 6.5L4.5 9L10 3.5" stroke="#d4d4d8" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
function toggleDone(idx) {
  const card = document.getElementById('card-' + idx);
  const btn  = card.querySelector('.sc-complete-btn');
  const isDone = card.classList.toggle('is-done');
  btn.innerHTML = (isDone ? CHECK_DONE + 'Complété' : CHECK_IDLE + 'Marquer complété');
  btn.classList.toggle('done', isDone);
}

// ── RPE pill selection ──
function selectRpe(cardIdx, val, el) {
  const card = document.getElementById('card-' + cardIdx);
  if (!card.classList.contains('is-done')) return;
  card.querySelectorAll('.rpe-pill').forEach(p => p.classList.remove('selected'));
  el.classList.add('selected');
}
</script>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/268-1775885848/content/checkin-v2.html', html);
console.log('done');
