const fs = require('fs');

const runner  = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');
const swimmer = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/swimmer.png').toString('base64');
const biker   = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/biker.png').toString('base64');
const settings= 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');

const PX_PER_HOUR = 52;
const START_HOUR  = 6;
const END_HOUR    = 22;
const HOURS       = END_HOUR - START_HOUR;
const GRID_HEIGHT = HOURS * PX_PER_HOUR;
const DETAIL_W    = 264; // keep in sync with CSS .detail-panel width

function top(h, m = 0) { return ((h - START_HOUR) + m / 60) * PX_PER_HOUR; }
function height(min)   { return (min / 60) * PX_PER_HOUR; }

// Time labels
let timeLabels = '';
for (let h = START_HOUR; h <= END_HOUR; h++) {
  timeLabels += `<div class="time-label" style="top:${(h-START_HOUR)*PX_PER_HOUR}px">${h}h</div>`;
}

const SIDEBAR = `
<div class="sidebar">
  <div class="sidebar-logo">Resilio<span class="logo-plus">+</span></div>
  <div class="nav-section">
    <div class="nav-label">Principal</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="10" rx="8" ry="5" stroke="#52525b" stroke-width="1.5" fill="none"/><circle cx="10" cy="10" r="2.5" fill="#52525b"/><circle cx="10" cy="10" r="1" fill="white"/></svg></div>Aperçu</div>
    <div class="nav-item active"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="3" y="4" width="14" height="12" rx="1" stroke="#09090b" stroke-width="1.4" fill="none"/><path d="M3 4C3 2.5 5 2.5 5 4M17 4C17 2.5 15 2.5 15 4M3 16C3 17.5 5 17.5 5 16M17 16C17 17.5 15 17.5 15 16" stroke="#09090b" stroke-width="1.2" fill="none"/><line x1="6" y1="8" x2="14" y2="8" stroke="#09090b" stroke-width="1"/><line x1="6" y1="11" x2="14" y2="11" stroke="#09090b" stroke-width="1"/><line x1="6" y1="14" x2="10" y2="14" stroke="#09090b" stroke-width="1"/></svg></div>Plan</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M12 2L5.5 11H10L8 18L15.5 8H11Z" fill="#52525b"/></svg></div>Énergie</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M4 10C4 6.7 6.7 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 6.7 13.3 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M4 10C4 13.3 6.7 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 13.3 13.3 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M7.5 10L9.2 11.8L12.5 8.5" stroke="#52525b" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></div>Check-in</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Données</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><line x1="3" y1="3" x2="17" y2="3" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/><line x1="3" y1="17" x2="17" y2="17" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/><path d="M5 3L10 11L15 3" fill="#52525b" opacity="0.35"/><path d="M5 3L10 11L15 3M5 17L10 11L15 17" stroke="#52525b" stroke-width="1.2" fill="none"/><path d="M5 17L10 11L15 17" fill="#52525b" opacity="0.65"/></svg></div>Historique</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="2" y="2" width="16" height="16" rx="1.5" stroke="#52525b" stroke-width="1.3" fill="none"/><rect x="5" y="12" width="2.5" height="4" rx="0.5" fill="#52525b" opacity="0.4"/><rect x="8.8" y="9.5" width="2.5" height="6.5" rx="0.5" fill="#52525b" opacity="0.7"/><rect x="12.5" y="6" width="2.5" height="10" rx="0.5" fill="#52525b"/></svg></div>Analytiques</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Compte</div>
    <div class="nav-item"><div class="nav-icon" style="opacity:0.45"><img src="${settings}" style="width:18px;height:18px;object-fit:contain"></div>Paramètres</div>
  </div>
  <div class="sidebar-footer">
    <div class="avatar">S</div>
    <div><div class="avatar-name">Simon</div><div class="avatar-status">Récupération optimale</div></div>
  </div>
</div>`;

