const fs = require('fs');
const r = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');
const sw = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/swimmer.png').toString('base64');
const b = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/biker.png').toString('base64');
const g = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');

const out = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Icons réels</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=Playfair+Display:wght@400&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #f0f0f0; display: flex; align-items: flex-start; justify-content: center; gap: 36px; padding: 40px; font-family: 'DM Sans', system-ui; min-height: 100vh; flex-wrap: wrap; }
  .panel { background: white; border-radius: 14px; border: 1px solid #e4e4e7; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 28px; width: 380px; }
  .panel-title { font-family: 'Playfair Display', serif; font-size: 17px; color: #09090b; margin-bottom: 6px; }
  .panel-sub { font-size: 12px; color: #71717a; margin-bottom: 22px; }
  .section-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #a1a1aa; margin-bottom: 14px; margin-top: 20px; }
  .icon-row { display: flex; gap: 16px; flex-wrap: wrap; }
  .icon-item { display: flex; flex-direction: column; align-items: center; gap: 8px; }
  .box-dark { width: 80px; height: 80px; background: #18181b; border-radius: 14px; display: flex; align-items: center; justify-content: center; }
  .box-dark img { width: 52px; height: 52px; object-fit: contain; filter: invert(1); }
  .box-light { width: 80px; height: 80px; background: #f4f4f5; border: 1px solid #e4e4e7; border-radius: 14px; display: flex; align-items: center; justify-content: center; }
  .box-light img { width: 52px; height: 52px; object-fit: contain; }
  .icon-label { font-size: 11px; color: #71717a; text-transform: uppercase; letter-spacing: 0.08em; text-align: center; }
  hr { border: none; border-top: 1px solid #e4e4e7; margin: 20px 0; }
  .session-card { background: #fff; border: 1px solid #e4e4e7; border-radius: 12px; padding: 18px 22px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 10px; }
  .session-sport { width: 52px; height: 52px; background: #18181b; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .session-sport img { width: 32px; height: 32px; object-fit: contain; filter: invert(1); }
  .session-type { font-size: 15px; font-weight: 600; color: #09090b; margin-bottom: 3px; }
  .session-meta { font-size: 12px; color: #71717a; }
  .sidebar { width: 240px; background: #fff; border-radius: 14px; box-shadow: 0 4px 24px rgba(0,0,0,0.1); padding: 24px 0 20px; display: flex; flex-direction: column; border: 1px solid #e4e4e7; align-self: flex-start; }
  .sidebar-logo { font-family: 'Playfair Display', serif; font-size: 22px; color: #09090b; padding: 0 22px 22px; border-bottom: 1px solid #e4e4e7; }
  .sidebar-logo span { color: #16a34a; }
  .nav-section { padding: 16px 14px 4px; }
  .nav-label { font-size: 9px; text-transform: uppercase; letter-spacing: 0.14em; color: #a1a1aa; padding: 0 8px; margin-bottom: 4px; }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 8px; font-size: 14px; color: #52525b; margin-bottom: 2px; border-left: 2px solid transparent; }
  .nav-item.active { background: #f4f4f5; color: #09090b; border-left: 2px solid #18181b; font-weight: 500; }
  .nav-icon { width: 22px; height: 22px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; opacity: 0.5; }
  .nav-item.active .nav-icon { opacity: 1; }
  .nav-icon img { width: 18px; height: 18px; object-fit: contain; }
  .nav-icon svg { width: 18px; height: 18px; }
  .sidebar-footer { margin-top: auto; padding: 14px 18px 0; border-top: 1px solid #e4e4e7; display: flex; align-items: center; gap: 10px; }
  .avatar { width: 34px; height: 34px; border-radius: 50%; background: #18181b; color: white; font-size: 13px; font-weight: 600; display: flex; align-items: center; justify-content: center; }
  .avatar-name { font-size: 13px; font-weight: 500; color: #09090b; }
  .avatar-status { font-size: 11px; color: #16a34a; }
</style>
</head>
<body>

<div class="panel">
  <div class="panel-title">Icônes sport — PNGs originaux</div>
  <div class="panel-sub">RGBA transparent. filter:invert(1) pour fond sombre.</div>

  <div class="section-label">Fond sombre — cards de séance</div>
  <div class="icon-row">
    <div class="icon-item"><div class="box-dark"><img src="${r}" alt="course"></div><div class="icon-label">Course</div></div>
    <div class="icon-item"><div class="box-dark"><img src="${sw}" alt="natation"></div><div class="icon-label">Natation</div></div>
    <div class="icon-item"><div class="box-dark"><img src="${b}" alt="vélo"></div><div class="icon-label">Vélo</div></div>
  </div>

  <div class="section-label">Fond clair</div>
  <div class="icon-row">
    <div class="icon-item"><div class="box-light"><img src="${r}" alt="course"></div><div class="icon-label">Course</div></div>
    <div class="icon-item"><div class="box-light"><img src="${sw}" alt="natation"></div><div class="icon-label">Natation</div></div>
    <div class="icon-item"><div class="box-light"><img src="${b}" alt="vélo"></div><div class="icon-label">Vélo</div></div>
  </div>

  <hr>
  <div class="section-label">Aperçu cards de séance réelles</div>
  <div class="session-card">
    <div class="session-sport"><img src="${r}" alt="course"></div>
    <div><div class="session-type">Course — Tempo progressif</div><div class="session-meta">Aujourd'hui · 17h00 · 55 min</div></div>
  </div>
  <div class="session-card">
    <div class="session-sport"><img src="${sw}" alt="natation"></div>
    <div><div class="session-type">Natation — Endurance</div><div class="session-meta">Mercredi · 7h00 · 45 min</div></div>
  </div>
  <div class="session-card">
    <div class="session-sport"><img src="${b}" alt="vélo"></div>
    <div><div class="session-type">Vélo — Zone 2</div><div class="session-meta">Samedi · 9h00 · 90 min</div></div>
  </div>
</div>

<div class="sidebar">
  <div class="sidebar-logo">Resilio<span>+</span></div>
  <div class="nav-section">
    <div class="nav-label">Principal</div>
    <div class="nav-item active">
      <div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="10" rx="8" ry="5" stroke="#09090b" stroke-width="1.5" fill="none"/><circle cx="10" cy="10" r="2.5" fill="#09090b"/><circle cx="10" cy="10" r="1" fill="white"/></svg></div>Aperçu
    </div>
    <div class="nav-item">
      <div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="3" y="4" width="14" height="12" rx="1" stroke="#52525b" stroke-width="1.4" fill="none"/><line x1="6" y1="8" x2="14" y2="8" stroke="#52525b" stroke-width="1"/><line x1="6" y1="11" x2="14" y2="11" stroke="#52525b" stroke-width="1"/><line x1="6" y1="14" x2="10" y2="14" stroke="#52525b" stroke-width="1"/></svg></div>Plan
    </div>
    <div class="nav-item">
      <div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M12 2L5.5 11H10L8 18L15.5 8H11Z" fill="#52525b"/></svg></div>Énergie
    </div>
    <div class="nav-item">
      <div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M4 10C4 6.7 6.7 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 6.7 13.3 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M4 10C4 13.3 6.7 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 13.3 13.3 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M7.5 10L9.2 11.8L12.5 8.5" stroke="#52525b" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></div>Check-in
    </div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Données</div>
    <div class="nav-item">
      <div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><line x1="3" y1="3" x2="17" y2="3" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/><line x1="3" y1="17" x2="17" y2="17" stroke="#52525b" stroke-width="1.5" stroke-linecap="round"/><path d="M5 3L10 11L15 3" fill="#52525b" opacity="0.35"/><path d="M5 3L10 11L15 3M5 17L10 11L15 17" stroke="#52525b" stroke-width="1.2" fill="none"/><path d="M5 17L10 11L15 17" fill="#52525b" opacity="0.65"/></svg></div>Historique
    </div>
    <div class="nav-item">
      <div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="2" y="2" width="16" height="16" rx="1.5" stroke="#52525b" stroke-width="1.3" fill="none"/><rect x="5" y="12" width="2.5" height="4" rx="0.5" fill="#52525b" opacity="0.4"/><rect x="8.8" y="9.5" width="2.5" height="6.5" rx="0.5" fill="#52525b" opacity="0.7"/><rect x="12.5" y="6" width="2.5" height="10" rx="0.5" fill="#52525b"/></svg></div>Analytiques
    </div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Compte</div>
    <div class="nav-item">
      <div class="nav-icon" style="opacity:0.5"><img src="${g}" style="width:18px;height:18px;object-fit:contain"></div>Paramètres
    </div>
  </div>
  <div class="sidebar-footer">
    <div class="avatar">S</div>
    <div><div class="avatar-name">Simon</div><div class="avatar-status">● Récupération optimale</div></div>
  </div>
</div>

<div style="position:fixed;bottom:16px;left:0;right:0;text-align:center;font-size:11px;color:#71717a;font-family:system-ui">
  PNGs base64 embarqués · http://localhost:59489
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/icons-clean.html', out);
console.log('done');
