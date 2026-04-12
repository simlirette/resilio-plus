const fs = require('fs');

const iconPath = 'C:/resilio-plus/frontend/icons/';
const runner  = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'runner.png').toString('base64');
const biker   = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'biker.png').toString('base64');
const swimmer = 'data:image/png;base64,' + fs.readFileSync(iconPath + 'swimmer.png').toString('base64');
const settings= 'data:image/png;base64,' + fs.readFileSync(iconPath + 'settings.png').toString('base64');

const SIDEBAR = `<div class="sidebar">
  <div class="sidebar-logo">Resilio<span class="logo-plus">+</span></div>
  <div class="nav-section">
    <div class="nav-label">Principal</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="10" rx="8" ry="5" stroke="#52525b" stroke-width="1.5" fill="none"/><circle cx="10" cy="10" r="2.5" fill="#52525b"/><circle cx="10" cy="10" r="1" fill="white"/></svg></div>Aperçu</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="3" y="4" width="14" height="12" rx="1" stroke="#52525b" stroke-width="1.4" fill="none"/><line x1="6" y1="8" x2="14" y2="8" stroke="#52525b" stroke-width="1"/><line x1="6" y1="11" x2="14" y2="11" stroke="#52525b" stroke-width="1"/></svg></div>Plan</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M12 2L5.5 11H10L8 18L15.5 8H11Z" fill="#52525b"/></svg></div>Énergie</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M4 10C4 6.7 6.7 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 6.7 13.3 4 10 4" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M4 10C4 13.3 6.7 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M16 10C16 13.3 13.3 16 10 16" stroke="#52525b" stroke-width="1.5" fill="none" stroke-linecap="round"/><path d="M7.5 10L9.2 11.8L12.5 8.5" stroke="#52525b" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg></div>Check-in</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Données</div>
    <div class="nav-item active"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><line x1="3" y1="3" x2="17" y2="3" stroke="#09090b" stroke-width="1.5" stroke-linecap="round"/><line x1="3" y1="17" x2="17" y2="17" stroke="#09090b" stroke-width="1.5" stroke-linecap="round"/><path d="M5 3L10 11L15 3" fill="#09090b" opacity="0.35"/><path d="M5 3L10 11L15 3M5 17L10 11L15 17" stroke="#09090b" stroke-width="1.2" fill="none"/><path d="M5 17L10 11L15 17" fill="#09090b" opacity="0.65"/></svg></div>Historique</div>
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

// Sessions data — most recent first
const sessions = [
  { date:'Jeu 10 avril', sport:'running', name:'Sortie facile',       dur:'45 min', dist:'8.2 km',  tss:38,  rpe:4, hr:138, load:'légère' },
  { date:'Mer 9 avril',  sport:'running', name:'Tempo progressif',    dur:'55 min', dist:'11.4 km', tss:72,  rpe:7, hr:161, load:'modérée' },
  { date:'Mar 8 avril',  sport:'bike',    name:'Sortie endurance Z2', dur:'1h 45',  dist:'52 km',   tss:88,  rpe:5, hr:142, load:'modérée' },
  { date:'Lun 7 avril',  sport:'running', name:'Intervalles VO2max',  dur:'50 min', dist:'10.8 km', tss:95,  rpe:9, hr:172, load:'élevée' },
  { date:'Sam 5 avril',  sport:'swim',    name:'Technique & endurance',dur:'1h 00', dist:'2.8 km',  tss:54,  rpe:6, hr:148, load:'modérée' },
  { date:'Ven 4 avril',  sport:'running', name:'Récupération active', dur:'30 min', dist:'5.1 km',  tss:18,  rpe:3, hr:122, load:'légère' },
  { date:'Jeu 3 avril',  sport:'bike',    name:'FTP intervals',        dur:'1h 10', dist:'34 km',   tss:102, rpe:8, hr:168, load:'élevée' },
  { date:'Mar 1 avril',  sport:'running', name:'Sortie longue',        dur:'1h 30', dist:'19.2 km', tss:110, rpe:7, hr:155, load:'élevée' },
];

const sportColor = { running:'#3b82f6', bike:'#f59e0b', swim:'#06b6d4' };
const sportIcon  = { running:runner, bike:biker, swim:swimmer };
const sportLabel = { running:'Course', bike:'Vélo', swim:'Natation' };
const loadColor  = {
  légère:  { bg:'#f0fdf4', c:'#16a34a' },
  modérée: { bg:'#fef9ec', c:'#b45309' },
  élevée:  { bg:'#fff1f2', c:'#e11d48' },
};

const rpeColor = (r) => r <= 3 ? '#16a34a' : r <= 6 ? '#f59e0b' : '#e11d48';

// Weekly load bars (last 8 weeks)
const weekBars = [42,68,95,80,112,88,74,87];
const maxBar = Math.max(...weekBars);

const sessionRows = sessions.map((s, i) => {
  const lc = loadColor[s.load];
  const ic = sportColor[s.sport];
  return `
  <div class="session-row${i === 0 ? ' today' : ''}" onclick="">
    <div class="sr-icon sport-${s.sport}">
      <img src="${sportIcon[s.sport]}" alt="">
    </div>
    <div class="sr-main">
      <div class="sr-name">${s.name}</div>
      <div class="sr-meta">${s.date} · <span style="color:${ic}">${sportLabel[s.sport]}</span></div>
    </div>
    <div class="sr-stat"><div class="sr-stat-val">${s.dur}</div><div class="sr-stat-label">Durée</div></div>
    <div class="sr-stat"><div class="sr-stat-val">${s.dist}</div><div class="sr-stat-label">Distance</div></div>
    <div class="sr-stat"><div class="sr-stat-val" style="color:${rpeColor(s.rpe)}">${s.rpe}<span style="font-size:10px;color:#a1a1aa">/10</span></div><div class="sr-stat-label">RPE</div></div>
    <div class="sr-stat"><div class="sr-stat-val">${s.tss}</div><div class="sr-stat-label">TSS</div></div>
    <div class="sr-badge" style="background:${lc.bg};color:${lc.c}">${s.load}</div>
    <svg class="sr-chevron" viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M6 4l4 4-4 4" stroke="#d4d4d8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
  </div>`;
}).join('');

const barChart = weekBars.map((v, i) => {
  const h = Math.round((v / maxBar) * 72);
  const isLast = i === weekBars.length - 1;
  return `<div style="display:flex;flex-direction:column;align-items:center;gap:4px;flex:1">
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:${isLast?'#09090b':'#a1a1aa'}">${v}</div>
    <div style="width:100%;height:${h}px;background:${isLast?'#18181b':'#e4e4e7'};border-radius:3px 3px 0 0"></div>
  </div>`;
}).join('');

const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Historique</title>
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
.nav-item { display:flex; align-items:center; gap:10px; padding:11px 12px; border-radius:8px; font-size:14px; color:#52525b; margin-bottom:2px; border-left:2px solid transparent; cursor:pointer; }
.nav-item.active { background:#f4f4f5; color:#09090b; border-left:2px solid #18181b; font-weight:500; }
.nav-icon { width:22px; height:22px; display:flex; align-items:center; justify-content:center; flex-shrink:0; opacity:0.45; }
.nav-item.active .nav-icon { opacity:1; }
.nav-icon svg { width:18px; height:18px; }
.sidebar-footer { margin-top:auto; padding:16px 20px 0; border-top:1px solid #e4e4e7; display:flex; align-items:center; gap:12px; }
.avatar { width:36px; height:36px; border-radius:50%; background:#18181b; color:white; font-size:13px; font-weight:600; display:flex; align-items:center; justify-content:center; }
.avatar-name { font-size:13px; font-weight:500; color:#09090b; }
.avatar-status { font-size:11px; color:#16a34a; display:flex; align-items:center; gap:4px; }
.avatar-status::before { content:''; width:6px; height:6px; background:#16a34a; border-radius:50%; display:inline-block; }

/* ── MAIN ── */
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; }

/* ── HEADER ── */
.page-header { padding:22px 28px 18px; border-bottom:1px solid #e4e4e7; flex-shrink:0; display:flex; align-items:center; justify-content:space-between; gap:20px; }
.page-title { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; letter-spacing:-0.02em; }

/* Filters */
.filters { display:flex; align-items:center; gap:8px; }
.filter-group { display:flex; border:1px solid #e4e4e7; border-radius:8px; overflow:hidden; background:#fff; }
.filter-btn { font-size:12px; font-weight:500; padding:6px 12px; border:none; background:transparent; cursor:pointer; color:#71717a; border-right:1px solid #e4e4e7; white-space:nowrap; }
.filter-btn:last-child { border-right:none; }
.filter-btn.active { background:#18181b; color:#fff; }

/* ── BODY: list + sidebar ── */
.body { flex:1; display:flex; overflow:hidden; }

/* Session list */
.session-list { flex:1; overflow-y:auto; padding:8px 0; }
.session-list::-webkit-scrollbar { width:4px; }
.session-list::-webkit-scrollbar-thumb { background:#e4e4e7; border-radius:2px; }

.session-row {
  display:flex; align-items:center; gap:14px;
  padding:12px 28px; cursor:pointer; border-bottom:1px solid #f4f4f5;
  transition:background 0.1s;
}
.session-row:hover { background:#f9f9f9; }
.session-row.today { background:#fafafa; }

.sr-icon { width:42px; height:42px; border-radius:10px; background:#e4e4e7; display:flex; align-items:center; justify-content:center; overflow:hidden; flex-shrink:0; }
.sr-icon img { object-fit:contain; display:block; }
.sr-icon.sport-running img { width:82%; height:82%; }
.sr-icon.sport-bike    img { width:68%; height:68%; }
.sr-icon.sport-swim    img { width:92%; height:92%; }

.sr-main { flex:1; min-width:0; }
.sr-name { font-size:13px; font-weight:500; color:#09090b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sr-meta { font-size:11px; color:#a1a1aa; margin-top:2px; }

.sr-stat { text-align:center; min-width:52px; }
.sr-stat-val { font-family:'DM Mono',monospace; font-size:13px; font-weight:500; color:#09090b; }
.sr-stat-label { font-size:9px; color:#a1a1aa; text-transform:uppercase; letter-spacing:0.06em; margin-top:2px; }

.sr-badge { font-size:10px; font-weight:500; padding:3px 8px; border-radius:10px; white-space:nowrap; }
.sr-chevron { flex-shrink:0; }

/* ── RIGHT SIDEBAR ── */
.right-panel { width:240px; min-width:240px; border-left:1px solid #e4e4e7; padding:20px 20px; display:flex; flex-direction:column; gap:20px; overflow-y:auto; background:#fff; }

.rp-title { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:10px; }

/* Summary stats */
.summary-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.summary-card { background:#f4f4f5; border-radius:8px; padding:9px 10px; }
.sc-val { font-family:'DM Mono',monospace; font-size:16px; font-weight:500; color:#09090b; }
.sc-label { font-size:9px; color:#a1a1aa; text-transform:uppercase; letter-spacing:0.07em; margin-top:2px; }

/* Sport breakdown */
.sport-bar-row { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.sport-bar-label { font-size:11px; color:#52525b; width:60px; flex-shrink:0; }
.sport-bar-track { flex:1; height:5px; background:#f0f0f0; border-radius:3px; }
.sport-bar-fill { height:100%; border-radius:3px; }
.sport-bar-val { font-family:'DM Mono',monospace; font-size:10px; color:#71717a; width:28px; text-align:right; flex-shrink:0; }

/* Load bars */
.bar-chart { display:flex; align-items:flex-end; gap:3px; height:80px; padding-top:8px; }
.week-labels { display:flex; gap:3px; margin-top:4px; }
.week-label { flex:1; text-align:center; font-size:8px; color:#a1a1aa; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}
  <div class="main">

    <div class="page-header">
      <div class="page-title">Historique</div>
      <div class="filters">
        <!-- Sport filter -->
        <div class="filter-group">
          <button class="filter-btn active">Tous</button>
          <button class="filter-btn">Course</button>
          <button class="filter-btn">Vélo</button>
          <button class="filter-btn">Natation</button>
        </div>
        <!-- Period filter -->
        <div class="filter-group">
          <button class="filter-btn">7 j</button>
          <button class="filter-btn active">30 j</button>
          <button class="filter-btn">3 mois</button>
        </div>
      </div>
    </div>

    <div class="body">
      <!-- Session list -->
      <div class="session-list">
        ${sessionRows}
      </div>

      <!-- Right stats panel -->
      <div class="right-panel">

        <div>
          <div class="rp-title">Ce mois — résumé</div>
          <div class="summary-grid">
            <div class="summary-card"><div class="sc-val">18</div><div class="sc-label">Séances</div></div>
            <div class="summary-card"><div class="sc-val">22h</div><div class="sc-label">Volume</div></div>
            <div class="summary-card"><div class="sc-val">412</div><div class="sc-label">TSS total</div></div>
            <div class="summary-card"><div class="sc-val">6.1</div><div class="sc-label">RPE moy.</div></div>
          </div>
        </div>

        <div>
          <div class="rp-title">Répartition sports</div>
          <div class="sport-bar-row">
            <div class="sport-bar-label">Course</div>
            <div class="sport-bar-track"><div class="sport-bar-fill" style="width:62%;background:#3b82f6"></div></div>
            <div class="sport-bar-val">62%</div>
          </div>
          <div class="sport-bar-row">
            <div class="sport-bar-label">Vélo</div>
            <div class="sport-bar-track"><div class="sport-bar-fill" style="width:26%;background:#f59e0b"></div></div>
            <div class="sport-bar-val">26%</div>
          </div>
          <div class="sport-bar-row">
            <div class="sport-bar-label">Natation</div>
            <div class="sport-bar-track"><div class="sport-bar-fill" style="width:12%;background:#06b6d4"></div></div>
            <div class="sport-bar-val">12%</div>
          </div>
        </div>

        <div>
          <div class="rp-title">Charge hebdo (TSS)</div>
          <div class="bar-chart">
            ${barChart}
          </div>
          <div class="week-labels">
            ${['S-7','S-6','S-5','S-4','S-3','S-2','S-1','Cette sem.'].map(l=>`<div class="week-label">${l}</div>`).join('')}
          </div>
        </div>

      </div>
    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 6/12 — /history · 1280×800px
</div>

<script>
// Filter toggle demo
document.querySelectorAll('.filter-group').forEach(group => {
  group.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      group.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});
</script>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/268-1775885848/content/history.html', html);
console.log('done');
