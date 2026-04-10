const fs = require('fs');

const runner = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');
const swimmer = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/swimmer.png').toString('base64');
const biker = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/biker.png').toString('base64');
const settings = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');

// PX per hour in the time grid
const PX_PER_HOUR = 52;
const START_HOUR = 6; // grid starts at 6h
const END_HOUR = 22;  // grid ends at 22h
const HOURS = END_HOUR - START_HOUR; // 16 hours
const GRID_HEIGHT = HOURS * PX_PER_HOUR; // 832px — scrollable

function top(hour, min = 0) {
  return ((hour - START_HOUR) + min / 60) * PX_PER_HOUR;
}
function height(min) {
  return (min / 60) * PX_PER_HOUR;
}

// Time labels
let timeLabels = '';
for (let h = START_HOUR; h <= END_HOUR; h++) {
  timeLabels += `<div class="time-label" style="top:${(h - START_HOUR) * PX_PER_HOUR}px">${h}h</div>`;
}

// Horizontal hour lines
let hourLines = '';
for (let h = START_HOUR; h <= END_HOUR; h++) {
  hourLines += `<div class="hour-line" style="top:${(h - START_HOUR) * PX_PER_HOUR}px"></div>`;
}

const SIDEBAR_SVG = `
  <div class="sidebar">
    <div class="sidebar-logo">Resilio<span>+</span></div>
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
  </div>
`;

