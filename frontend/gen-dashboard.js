const fs = require('fs');

const runner = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');
const swimmer = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/swimmer.png').toString('base64');
const biker = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/biker.png').toString('base64');
const settings = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');

const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400&family=Playfair+Display:wght@400;600&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', system-ui, sans-serif;
    background: #e8e8e8;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 32px;
  }

  /* ── FRAME ── */
  .frame {
    width: 1280px;
    height: 800px;
    background: #fafafa;
    border-radius: 16px;
    box-shadow: 0 12px 64px rgba(0,0,0,0.16);
    display: flex;
    overflow: hidden;
  }

  /* ── SIDEBAR ── */
  .sidebar {
    width: 260px;
    min-width: 260px;
    background: #ffffff;
    border-right: 1px solid #e4e4e7;
    display: flex;
    flex-direction: column;
    padding: 32px 0 24px;
  }
  .sidebar-logo {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 24px;
    color: #09090b;
    padding: 0 28px 28px;
    border-bottom: 1px solid #e4e4e7;
    letter-spacing: -0.01em;
  }
  .sidebar-logo span { color: #16a34a; }

  .nav-section { padding: 20px 16px 4px; }
  .nav-label {
    font-family: 'DM Sans', system-ui;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #a1a1aa;
    padding: 0 8px;
    margin-bottom: 4px;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
    border-radius: 8px;
    font-family: 'DM Sans', system-ui;
    font-size: 14px;
    font-weight: 400;
    color: #52525b;
    margin-bottom: 2px;
    border-left: 2px solid transparent;
    cursor: pointer;
  }
  .nav-item.active {
    background: #f4f4f5;
    color: #09090b;
    border-left: 2px solid #18181b;
    font-weight: 500;
  }
  .nav-icon {
    width: 22px; height: 22px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    opacity: 0.45;
  }
  .nav-item.active .nav-icon { opacity: 1; }
  .nav-icon svg { width: 18px; height: 18px; }
  .nav-icon img { width: 18px; height: 18px; object-fit: contain; }

  .sidebar-footer {
    margin-top: auto;
    padding: 16px 20px 0;
    border-top: 1px solid #e4e4e7;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: #18181b;
    color: white;
    font-size: 13px;
    font-weight: 600;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    font-family: 'DM Sans', system-ui;
  }
  .avatar-name { font-size: 13px; font-weight: 500; color: #09090b; }
  .avatar-status {
    font-size: 11px; color: #16a34a;
    display: flex; align-items: center; gap: 4px;
  }
  .avatar-status::before {
    content: ''; width: 6px; height: 6px;
    background: #16a34a; border-radius: 50%;
    display: inline-block;
  }

  /* ── MAIN ── */
  .main {
    flex: 1;
    overflow-y: auto;
    padding: 48px 52px;
  }

  /* Page header */
  .page-date {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #71717a;
    margin-bottom: 8px;
    font-family: 'DM Sans', system-ui;
  }
  .page-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 34px;
    color: #09090b;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin-bottom: 6px;
  }
  .page-subtitle {
    font-size: 15px;
    color: #71717a;
    margin-bottom: 40px;
    line-height: 1.6;
  }

  /* Section label */
  .section-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #a1a1aa;
    margin-bottom: 12px;
    font-family: 'DM Sans', system-ui;
  }

  /* Cards base */
  .card {
    background: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 12px;
    padding: 24px 28px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }

  /* ── STATUS CARD ── */
  .status-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }
  .status-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }
  .status-dot {
    width: 10px; height: 10px;
    background: #16a34a;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .status-value {
    font-size: 17px;
    font-weight: 600;
    color: #16a34a;
  }
  .status-desc {
    font-size: 14px;
    color: #52525b;
    line-height: 1.55;
    max-width: 500px;
  }
  .status-badge {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #16a34a;
    font-size: 12px;
    font-weight: 500;
    font-family: 'DM Sans', system-ui;
    padding: 7px 16px;
    border-radius: 20px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* ── METRICS ROW ── */
  .metrics-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 20px;
  }
  .metric-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #71717a;
    margin-bottom: 14px;
    font-family: 'DM Sans', system-ui;
  }
  .metric-value {
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 48px;
    color: #09090b;
    line-height: 1;
    letter-spacing: -0.03em;
    margin-bottom: 8px;
  }
  .metric-unit {
    font-size: 16px;
    color: #71717a;
    font-family: 'DM Sans', system-ui;
    font-weight: 400;
  }
  .metric-bar {
    height: 4px;
    background: #f4f4f5;
    border-radius: 2px;
    overflow: hidden;
    margin-bottom: 8px;
  }
  .metric-bar-fill { height: 100%; border-radius: 2px; }
  .metric-trend {
    font-size: 12px;
    font-family: 'DM Sans', system-ui;
  }
  .trend-green { color: #16a34a; }
  .trend-amber { color: #d97706; }
  .trend-neutral { color: #71717a; }

  /* ── SESSION CARD ── */
  .session-card {
    display: flex;
    align-items: center;
    gap: 22px;
    margin-bottom: 20px;
  }
  .session-sport-icon {
    width: 56px; height: 56px;
    background: #18181b;
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .session-sport-icon img {
    width: 34px; height: 34px;
    object-fit: contain;
    filter: invert(1);
  }
  .session-info { flex: 1; }
  .session-type {
    font-size: 17px;
    font-weight: 600;
    color: #09090b;
    margin-bottom: 3px;
  }
  .session-meta {
    font-size: 12px;
    color: #71717a;
    margin-bottom: 7px;
    font-family: 'DM Sans', system-ui;
  }
  .session-desc {
    font-size: 13px;
    color: #52525b;
    line-height: 1.55;
  }
  .session-time {
    text-align: right;
    flex-shrink: 0;
  }
  .session-time-value {
    font-family: 'DM Mono', monospace;
    font-size: 28px;
    color: #09090b;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 4px;
  }
  .session-time-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #a1a1aa;
    font-family: 'DM Sans', system-ui;
  }

  /* ── WEEK CHART ── */
  .week-card {}
  .week-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
  }
  .week-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #a1a1aa;
    font-family: 'DM Sans', system-ui;
  }
  .week-summary {
    font-size: 12px;
    color: #71717a;
    font-family: 'DM Sans', system-ui;
  }
  .week-bars {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    height: 80px;
  }
  .week-bar-wrap {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    height: 100%;
    justify-content: flex-end;
  }
  .week-bar {
    width: 100%;
    border-radius: 3px 3px 0 0;
    min-height: 3px;
  }
  .week-day {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #a1a1aa;
    font-family: 'DM Sans', system-ui;
  }
  .week-day.today { color: #09090b; font-weight: 600; }
</style>
</head>
<body>
<div class="frame">

  <!-- ── SIDEBAR ── -->
  <div class="sidebar">
    <div class="sidebar-logo">Resilio<span>+</span></div>

    <div class="nav-section">
      <div class="nav-label">Principal</div>

      <div class="nav-item active">
        <div class="nav-icon">
          <svg viewBox="0 0 20 20" fill="none">
            <ellipse cx="10" cy="10" rx="8" ry="5" stroke="#09090b" stroke-width="1.5" fill="none"/>
            <circle cx="10" cy="10" r="2.5" fill="#09090b"/>
            <circle cx="10" cy="10" r="1" fill="white"/>
          </svg>
        </div>
        Aperçu
      </div>

      <div class="nav-item">
        <div class="nav-icon">
          <svg viewBox="0 0 20 20" fill="none">
            <rect x="3" y="4" width="14" height="12" rx="1" stroke="#52525b" stroke-width="1.4" fill="none"/>
            <path d="M3 4C3 2.5 5 2.5 5 4M17 4C17 2.5 15 2.5 15 4M3 16C3 17.5 5 17.5 5 16M17 16C17 17.5 15 17.5 15 16" stroke="#52525b" stroke-width="1.2" fill="none"/>
            <line x1="6" y1="8" x2="14" y2="8" stroke="#52525b" stroke-width="1"/>
            <line x1="6" y1="11" x2="14" y2="11" stroke="#52525b" stroke-width="1"/>
            <line x1="6" y1="14" x2="10" y2="14" stroke="#52525b" stroke-width="1"/>
          </svg>
        </div>
        Plan
      </div>

      <div class="nav-item">
        <div class="nav-icon">
          <svg viewBox="0 0 20 20" fill="none">
            <path d="M12 2L5.5 11H10L8 18L15.5 8H11Z" fill="#52525b"/>
          </svg>
        </div>
        Énergie
      </div>

      <div class="nav-item">
        <div class="nav-icon">
          <svg viewBox="0 0 20 20" fill="none">
            <path d="M4 10C4 6.7 6.7 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M16 10C16 6.7 13.3 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M4 10C4 13.3 6.7 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M16 10C16 13.3 13.3 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
            <path d="M7.5 10L9.2 11.8L12.5 8.5" stroke="#52525b" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
        </div>
        Check-in
      </div>
    </div>

    <div class="nav-section">
      <div class="nav-label">Données</div>

      <div class="nav-item">
        <div class="nav-icon">
          <svg viewBox="0 0 20 20" fill="none">
            <line x1="3" y1="3" x2="17" y2="3" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="3" y1="17" x2="17" y2="17" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M5 3L10 11L15 3" fill="#52525b" opacity="0.35"/>
            <path d="M5 3L10 11L15 3" stroke="#52525b" stroke-width="1.2" fill="none"/>
            <path d="M5 17L10 11L15 17" fill="#52525b" opacity="0.65"/>
            <path d="M5 17L10 11L15 17" stroke="#52525b" stroke-width="1.2" fill="none"/>
          </svg>
        </div>
        Historique
      </div>

      <div class="nav-item">
        <div class="nav-icon">
          <svg viewBox="0 0 20 20" fill="none">
            <rect x="2" y="2" width="16" height="16" rx="1.5" stroke="#52525b" stroke-width="1.3" fill="none"/>
            <rect x="5" y="12" width="2.5" height="4" rx="0.5" fill="#52525b" opacity="0.4"/>
            <rect x="8.8" y="9.5" width="2.5" height="6.5" rx="0.5" fill="#52525b" opacity="0.7"/>
            <rect x="12.5" y="6" width="2.5" height="10" rx="0.5" fill="#52525b"/>
          </svg>
        </div>
        Analytiques
      </div>
    </div>

    <div class="nav-section">
      <div class="nav-label">Compte</div>
      <div class="nav-item">
        <div class="nav-icon">
          <img src="${settings}" style="width:18px;height:18px;object-fit:contain">
        </div>
        Paramètres
      </div>
    </div>

    <div class="sidebar-footer">
      <div class="avatar">S</div>
      <div>
        <div class="avatar-name">Simon</div>
        <div class="avatar-status">Récupération optimale</div>
      </div>
    </div>
  </div>

  <!-- ── MAIN CONTENT ── -->
  <div class="main">

    <!-- Header -->
    <div class="page-date">Jeudi 10 avril 2026</div>
    <div class="page-title">Bonjour, Simon.</div>
    <div class="page-subtitle">Votre tableau de bord du jour.</div>

    <!-- Section 1 — Statut -->
    <div class="card status-card">
      <div>
        <div class="status-indicator">
          <div class="status-dot"></div>
          <div class="status-value">Récupération optimale</div>
        </div>
        <div class="status-desc">Toutes vos métriques sont dans la zone verte. Vous pouvez vous permettre une intensité haute aujourd'hui.</div>
      </div>
      <div class="status-badge">Intensité haute recommandée ↑</div>
    </div>

    <!-- Section 2 — 3 métriques -->
    <div class="metrics-row">
      <div class="card">
        <div class="metric-label">HRV</div>
        <div class="metric-value">68<span class="metric-unit"> ms</span></div>
        <div class="metric-bar"><div class="metric-bar-fill" style="width:72%;background:#16a34a"></div></div>
        <div class="metric-trend trend-green">↑ +4 ms vs moyenne 14j</div>
      </div>
      <div class="card">
        <div class="metric-label">Sommeil</div>
        <div class="metric-value">7<span class="metric-unit">h</span><span style="font-size:28px;color:#09090b;font-family:'DM Mono',monospace;letter-spacing:-0.02em"> 42</span><span class="metric-unit">min</span></div>
        <div class="metric-bar"><div class="metric-bar-fill" style="width:58%;background:#d97706"></div></div>
        <div class="metric-trend trend-amber">⚠ Qualité légèrement réduite</div>
      </div>
      <div class="card">
        <div class="metric-label">Energy Availability</div>
        <div class="metric-value" style="font-size:40px">+245<span class="metric-unit" style="font-size:13px"> kcal</span></div>
        <div class="metric-bar"><div class="metric-bar-fill" style="width:81%;background:#16a34a"></div></div>
        <div class="metric-trend trend-green">✓ Au-dessus du seuil (≥ 45 kcal/kg)</div>
      </div>
    </div>

    <!-- Section 3 — Prochaine séance -->
    <div class="section-label">Prochaine séance</div>
    <div class="card session-card">
      <div class="session-sport-icon">
        <img src="${runner}" alt="course">
      </div>
      <div class="session-info">
        <div class="session-type">Course — Tempo progressif</div>
        <div class="session-meta">Aujourd'hui · Zone 3–4 · 55 min</div>
        <div class="session-desc">3 × 10 min au seuil lactate, récupération 2 min entre efforts. Échauffement 10 min, retour au calme 5 min.</div>
      </div>
      <div class="session-time">
        <div class="session-time-value">17h00</div>
        <div class="session-time-label">Heure prévue</div>
      </div>
    </div>

    <!-- Section 4 — Charge semaine -->
    <div class="section-label">Charge de la semaine</div>
    <div class="card week-card">
      <div class="week-header">
        <div class="week-title">Charge de la semaine</div>
        <div class="week-summary">3 séances · 2h55 réalisées</div>
      </div>
      <div class="week-bars">
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:44px;background:#18181b;opacity:0.8"></div>
          <div class="week-day">Lun</div>
        </div>
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:64px;background:#18181b;opacity:0.8"></div>
          <div class="week-day">Mar</div>
        </div>
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:18px;background:#e4e4e7"></div>
          <div class="week-day">Mer</div>
        </div>
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:54px;background:#18181b;opacity:0.4;border:1.5px dashed #d4d4d8;border-bottom:none"></div>
          <div class="week-day today">Jeu ▶</div>
        </div>
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:40px;background:#e4e4e7"></div>
          <div class="week-day">Ven</div>
        </div>
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:72px;background:#e4e4e7"></div>
          <div class="week-day">Sam</div>
        </div>
        <div class="week-bar-wrap">
          <div class="week-bar" style="height:14px;background:#e4e4e7"></div>
          <div class="week-day">Dim</div>
        </div>
      </div>
    </div>

  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 1/12 — /dashboard · Resilio+ Premium UI · 1280×800px
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/dashboard-final2.html', html);
console.log('done');
