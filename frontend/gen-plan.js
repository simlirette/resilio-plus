const fs = require('fs');

const runner = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');
const swimmer = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/swimmer.png').toString('base64');
const biker = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/biker.png').toString('base64');
const settings = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');

const SIDEBAR = `
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
  .main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

  /* Page header */
  .page-header { padding: 40px 48px 24px; border-bottom: 1px solid #e4e4e7; flex-shrink: 0; }
  .page-date { font-size: 11px; text-transform: uppercase; letter-spacing: 0.12em; color: #71717a; margin-bottom: 6px; }
  .page-title { font-family: 'Playfair Display', serif; font-size: 30px; color: #09090b; letter-spacing: -0.02em; margin-bottom: 4px; }
  .week-range { font-size: 14px; color: #71717a; }

  /* 7-column week grid */
  .week-grid { display: grid; grid-template-columns: repeat(7, 1fr); flex: 1; overflow: hidden; }

  .day-col { border-right: 1px solid #e4e4e7; display: flex; flex-direction: column; overflow: hidden; }
  .day-col:last-child { border-right: none; }

  .day-header { padding: 14px 12px 10px; border-bottom: 1px solid #e4e4e7; flex-shrink: 0; }
  .day-name { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #a1a1aa; margin-bottom: 3px; }
  .day-date { font-family: 'DM Mono', monospace; font-size: 20px; color: #09090b; line-height: 1; }
  .day-col.today .day-name { color: #16a34a; }
  .day-col.today .day-date { color: #16a34a; }
  .day-col.rest .day-date { color: #d4d4d8; }
  .day-col.rest .day-name { color: #d4d4d8; }

  .day-body { flex: 1; padding: 10px 8px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }

  /* Session cards inside day */
  .session-pill {
    background: #fff;
    border: 1px solid #e4e4e7;
    border-radius: 10px;
    padding: 10px 10px 8px;
    cursor: pointer;
    transition: box-shadow 0.15s;
  }
  .session-pill:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  .session-pill.today-session { border-color: #d4d4d8; }
  .session-pill-sport { display: flex; align-items: center; gap: 7px; margin-bottom: 6px; }
  .sport-dot { width: 28px; height: 28px; background: #18181b; border-radius: 7px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .sport-dot img { width: 17px; height: 17px; object-fit: contain; filter: invert(1); }
  .session-pill-type { font-size: 11px; font-weight: 500; color: #09090b; line-height: 1.3; }
  .session-pill-duration { font-size: 10px; color: #71717a; margin-top: 2px; }

  /* Charge bar */
  .day-load { margin-top: auto; padding: 0 8px 10px; flex-shrink: 0; }
  .load-bar-track { height: 4px; background: #f4f4f5; border-radius: 2px; overflow: hidden; }
  .load-bar-fill { height: 100%; border-radius: 2px; }

  /* Rest day */
  .rest-label { font-size: 11px; color: #d4d4d8; text-align: center; padding: 16px 0; }

  /* Completed badge */
  .done-badge { display: inline-flex; align-items: center; gap: 3px; font-size: 10px; color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 20px; padding: 2px 7px; margin-top: 5px; }

  /* Detail panel (slide-in from right) */
  .detail-panel {
    width: 300px;
    min-width: 300px;
    background: #fff;
    border-left: 1px solid #e4e4e7;
    display: flex;
    flex-direction: column;
    padding: 28px 24px;
    overflow-y: auto;
  }
  .detail-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #a1a1aa; margin-bottom: 16px; }
  .detail-sport { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
  .detail-sport-icon { width: 52px; height: 52px; background: #18181b; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
  .detail-sport-icon img { width: 30px; height: 30px; object-fit: contain; filter: invert(1); }
  .detail-title { font-family: 'Playfair Display', serif; font-size: 18px; color: #09090b; margin-bottom: 3px; }
  .detail-meta { font-size: 12px; color: #71717a; }
  .detail-divider { border: none; border-top: 1px solid #e4e4e7; margin: 16px 0; }
  .detail-section-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #a1a1aa; margin-bottom: 10px; }
  .detail-desc { font-size: 13px; color: #52525b; line-height: 1.65; margin-bottom: 16px; }
  .detail-stat { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f4f4f5; }
  .detail-stat-label { font-size: 12px; color: #71717a; }
  .detail-stat-value { font-family: 'DM Mono', monospace; font-size: 14px; color: #09090b; }
  .detail-btn { margin-top: 20px; background: #18181b; color: white; border: none; border-radius: 8px; padding: 11px 0; width: 100%; font-family: 'DM Sans', system-ui; font-size: 14px; font-weight: 500; cursor: pointer; text-align: center; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}

  <div class="main">
    <!-- Header -->
    <div class="page-header">
      <div class="page-date">Semaine du 7 au 13 avril 2026</div>
      <div class="page-title">Plan de la semaine</div>
      <div class="week-range">Semaine 2 · Phase de construction · 3 séances planifiées</div>
    </div>

    <!-- Week grid + detail panel -->
    <div style="display:flex;flex:1;overflow:hidden">

      <!-- 7 columns -->
      <div class="week-grid">

        <!-- Lundi 7 — Course faite -->
        <div class="day-col">
          <div class="day-header">
            <div class="day-name">Lun</div>
            <div class="day-date">07</div>
          </div>
          <div class="day-body">
            <div class="session-pill">
              <div class="session-pill-sport">
                <div class="sport-dot"><img src="${runner}" alt="course"></div>
                <div>
                  <div class="session-pill-type">Sortie facile</div>
                  <div class="session-pill-duration">45 min</div>
                </div>
              </div>
              <div class="done-badge">✓ Complétée</div>
            </div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:45%;background:#16a34a"></div></div></div>
        </div>

        <!-- Mardi 8 — Muscu + Vélo faits -->
        <div class="day-col">
          <div class="day-header">
            <div class="day-name">Mar</div>
            <div class="day-date">08</div>
          </div>
          <div class="day-body">
            <div class="session-pill">
              <div class="session-pill-sport">
                <div class="sport-dot" style="background:#3f3f46"><img src="${biker}" alt="vélo"></div>
                <div>
                  <div class="session-pill-type">Zone 2 vélo</div>
                  <div class="session-pill-duration">75 min</div>
                </div>
              </div>
              <div class="done-badge">✓ Complétée</div>
            </div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:70%;background:#16a34a"></div></div></div>
        </div>

        <!-- Mercredi 9 — Repos -->
        <div class="day-col rest">
          <div class="day-header">
            <div class="day-name">Mer</div>
            <div class="day-date">09</div>
          </div>
          <div class="day-body">
            <div class="rest-label">Repos</div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:0%;background:#e4e4e7"></div></div></div>
        </div>

        <!-- Jeudi 10 — Aujourd'hui, course à faire (selected) -->
        <div class="day-col today">
          <div class="day-header">
            <div class="day-name">Jeu ▶</div>
            <div class="day-date">10</div>
          </div>
          <div class="day-body">
            <div class="session-pill today-session" style="border-color:#18181b;border-width:1.5px">
              <div class="session-pill-sport">
                <div class="sport-dot"><img src="${runner}" alt="course"></div>
                <div>
                  <div class="session-pill-type">Tempo progressif</div>
                  <div class="session-pill-duration">55 min · 17h00</div>
                </div>
              </div>
            </div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:55%;background:#18181b;opacity:0.4"></div></div></div>
        </div>

        <!-- Vendredi 11 — Natation planifiée -->
        <div class="day-col">
          <div class="day-header">
            <div class="day-name">Ven</div>
            <div class="day-date">11</div>
          </div>
          <div class="day-body">
            <div class="session-pill">
              <div class="session-pill-sport">
                <div class="sport-dot" style="background:#3f3f46"><img src="${swimmer}" alt="natation"></div>
                <div>
                  <div class="session-pill-type">Endurance eau</div>
                  <div class="session-pill-duration">45 min · 7h00</div>
                </div>
              </div>
            </div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:38%;background:#e4e4e7"></div></div></div>
        </div>

        <!-- Samedi 12 — Long run -->
        <div class="day-col">
          <div class="day-header">
            <div class="day-name">Sam</div>
            <div class="day-date">12</div>
          </div>
          <div class="day-body">
            <div class="session-pill">
              <div class="session-pill-sport">
                <div class="sport-dot"><img src="${runner}" alt="course"></div>
                <div>
                  <div class="session-pill-type">Long run Z2</div>
                  <div class="session-pill-duration">90 min · 9h00</div>
                </div>
              </div>
            </div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:78%;background:#e4e4e7"></div></div></div>
        </div>

        <!-- Dimanche 13 — Repos -->
        <div class="day-col rest">
          <div class="day-header">
            <div class="day-name">Dim</div>
            <div class="day-date">13</div>
          </div>
          <div class="day-body">
            <div class="rest-label">Repos</div>
          </div>
          <div class="day-load"><div class="load-bar-track"><div class="load-bar-fill" style="width:0%;background:#e4e4e7"></div></div></div>
        </div>

      </div>

      <!-- Detail panel (séance du jour sélectionnée) -->
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
        <div class="detail-desc">3 × 10 min au seuil lactate (allure T), récupération 2 min entre efforts. Échauffement 10 min progressif, retour au calme 5 min.</div>

        <div class="detail-section-title">Paramètres</div>
        <div class="detail-stat"><span class="detail-stat-label">Durée totale</span><span class="detail-stat-value">55 min</span></div>
        <div class="detail-stat"><span class="detail-stat-label">Zone cible</span><span class="detail-stat-value">Z3 – Z4</span></div>
        <div class="detail-stat"><span class="detail-stat-label">FC cible</span><span class="detail-stat-value">162–175 bpm</span></div>
        <div class="detail-stat"><span class="detail-stat-label">Allure T</span><span class="detail-stat-value">4:52 /km</span></div>
        <div class="detail-stat"><span class="detail-stat-label">Charge estimée</span><span class="detail-stat-value">68 TSS</span></div>

        <div class="detail-btn">Marquer comme complétée</div>
      </div>

    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 2/12 — /plan · Resilio+ Premium UI · 1280×800px
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/plan.html', html);
console.log('done');