const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Plan</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400&family=Playfair+Display:wght@400;600&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', system-ui; background: #e8e8e8; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 32px; }

  .frame { width: 1280px; height: 800px; background: #fafafa; border-radius: 16px; box-shadow: 0 12px 64px rgba(0,0,0,0.16); display: flex; overflow: hidden; }

  /* Sidebar */
  .sidebar { width: 260px; min-width: 260px; background: #fff; border-right: 1px solid #e4e4e7; display: flex; flex-direction: column; padding: 32px 0 24px; }
  .sidebar-logo { font-family: 'Playfair Display', serif; font-size: 24px; color: #09090b; padding: 0 28px 28px; border-bottom: 1px solid #e4e4e7; }
  .sidebar-logo span { color: #16a34a; }
  .nav-section { padding: 20px 16px 4px; }
  .nav-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #a1a1aa; padding: 0 8px; margin-bottom: 4px; }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 11px 12px; border-radius: 8px; font-size: 14px; color: #52525b; margin-bottom: 2px; border-left: 2px solid transparent; }
  .nav-item.active { background: #f4f4f5; color: #09090b; border-left: 2px solid #18181b; font-weight: 500; }
  .nav-icon { width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; opacity: 0.45; }
  .nav-item.active .nav-icon { opacity: 1; }
  .nav-icon svg { width: 18px; height: 18px; }
  .nav-icon img { width: 18px; height: 18px; object-fit: contain; }
  .sidebar-footer { margin-top: auto; padding: 16px 20px 0; border-top: 1px solid #e4e4e7; display: flex; align-items: center; gap: 12px; }
  .avatar { width: 36px; height: 36px; border-radius: 50%; background: #18181b; color: white; font-size: 13px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
  .avatar-name { font-size: 13px; font-weight: 500; color: #09090b; }
  .avatar-status { font-size: 11px; color: #16a34a; display: flex; align-items: center; gap: 4px; }
  .avatar-status::before { content: ''; width: 6px; height: 6px; background: #16a34a; border-radius: 50%; display: inline-block; }

  /* Main */
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }

  /* ── PAGE HEADER ── */
  .page-header { padding: 24px 28px 16px; border-bottom: 1px solid #e4e4e7; flex-shrink: 0; }
  .header-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .page-title { font-family: 'Playfair Display', serif; font-size: 26px; color: #09090b; letter-spacing: -0.02em; }

  /* View toggle */
  .view-toggle { display: flex; background: #f4f4f5; border-radius: 8px; padding: 3px; gap: 2px; }
  .view-btn { font-family: 'DM Sans', system-ui; font-size: 12px; font-weight: 500; padding: 5px 14px; border-radius: 6px; border: none; cursor: pointer; background: transparent; color: #71717a; }
  .view-btn.active { background: #ffffff; color: #09090b; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

  /* Week nav */
  .week-nav { display: flex; align-items: center; gap: 12px; }
  .nav-btn { width: 30px; height: 30px; border-radius: 7px; border: 1px solid #e4e4e7; background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #52525b; font-size: 14px; flex-shrink: 0; }
  .nav-btn:hover { background: #f4f4f5; }
  .week-label { font-size: 13px; font-weight: 500; color: #09090b; white-space: nowrap; }
  .week-sub { font-size: 11px; color: #71717a; }

  /* ── DAY HEADERS ROW ── */
  .day-headers { display: flex; border-bottom: 1px solid #e4e4e7; flex-shrink: 0; }
  .time-gutter-header { width: 44px; min-width: 44px; flex-shrink: 0; }
  .day-header-cell { flex: 1; min-width: 0; padding: 10px 8px 8px; border-left: 1px solid #e4e4e7; }
  .day-header-cell:first-of-type { border-left: none; }
  .day-name { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #a1a1aa; margin-bottom: 2px; }
  .day-date-num { font-family: 'DM Mono', monospace; font-size: 18px; color: #09090b; line-height: 1; }
  .day-header-cell.today .day-name { color: #16a34a; }
  .day-header-cell.today .day-date-num { color: #16a34a; }
  .day-header-cell.rest .day-name { color: #d4d4d8; }
  .day-header-cell.rest .day-date-num { color: #d4d4d8; }

  /* ── CALENDAR GRID ── */
  .calendar-area { display: flex; flex: 1; overflow: hidden; }
  .calendar-scroll { flex: 1; overflow-y: auto; overflow-x: hidden; display: flex; }

  /* Time gutter */
  .time-gutter { width: 44px; min-width: 44px; position: relative; flex-shrink: 0; height: ${GRID_HEIGHT}px; }
  .time-label { position: absolute; right: 8px; font-size: 10px; color: #a1a1aa; font-family: 'DM Mono', monospace; transform: translateY(-50%); white-space: nowrap; }

  /* Day columns */
  .day-cols { flex: 1; display: flex; position: relative; min-width: 0; }
  .day-col { flex: 1; min-width: 0; border-left: 1px solid #e4e4e7; position: relative; height: ${GRID_HEIGHT}px; }
  .day-col:first-child { border-left: none; }

  /* Hour lines */
  .hour-line { position: absolute; left: 0; right: 0; border-top: 1px solid #f4f4f5; pointer-events: none; }
  .hour-line.half { border-top: 1px dashed #f4f4f5; }

  /* Current time indicator */
  .now-line { position: absolute; left: 0; right: 0; border-top: 2px solid #16a34a; z-index: 10; }
  .now-dot { position: absolute; left: -4px; top: -4px; width: 8px; height: 8px; background: #16a34a; border-radius: 50%; }

  /* ── SESSION BLOCK ── */
  .session-block {
    position: absolute;
    left: 4px;
    right: 4px;
    border-radius: 8px;
    padding: 6px 8px;
    cursor: pointer;
    overflow: hidden;
    border: 1px solid transparent;
    transition: box-shadow 0.15s;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .session-block:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
  .session-block.planned { background: #f4f4f5; border-color: #e4e4e7; }
  .session-block.selected { background: #f4f4f5; border-color: #18181b; border-width: 1.5px; }
  .session-block.done { background: #f0fdf4; border-color: #bbf7d0; }

  .block-top { display: flex; align-items: center; gap: 6px; min-width: 0; }
  .block-sport-dot { width: 22px; height: 22px; border-radius: 6px; background: #18181b; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .block-sport-dot.done { background: #16a34a; }
  .block-sport-dot img { width: 13px; height: 13px; object-fit: contain; filter: invert(1); }
  .block-title { font-size: 11px; font-weight: 500; color: #09090b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 1; }
  .block-duration { font-size: 10px; color: #71717a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* Done badge inline */
  .done-row { display: flex; align-items: center; gap: 4px; }
  .done-check { font-size: 10px; color: #16a34a; line-height: 1; flex-shrink: 0; }
  .done-text { font-size: 10px; color: #16a34a; line-height: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* ── DETAIL PANEL ── */
  .detail-panel { width: 272px; min-width: 272px; background: #fff; border-left: 1px solid #e4e4e7; display: flex; flex-direction: column; padding: 24px 20px; overflow-y: auto; flex-shrink: 0; }
  .detail-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #a1a1aa; margin-bottom: 14px; }
  .detail-sport { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
  .detail-sport-icon { width: 48px; height: 48px; background: #18181b; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .detail-sport-icon img { width: 28px; height: 28px; object-fit: contain; filter: invert(1); }
  .detail-title { font-family: 'Playfair Display', serif; font-size: 17px; color: #09090b; margin-bottom: 2px; line-height: 1.2; }
  .detail-meta { font-size: 11px; color: #71717a; }
  .detail-divider { border: none; border-top: 1px solid #e4e4e7; margin: 14px 0; }
  .detail-section-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #a1a1aa; margin-bottom: 8px; }
  .detail-desc { font-size: 12px; color: #52525b; line-height: 1.65; margin-bottom: 14px; }
  .detail-stat { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid #f4f4f5; }
  .detail-stat-label { font-size: 11px; color: #71717a; }
  .detail-stat-value { font-family: 'DM Mono', monospace; font-size: 12px; color: #09090b; }
  .detail-btn { margin-top: 18px; background: #18181b; color: white; border: none; border-radius: 8px; padding: 10px 0; width: 100%; font-family: 'DM Sans', system-ui; font-size: 13px; font-weight: 500; cursor: pointer; text-align: center; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR_SVG}

  <div class="main">
    <!-- Page header -->
    <div class="page-header">
      <div class="header-top">
        <div class="page-title">Plan de la semaine</div>
        <div class="view-toggle">
          <button class="view-btn active">Semaine</button>
          <button class="view-btn">Mois</button>
        </div>
      </div>
      <div class="week-nav">
        <button class="nav-btn">←</button>
        <div>
          <div class="week-label">7 – 13 avril 2026</div>
          <div class="week-sub">Semaine 2 · Phase de construction</div>
        </div>
        <button class="nav-btn">→</button>
      </div>
    </div>

    <!-- Day headers -->
    <div class="day-headers">
      <div class="time-gutter-header"></div>
      <div class="day-header-cell"><div class="day-name">Lun</div><div class="day-date-num">07</div></div>
      <div class="day-header-cell"><div class="day-name">Mar</div><div class="day-date-num">08</div></div>
      <div class="day-header-cell rest"><div class="day-name">Mer</div><div class="day-date-num">09</div></div>
      <div class="day-header-cell today"><div class="day-name">Jeu ▶</div><div class="day-date-num">10</div></div>
      <div class="day-header-cell"><div class="day-name">Ven</div><div class="day-date-num">11</div></div>
      <div class="day-header-cell"><div class="day-name">Sam</div><div class="day-date-num">12</div></div>
      <div class="day-header-cell rest"><div class="day-name">Dim</div><div class="day-date-num">13</div></div>
    </div>

    <!-- Calendar grid + detail panel -->
    <div class="calendar-area">
      <div class="calendar-scroll">
        <!-- Time gutter -->
        <div class="time-gutter">
          ${timeLabels}
        </div>

        <!-- Day columns -->
        <div class="day-cols">
          ${hourLines}

          <!-- Current time: ~14h30 -->
          <div class="now-line" style="top:${top(14,30)}px"><div class="now-dot"></div></div>

          <!-- LUNDI: Sortie facile 7h00, 45min — done -->
          <div class="day-col" style="left:0%;width:calc(100%/7 * 1)">
            <div class="session-block done" style="top:${top(7,0)}px;height:${height(45)}px">
              <div class="block-top">
                <div class="block-sport-dot done"><img src="${runner}" alt="course"></div>
                <div class="block-title">Sortie facile</div>
              </div>
              <div class="done-row">
                <span class="done-check">✓</span>
                <span class="done-text">Complétée</span>
              </div>
            </div>
          </div>

          <!-- MARDI: Zone 2 vélo 7h00, 75min — done -->
          <div class="day-col" style="left:calc(100%/7 * 1);width:calc(100%/7 * 1)">
            <div class="session-block done" style="top:${top(7,0)}px;height:${height(75)}px">
              <div class="block-top">
                <div class="block-sport-dot done"><img src="${biker}" alt="vélo"></div>
                <div class="block-title">Zone 2 vélo</div>
              </div>
              <div class="block-duration">75 min</div>
              <div class="done-row">
                <span class="done-check">✓</span>
                <span class="done-text">Complétée</span>
              </div>
            </div>
          </div>

          <!-- MERCREDI: repos — empty -->
          <div class="day-col" style="left:calc(100%/7 * 2);width:calc(100%/7 * 1)"></div>

          <!-- JEUDI: Tempo 17h00, 55min — selected -->
          <div class="day-col" style="left:calc(100%/7 * 3);width:calc(100%/7 * 1)">
            <div class="session-block selected" style="top:${top(17,0)}px;height:${height(55)}px">
              <div class="block-top">
                <div class="block-sport-dot"><img src="${runner}" alt="course"></div>
                <div class="block-title">Tempo progressif</div>
              </div>
              <div class="block-duration">55 min · 17h00</div>
            </div>
          </div>

          <!-- VENDREDI: Natation 7h00, 45min -->
          <div class="day-col" style="left:calc(100%/7 * 4);width:calc(100%/7 * 1)">
            <div class="session-block planned" style="top:${top(7,0)}px;height:${height(45)}px">
              <div class="block-top">
                <div class="block-sport-dot"><img src="${swimmer}" alt="natation"></div>
                <div class="block-title">Endurance eau</div>
              </div>
              <div class="block-duration">45 min · 7h00</div>
            </div>
          </div>

          <!-- SAMEDI: Long run 9h00, 90min -->
          <div class="day-col" style="left:calc(100%/7 * 5);width:calc(100%/7 * 1)">
            <div class="session-block planned" style="top:${top(9,0)}px;height:${height(90)}px">
              <div class="block-top">
                <div class="block-sport-dot"><img src="${runner}" alt="course"></div>
                <div class="block-title">Long run Z2</div>
              </div>
              <div class="block-duration">90 min · 9h00</div>
            </div>
          </div>

          <!-- DIMANCHE: repos — empty -->
          <div class="day-col" style="left:calc(100%/7 * 6);width:calc(100%/7 * 1)"></div>
        </div>
      </div>

      <!-- Detail panel -->
      <div class="detail-panel">
        <div class="detail-label">Détail de la séance</div>
        <div class="detail-sport">
          <div class="detail-sport-icon"><img src="${runner}" alt="course"></div>
          <div>
            <div class="detail-title">Tempo progressif</div>
            <div class="detail-meta">Jeudi 10 avril · 17h00</div>
          </div>
        </div>
        <div class="detail-section-title">Description</div>
        <div class="detail-desc">3 × 10 min au seuil lactate (allure T), récupération 2 min entre efforts. Échauffement 10 min, retour au calme 5 min.</div>
        <div class="detail-divider"></div>
        <div class="detail-section-title">Paramètres</div>
        <div class="detail-stat"><span class="detail-stat-label">Durée totale</span><span class="detail-stat-value">55 min</span></div>
        <div class="detail-stat"><span class="detail-stat-label">Zone cible</span><span class="detail-stat-value">Z3 – Z4</span></div>
        <div class="detail-stat"><span class="detail-stat-label">FC cible</span><span class="detail-stat-value">162–175 bpm</span></div>
        <div class="detail-stat"><span class="detail-stat-label">Allure T</span><span class="detail-stat-value">4:52 /km</span></div>
        <div class="detail-stat"><span class="detail-stat-label">Charge estimée</span><span class="detail-stat-value">68 TSS</span></div>
        <button class="detail-btn">Marquer comme complétée</button>
      </div>
    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 2/12 — /plan · 1280×800px
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/plan-v2.html', html);
console.log('done');