const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Plan</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400&family=Playfair+Display:wght@400;600&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', system-ui; background: #e8e8e8; display:flex; align-items:center; justify-content:center; min-height:100vh; padding:32px; }

  .frame { width:1280px; height:800px; background:#fafafa; border-radius:16px; box-shadow:0 12px 64px rgba(0,0,0,0.16); display:flex; overflow:hidden; }

  /* ── SIDEBAR ── */
  .sidebar { width:260px; min-width:260px; background:#fff; border-right:1px solid #e4e4e7; display:flex; flex-direction:column; padding:32px 0 24px; }
  .sidebar-logo { font-family:'Playfair Display',serif; font-size:24px; color:#09090b; padding:0 28px 28px; border-bottom:1px solid #e4e4e7; }
  .logo-plus { color:#16a34a; }
  .nav-section { padding:20px 16px 4px; }
  .nav-label { font-size:10px; text-transform:uppercase; letter-spacing:0.12em; color:#a1a1aa; padding:0 8px; margin-bottom:4px; }
  .nav-item { display:flex; align-items:center; gap:10px; padding:11px 12px; border-radius:8px; font-size:14px; color:#52525b; margin-bottom:2px; border-left:2px solid transparent; }
  .nav-item.active { background:#f4f4f5; color:#09090b; border-left:2px solid #18181b; font-weight:500; }
  .nav-icon { width:22px; height:22px; display:flex; align-items:center; justify-content:center; flex-shrink:0; opacity:0.45; }
  .nav-item.active .nav-icon { opacity:1; }
  .nav-icon svg { width:18px; height:18px; }
  .nav-icon img { width:18px; height:18px; object-fit:contain; }
  .sidebar-footer { margin-top:auto; padding:16px 20px 0; border-top:1px solid #e4e4e7; display:flex; align-items:center; gap:12px; }
  .avatar { width:36px; height:36px; border-radius:50%; background:#18181b; color:white; font-size:13px; font-weight:600; display:flex; align-items:center; justify-content:center; }
  .avatar-name { font-size:13px; font-weight:500; color:#09090b; }
  .avatar-status { font-size:11px; color:#16a34a; display:flex; align-items:center; gap:4px; }
  .avatar-status::before { content:''; width:6px; height:6px; background:#16a34a; border-radius:50%; display:inline-block; }

  /* ── MAIN ── */
  .main { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }

  /* Header */
  .page-header { padding:20px 24px 14px; border-bottom:1px solid #e4e4e7; flex-shrink:0; }
  .header-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; }
  .page-title { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; letter-spacing:-0.02em; }
  .view-toggle { display:flex; background:#f4f4f5; border-radius:8px; padding:3px; gap:2px; }
  .view-btn { font-family:'DM Sans',system-ui; font-size:12px; font-weight:500; padding:5px 14px; border-radius:6px; border:none; cursor:pointer; background:transparent; color:#71717a; }
  .view-btn.active { background:#fff; color:#09090b; box-shadow:0 1px 3px rgba(0,0,0,0.08); }
  .week-nav { display:flex; align-items:center; gap:10px; }
  .nav-arrow { width:28px; height:28px; border-radius:7px; border:1px solid #e4e4e7; background:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; color:#52525b; font-size:13px; flex-shrink:0; }
  .week-label { font-size:13px; font-weight:500; color:#09090b; }
  .week-sub { font-size:11px; color:#71717a; }

  /* ── DAY HEADER ROW ── */
  /* day-headers uses same flex layout as the grid: gutter + 7 cols + detail-panel-width spacer */
  .day-headers { display:flex; border-bottom:1px solid #e4e4e7; flex-shrink:0; }
  .time-gutter-h { width:44px; min-width:44px; flex-shrink:0; }
  /* 7 day cells fill the calendar area (full width minus detail panel) */
  .day-hcols { flex:1; display:flex; min-width:0; }
  .day-hcell { flex:1; min-width:0; padding:8px 8px 7px; border-left:1px solid #e4e4e7; }
  .day-hcell:first-child { border-left:none; }
  .dhname { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:2px; }
  .dhnum  { font-family:'DM Mono',monospace; font-size:17px; color:#09090b; line-height:1; }
  .day-hcell.today .dhname { color:#16a34a; }
  .day-hcell.today .dhnum  { color:#16a34a; }
  .day-hcell.rest .dhname  { color:#d4d4d8; }
  .day-hcell.rest .dhnum   { color:#d4d4d8; }
  /* spacer that aligns with detail panel */
  .detail-header-spacer { width:${DETAIL_W}px; min-width:${DETAIL_W}px; flex-shrink:0; border-left:1px solid #e4e4e7; }

  /* ── CALENDAR SCROLL AREA ── */
  .cal-wrap { flex:1; display:flex; overflow:hidden; }
  .cal-scroll { flex:1; overflow-y:auto; overflow-x:hidden; display:flex; min-width:0; }

  /* Time gutter */
  .time-gutter { width:44px; min-width:44px; position:relative; flex-shrink:0; height:${GRID_HEIGHT}px; }
  .time-label { position:absolute; right:6px; font-size:10px; color:#a1a1aa; font-family:'DM Mono',monospace; transform:translateY(-50%); white-space:nowrap; line-height:1; }

  /* Day columns container */
  .day-cols { flex:1; display:flex; position:relative; min-width:0; height:${GRID_HEIGHT}px; }

  /* Individual day column */
  .day-col {
    flex:1;
    min-width:0;
    position:relative;
    border-left:1px solid #e4e4e7;
    background-image: repeating-linear-gradient(
      to bottom,
      transparent 0px,
      transparent ${PX_PER_HOUR - 1}px,
      #f0f0f0 ${PX_PER_HOUR - 1}px,
      #f0f0f0 ${PX_PER_HOUR}px
    );
    background-size: 100% ${PX_PER_HOUR}px;
  }
  .day-col:first-child { border-left:none; }
  .day-col.today-col { background-color:rgba(22,163,74,0.02); }

  /* Now line */
  .now-line { position:absolute; left:0; right:0; height:2px; background:#16a34a; z-index:5; pointer-events:none; }
  .now-dot { position:absolute; left:-3px; top:-3px; width:7px; height:7px; background:#16a34a; border-radius:50%; }

  /* ── SESSION BLOCK — minimal: icon + time only ── */
  .sblock {
    position:absolute;
    left:5px; right:5px;
    border-radius:8px;
    padding:4px 6px;
    cursor:pointer;
    overflow:hidden;
    display:flex;
    align-items:center;
    gap:5px;
    transition:box-shadow 0.15s;
  }
  .sblock:hover { box-shadow:0 3px 10px rgba(0,0,0,0.12); }
  .sblock.planned  { background:#f4f4f5; border:1px solid #e4e4e7; }
  .sblock.selected { background:#f4f4f5; border:1.5px solid #18181b; }
  .sblock.done     { background:#f0fdf4; border:1px solid #bbf7d0; }

  .sport-dot {
    width:20px; height:20px; border-radius:5px;
    background:#18181b;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
  }
  .sport-dot img { width:12px; height:12px; object-fit:contain; filter:invert(1); }

  .sblock-time {
    font-size:10px; font-family:'DM Mono',monospace; color:#52525b;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    flex:1; min-width:0;
  }
  .sblock.done .sblock-time { color:#15803d; }
  /* Green dot for done state (replaces time text) */
  .done-dot { width:6px; height:6px; border-radius:50%; background:#16a34a; flex-shrink:0; }

  /* ── DETAIL PANEL ── */
  .detail-panel { width:${DETAIL_W}px; min-width:${DETAIL_W}px; background:#fff; border-left:1px solid #e4e4e7; display:flex; flex-direction:column; overflow-y:auto; flex-shrink:0; }
  .detail-hd { display:flex; align-items:center; justify-content:space-between; padding:20px 18px 0; margin-bottom:14px; }
  .detail-label { font-size:10px; text-transform:uppercase; letter-spacing:0.12em; color:#a1a1aa; }

  /* FIX 1: ✕ without any box/border */
  .detail-close {
    background:transparent;
    border:none;
    padding:2px 4px;
    cursor:pointer;
    color:#a1a1aa;
    font-size:15px;
    line-height:1;
    display:flex;
    align-items:center;
    justify-content:center;
    border-radius:4px;
  }
  .detail-close:hover { color:#09090b; background:#f4f4f5; }

  .detail-body { padding:0 18px 24px; }
  .detail-sport { display:flex; align-items:center; gap:12px; margin-bottom:18px; }
  .detail-sport-icon { width:48px; height:48px; background:#18181b; border-radius:12px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
  .detail-sport-icon img { width:28px; height:28px; object-fit:contain; filter:invert(1); }
  .detail-title { font-family:'Playfair Display',serif; font-size:17px; color:#09090b; margin-bottom:2px; line-height:1.2; }
  .detail-meta { font-size:11px; color:#71717a; }
  .detail-divider { border:none; border-top:1px solid #e4e4e7; margin:14px 0; }
  .detail-stitle { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:8px; }
  .detail-desc { font-size:12px; color:#52525b; line-height:1.65; margin-bottom:4px; }
  .detail-stat { display:flex; justify-content:space-between; align-items:center; padding:7px 0; border-bottom:1px solid #f4f4f5; }
  .detail-stat-l { font-size:11px; color:#71717a; }
  .detail-stat-v { font-family:'DM Mono',monospace; font-size:12px; color:#09090b; }
  .detail-btn { margin-top:16px; background:#18181b; color:white; border:none; border-radius:8px; padding:10px 0; width:100%; font-family:'DM Sans',system-ui; font-size:13px; font-weight:500; cursor:pointer; text-align:center; display:block; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}

  <div class="main">
    <!-- Header -->
    <div class="page-header">
      <div class="header-top">
        <div class="page-title">Plan de la semaine</div>
        <div class="view-toggle">
          <button class="view-btn active">Semaine</button>
          <button class="view-btn">Mois</button>
        </div>
      </div>
      <div class="week-nav">
        <button class="nav-arrow">←</button>
        <div>
          <div class="week-label">7 – 13 avril 2026</div>
          <div class="week-sub">Semaine 2 · Phase de construction</div>
        </div>
        <button class="nav-arrow">→</button>
      </div>
    </div>

    <!-- FIX 3: Day headers — wrapped in .day-hcols so they align with .day-cols only,
         plus a .detail-header-spacer matching the detail panel width -->
    <div class="day-headers">
      <div class="time-gutter-h"></div>
      <div class="day-hcols">
        <div class="day-hcell"><div class="dhname">Lun</div><div class="dhnum">07</div></div>
        <div class="day-hcell"><div class="dhname">Mar</div><div class="dhnum">08</div></div>
        <div class="day-hcell rest"><div class="dhname">Mer</div><div class="dhnum">09</div></div>
        <div class="day-hcell today"><div class="dhname">Jeu ▶</div><div class="dhnum">10</div></div>
        <div class="day-hcell"><div class="dhname">Ven</div><div class="dhnum">11</div></div>
        <div class="day-hcell"><div class="dhname">Sam</div><div class="dhnum">12</div></div>
        <div class="day-hcell rest"><div class="dhname">Dim</div><div class="dhnum">13</div></div>
      </div>
      <div class="detail-header-spacer"></div>
    </div>

    <!-- Grid -->
    <div class="cal-wrap">
      <div class="cal-scroll">
        <!-- Time gutter -->
        <div class="time-gutter">${timeLabels}</div>

        <!-- 7 day columns as proper flex children -->
        <div class="day-cols">

          <!-- LUN: Sortie facile 7h00 45min done -->
          <div class="day-col">
            <div class="sblock done" style="top:${top(7,0)}px;height:${height(45)}px">
              <div class="sport-dot"><img src="${runner}" alt=""></div>
              <div class="sblock-time">7h00</div>
              <div class="done-dot"></div>
            </div>
          </div>

          <!-- MAR: Zone 2 vélo 7h00 75min done -->
          <div class="day-col">
            <div class="sblock done" style="top:${top(7,0)}px;height:${height(75)}px">
              <div class="sport-dot"><img src="${biker}" alt=""></div>
              <div class="sblock-time">7h00</div>
              <div class="done-dot"></div>
            </div>
          </div>

          <!-- MER: repos -->
          <div class="day-col"></div>

          <!-- JEU: Tempo 17h00 55min — selected, now-line here -->
          <div class="day-col today-col">
            <div class="now-line" style="top:${top(14,30)}px"><div class="now-dot"></div></div>
            <div class="sblock selected" style="top:${top(17,0)}px;height:${height(55)}px">
              <div class="sport-dot"><img src="${runner}" alt=""></div>
              <div class="sblock-time">17h00</div>
            </div>
          </div>

          <!-- VEN: Natation 7h00 45min -->
          <div class="day-col">
            <div class="sblock planned" style="top:${top(7,0)}px;height:${height(45)}px">
              <div class="sport-dot"><img src="${swimmer}" alt=""></div>
              <div class="sblock-time">7h00</div>
            </div>
          </div>

          <!-- SAM: Long run 9h00 90min -->
          <div class="day-col">
            <div class="sblock planned" style="top:${top(9,0)}px;height:${height(90)}px">
              <div class="sport-dot"><img src="${runner}" alt=""></div>
              <div class="sblock-time">9h00</div>
            </div>
          </div>

          <!-- DIM: repos -->
          <div class="day-col"></div>

        </div>
      </div>

      <!-- Detail panel -->
      <div class="detail-panel">
        <div class="detail-hd">
          <div class="detail-label">Détail de la séance</div>
          <!-- FIX 1: no border/box around ✕ -->
          <button class="detail-close" title="Fermer">✕</button>
        </div>
        <div class="detail-body">
          <div class="detail-sport">
            <div class="detail-sport-icon"><img src="${runner}" alt="course"></div>
            <div>
              <div class="detail-title">Tempo progressif</div>
              <div class="detail-meta">Jeudi 10 avril · 17h00</div>
            </div>
          </div>
          <div class="detail-stitle">Description</div>
          <div class="detail-desc">3 × 10 min au seuil lactate (allure T), récupération 2 min entre efforts. Échauffement 10 min, retour au calme 5 min.</div>
          <div class="detail-divider"></div>
          <div class="detail-stitle">Paramètres</div>
          <div class="detail-stat"><span class="detail-stat-l">Durée totale</span><span class="detail-stat-v">55 min</span></div>
          <div class="detail-stat"><span class="detail-stat-l">Zone cible</span><span class="detail-stat-v">Z3 – Z4</span></div>
          <div class="detail-stat"><span class="detail-stat-l">FC cible</span><span class="detail-stat-v">162–175 bpm</span></div>
          <div class="detail-stat"><span class="detail-stat-l">Allure T</span><span class="detail-stat-v">4:52 /km</span></div>
          <div class="detail-stat"><span class="detail-stat-l">Charge estimée</span><span class="detail-stat-v">68 TSS</span></div>
          <button class="detail-btn">Marquer comme complétée</button>
        </div>
      </div>
    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 2/12 — /plan · 1280×800px
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/plan-v4.html', html);
console.log('done');
