const fs = require('fs');

const settings = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');

const chevL = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9 3L5 7L9 11" stroke="#52525b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const chevR = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3L9 7L5 11" stroke="#52525b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// ── Mock data ──────────────────────────────────────────────────────────────
const D = {
  // Calories
  bmr: 2200, exercise: 450, ea: 245,
  get consumed() { return this.bmr + this.exercise + this.ea; }, // 2895
  // Macros [target, actual]
  macros: [
    { label:'Glucides',  target:320, actual:280, unit:'g', color:'#3b82f6' },
    { label:'Protéines', target:160, actual:145, unit:'g', color:'#f59e0b' },
    { label:'Lipides',   target:70,  actual:65,  unit:'g', color:'#8b5cf6' },
  ],
  meals: [
    { time:'7h15',  name:'Déjeuner pré-séance',   kcal:520, macro:'G78 · P28 · L12' },
    { time:'10h30', name:'Collation récupération', kcal:380, macro:'G52 · P24 · L8'  },
    { time:'13h00', name:'Dîner',                  kcal:780, macro:'G95 · P48 · L22' },
    { time:'16h30', name:'Collation après-midi',   kcal:290, macro:'G38 · P18 · L9'  },
    { time:'19h30', name:'Souper',                 kcal:875, macro:'G117 · P52 · L24'},
  ],
  // Sleep
  sleep: { total:'7h 42', score:82, deep:'1h 45', rem:'1h 52', light:'4h 05', bed:'22h30', wake:'6h12' },
  // Recovery
  hrv: 68, readiness: 84, restHR: 48, bodyTemp:'+0.1°C',
  // Readiness breakdown
  readinessDim: [
    { label:'Qualité du sommeil', val:86, color:'#3b82f6' },
    { label:'HRV',                val:82, color:'#16a34a' },
    { label:'Charge d\'entr.',    val:79, color:'#f59e0b' },
    { label:'FC repos',           val:90, color:'#8b5cf6' },
  ],
  // Weekly EA
  weekEA:     [+245, +180, -60, null, +310, -120, -200],
  weekLabels: ['L','M','M','J','V','S','D'],
};

// ── SVG donut ──────────────────────────────────────────────────────────────
const R  = 88;
const CX = 110, CY = 110;
const C  = 2 * Math.PI * R;

function donutSeg(color, len, skip, width=20) {
  return `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none"
    stroke="${color}" stroke-width="${width}"
    stroke-dasharray="${len.toFixed(2)} ${C.toFixed(2)}"
    stroke-dashoffset="${(-skip).toFixed(2)}"
    transform="rotate(-90 ${CX} ${CY})"
    stroke-linecap="butt"/>`;
}

const bmrLen  = D.bmr      / D.consumed * C;
const exLen   = D.exercise / D.consumed * C;
const eaLen   = D.ea       / D.consumed * C;

const donut = `
<svg width="220" height="220" style="display:block;margin:0 auto">
  <!-- Track -->
  <circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="#f0f0f0" stroke-width="20"/>
  <!-- BMR -->
  ${donutSeg('#e4e4e7', bmrLen, 0)}
  <!-- Exercise -->
  ${donutSeg('#fbbf24', exLen, bmrLen)}
  <!-- EA -->
  ${donutSeg('#16a34a', eaLen, bmrLen + exLen)}
  <!-- Center text -->
  <text x="${CX}" y="102" text-anchor="middle" font-family="DM Mono,monospace" font-size="26" font-weight="500" fill="#09090b">+${D.ea}</text>
  <text x="${CX}" y="120" text-anchor="middle" font-family="DM Mono,monospace" font-size="11" fill="#71717a">kcal</text>
  <text x="${CX}" y="137" text-anchor="middle" font-family="DM Sans,system-ui" font-size="9.5" fill="#a1a1aa" letter-spacing="0.08em">ÉNERGIE DISPONIBLE</text>
</svg>`;

// ── Helpers ────────────────────────────────────────────────────────────────
function macroBar(m) {
  const pct = Math.min(100, Math.round(m.actual / m.target * 100));
  return `<div class="macro-row">
    <div class="macro-label-row">
      <span class="macro-name">${m.label}</span>
      <span class="macro-vals"><span style="color:${m.color};font-weight:600">${m.actual}${m.unit}</span>&nbsp;<span class="macro-target">/ ${m.target}${m.unit}</span></span>
    </div>
    <div class="macro-track"><div class="macro-fill" style="width:${pct}%;background:${m.color}"></div></div>
  </div>`;
}

function radBar(dim) {
  return `<div style="margin-bottom:10px">
    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
      <span style="font-size:12px;color:#3f3f46">${dim.label}</span>
      <span style="font-family:'DM Mono',monospace;font-size:12px;color:${dim.color};font-weight:500">${dim.val}/100</span>
    </div>
    <div style="height:5px;background:#f4f4f5;border-radius:3px;overflow:hidden">
      <div style="height:100%;width:${dim.val}%;background:${dim.color};border-radius:3px"></div>
    </div>
  </div>`;
}

function weekBar(ea, label, today) {
  const maxH = 40, maxAbs = 350;
  const h = ea !== null ? Math.max(4, Math.round(Math.abs(ea) / maxAbs * maxH)) : 3;
  const col = ea === null ? '#e4e4e7' : ea >= 0 ? '#16a34a' : '#f87171';
  const todayCls = today ? ' today' : '';
  return `<div class="wbar-col${todayCls}">
    <div class="wbar-wrap"><div class="wbar" style="height:${h}px;background:${col}"></div></div>
    <div class="wbar-l">${label}</div>
    <div class="wbar-v" style="color:${col}">${ea !== null ? (ea>0?'+':'')+ea : '—'}</div>
  </div>`;
}

// ── Sidebar ────────────────────────────────────────────────────────────────
const SIDEBAR = `<div class="sidebar">
  <div class="sidebar-logo">Resilio<span class="logo-plus">+</span></div>
  <div class="nav-section">
    <div class="nav-label">Principal</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="10" rx="8" ry="5" stroke="#52525b" stroke-width="1.5" fill="none"/><circle cx="10" cy="10" r="2.5" fill="#52525b"/><circle cx="10" cy="10" r="1" fill="white"/></svg></div>Aperçu</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="3" y="4" width="14" height="12" rx="1" stroke="#52525b" stroke-width="1.4" fill="none"/><line x1="6" y1="8" x2="14" y2="8" stroke="#52525b" stroke-width="1"/><line x1="6" y1="11" x2="14" y2="11" stroke="#52525b" stroke-width="1"/></svg></div>Plan</div>
    <div class="nav-item active"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><path d="M12 2L5.5 11H10L8 18L15.5 8H11Z" fill="#09090b"/></svg></div>Énergie</div>
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

// ── HTML ───────────────────────────────────────────────────────────────────
const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Énergie</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@400;600&display=swap" rel="stylesheet">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'DM Sans',system-ui; background:#e8e8e8; display:flex; align-items:center; justify-content:center; min-height:100vh; padding:32px; }
.frame { width:1280px; height:800px; background:#fafafa; border-radius:16px; box-shadow:0 12px 64px rgba(0,0,0,0.16); display:flex; overflow:hidden; }

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

.main { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }

/* ── PAGE HEADER ── */
.page-header { padding:18px 28px 0; border-bottom:1px solid #e4e4e7; flex-shrink:0; }
.page-header-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.page-title { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; letter-spacing:-0.02em; }
.page-date-nav { display:flex; align-items:center; gap:10px; }
.nav-arrow { width:28px; height:28px; border-radius:7px; border:1px solid #e4e4e7; background:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0; }
.nav-arrow:hover { background:#f4f4f5; }
.nav-arrow svg { display:block; }
.page-date { font-size:13px; font-weight:500; color:#09090b; }
.day-badge { display:inline-flex; align-items:center; gap:5px; padding:3px 9px; border-radius:20px; background:#f0fdf4; border:1px solid #bbf7d0; font-size:11px; font-weight:500; color:#16a34a; }
.day-badge-dot { width:5px; height:5px; border-radius:50%; background:#16a34a; }

/* ── TAB BAR ── */
.tab-bar { display:flex; gap:2px; }
.tab-btn {
  padding:9px 16px; font-family:'DM Sans',system-ui; font-size:13px; font-weight:500;
  color:#71717a; border:none; background:transparent; cursor:pointer;
  border-bottom:2px solid transparent; margin-bottom:-1px;
  transition:color 0.12s, border-color 0.12s;
}
.tab-btn:hover { color:#09090b; }
.tab-btn.active { color:#09090b; border-bottom:2px solid #18181b; }

/* ── CONTENT ── */
.content-scroll { flex:1; overflow-y:auto; padding:24px 28px 32px; }
.content-scroll::-webkit-scrollbar { width:4px; }
.content-scroll::-webkit-scrollbar-thumb { background:#e4e4e7; border-radius:2px; }

.tab-content { display:none; }
.tab-content.active { display:block; }

/* ── CARD ── */
.card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:18px; }
.card-title { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:12px; }
.divider { border:none; border-top:1px solid #f4f4f5; margin:14px 0; }

/* ── RÉSUMÉ TAB ── */
.resume-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; align-items:start; }
.resume-left { display:flex; flex-direction:column; align-items:center; gap:16px; }

.donut-legend { display:flex; gap:16px; justify-content:center; flex-wrap:wrap; }
.legend-item { display:flex; align-items:center; gap:6px; font-size:11px; color:#52525b; }
.legend-dot { width:9px; height:9px; border-radius:50%; flex-shrink:0; }

.summary-cards { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.summary-card {
  background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:14px 16px;
  cursor:pointer; transition:border-color 0.15s, box-shadow 0.15s;
}
.summary-card:hover { border-color:#18181b; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.sc-label { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:6px; }
.sc-value { font-family:'DM Mono',monospace; font-size:19px; font-weight:500; color:#09090b; line-height:1; margin-bottom:4px; }
.sc-sub { font-size:11px; color:#71717a; }
.sc-bar { height:4px; background:#f4f4f5; border-radius:2px; overflow:hidden; margin-top:8px; }
.sc-bar-fill { height:100%; border-radius:2px; }
.sc-arrow { font-size:10px; color:#a1a1aa; float:right; margin-top:-16px; }

/* ── NUTRITION TAB ── */
.macro-row { margin-bottom:12px; }
.macro-label-row { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; }
.macro-name { font-size:13px; font-weight:500; color:#3f3f46; }
.macro-vals { font-size:12px; }
.macro-target { color:#a1a1aa; }
.macro-track { height:7px; background:#f4f4f5; border-radius:4px; overflow:hidden; }
.macro-fill { height:100%; border-radius:4px; }

.cal-bar { display:flex; height:10px; border-radius:5px; overflow:hidden; gap:2px; margin:10px 0 8px; }
.cal-seg { height:100%; border-radius:3px; }
.cal-legend { display:flex; gap:14px; flex-wrap:wrap; }
.cal-leg { display:flex; align-items:center; gap:5px; font-size:11px; color:#52525b; }
.cal-dot { width:8px; height:8px; border-radius:2px; }

.meal-item { display:flex; align-items:center; padding:9px 0; border-bottom:1px solid #f4f4f5; gap:10px; }
.meal-item:last-child { border-bottom:none; }
.meal-time { font-family:'DM Mono',monospace; font-size:10px; color:#a1a1aa; width:38px; flex-shrink:0; }
.meal-name { font-size:12px; color:#3f3f46; flex:1; }
.meal-kcal { font-family:'DM Mono',monospace; font-size:12px; font-weight:500; color:#09090b; white-space:nowrap; }
.meal-macro { font-size:10px; color:#a1a1aa; text-align:right; white-space:nowrap; }

.nut-grid { display:grid; grid-template-columns:1.1fr 1fr; gap:18px; }

/* ── READINESS TAB ── */
.read-hero { display:flex; align-items:center; gap:24px; margin-bottom:20px; }
.read-score-ring { width:90px; height:90px; flex-shrink:0; }
.read-score-num { font-family:'DM Mono',monospace; font-size:32px; font-weight:500; color:#09090b; line-height:1; }
.read-score-label { font-size:12px; color:#71717a; margin-top:4px; }
.read-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.read-cell { background:#f9f9f9; border-radius:10px; padding:12px 14px; }
.read-cell-label { font-size:10px; color:#a1a1aa; margin-bottom:4px; }
.read-cell-val { font-family:'DM Mono',monospace; font-size:16px; font-weight:500; }

/* ── SOMMEIL TAB ── */
.sleep-timeline { display:flex; height:12px; border-radius:6px; overflow:hidden; gap:2px; margin:12px 0; }
.sleep-seg { height:100%; border-radius:2px; }
.sleep-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-top:12px; }
.sleep-cell { background:#f9f9f9; border-radius:10px; padding:12px 14px; text-align:center; }
.sleep-cell-label { font-size:10px; color:#a1a1aa; margin-bottom:4px; }
.sleep-cell-val { font-family:'DM Mono',monospace; font-size:15px; font-weight:500; color:#09090b; }
.sleep-hero { display:grid; grid-template-columns:1fr 1fr; gap:18px; }

/* ── HRV TAB ── */
.hrv-hero { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:20px; }
.hrv-card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:18px; text-align:center; }
.hrv-card-label { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:8px; }
.hrv-card-val { font-family:'DM Mono',monospace; font-size:28px; font-weight:500; color:#09090b; }
.hrv-card-unit { font-size:12px; color:#a1a1aa; margin-top:2px; }
.hrv-card-trend { font-size:11px; color:#16a34a; margin-top:6px; }

/* ── WEEKLY EA ── */
.wbar-chart { display:flex; gap:8px; height:90px; padding-bottom:22px; position:relative; }
.wbar-chart::after { content:''; position:absolute; bottom:22px; left:0; right:0; height:1px; background:#e8e8e8; }
.wbar-col { flex:1; display:flex; flex-direction:column; align-items:center; gap:2px; }
.wbar-col.today .wbar { outline:1.5px solid #16a34a; outline-offset:2px; }
.wbar-wrap { flex:1; display:flex; align-items:flex-end; width:100%; justify-content:center; }
.wbar { width:80%; max-width:36px; border-radius:3px 3px 0 0; min-height:3px; }
.wbar-l { font-size:10px; color:#a1a1aa; }
.wbar-v { font-family:'DM Mono',monospace; font-size:9px; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}
  <div class="main">

    <!-- Page header + tabs -->
    <div class="page-header">
      <div class="page-header-top">
        <div style="display:flex;align-items:center;gap:12px">
          <div class="page-title">Énergie</div>
          <div class="day-badge"><div class="day-badge-dot"></div>Haute glucides · Jour d'entraînement</div>
        </div>
        <div class="page-date-nav">
          <button class="nav-arrow">${chevL}</button>
          <div class="page-date">Jeudi 10 avril 2026</div>
          <button class="nav-arrow">${chevR}</button>
        </div>
      </div>
      <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('resume')">Résumé</button>
        <button class="tab-btn" onclick="switchTab('nutrition')">Nutrition</button>
        <button class="tab-btn" onclick="switchTab('readiness')">Readiness</button>
        <button class="tab-btn" onclick="switchTab('sommeil')">Sommeil</button>
        <button class="tab-btn" onclick="switchTab('hrv')">HRV</button>
      </div>
    </div>

    <div class="content-scroll">

      <!-- ══ RÉSUMÉ ══ -->
      <div class="tab-content active" id="tab-resume">
        <div class="resume-grid">

          <!-- Left: donut + legend -->
          <div class="resume-left">
            ${donut}
            <div class="donut-legend">
              <div class="legend-item"><div class="legend-dot" style="background:#e4e4e7"></div>Métabolisme ${D.bmr} kcal</div>
              <div class="legend-item"><div class="legend-dot" style="background:#fbbf24"></div>Exercice ${D.exercise} kcal</div>
              <div class="legend-item"><div class="legend-dot" style="background:#16a34a"></div>Disponible +${D.ea} kcal</div>
            </div>
            <div style="text-align:center;font-size:12px;color:#71717a;max-width:260px;line-height:1.5">
              Consommé ${D.consumed} kcal sur ${D.consumed} kcal planifiés.<br>Zone d'énergie optimale pour aujourd'hui.
            </div>
          </div>

          <!-- Right: 4 summary cards -->
          <div style="display:flex;flex-direction:column;gap:12px">
            <div class="summary-cards">

              <!-- Nutrition -->
              <div class="summary-card" onclick="switchTab('nutrition')">
                <div class="sc-label">Nutrition</div>
                <div class="sc-value">${D.consumed}<span style="font-size:12px;color:#a1a1aa"> kcal</span></div>
                <div class="sc-sub">G280 · P145 · L65 g</div>
                <div class="sc-bar">
                  <div class="sc-bar-fill" style="width:87%;background:#3b82f6"></div>
                </div>
                <div style="font-size:10px;color:#a1a1aa;margin-top:4px;text-align:right">87% des objectifs →</div>
              </div>

              <!-- Readiness -->
              <div class="summary-card" onclick="switchTab('readiness')">
                <div class="sc-label">Readiness</div>
                <div class="sc-value">${D.readiness}<span style="font-size:12px;color:#a1a1aa"> /100</span></div>
                <div class="sc-sub">Récupération optimale</div>
                <div class="sc-bar">
                  <div class="sc-bar-fill" style="width:${D.readiness}%;background:#16a34a"></div>
                </div>
                <div style="font-size:10px;color:#a1a1aa;margin-top:4px;text-align:right">Très bien reposé →</div>
              </div>

              <!-- Sommeil -->
              <div class="summary-card" onclick="switchTab('sommeil')">
                <div class="sc-label">Sommeil</div>
                <div class="sc-value">${D.sleep.total}</div>
                <div class="sc-sub">Score ${D.sleep.score}/100 · Profond ${D.sleep.deep}</div>
                <div class="sc-bar" style="margin-top:8px">
                  <div class="sc-bar-fill" style="width:${D.sleep.score}%;background:#3b82f6"></div>
                </div>
                <div style="font-size:10px;color:#a1a1aa;margin-top:4px;text-align:right">${D.sleep.bed} → ${D.sleep.wake} →</div>
              </div>

              <!-- HRV -->
              <div class="summary-card" onclick="switchTab('hrv')">
                <div class="sc-label">HRV · RMSSD</div>
                <div class="sc-value">${D.hrv}<span style="font-size:12px;color:#a1a1aa"> ms</span></div>
                <div class="sc-sub">FC repos ${D.restHR} bpm · ${D.bodyTemp}</div>
                <div class="sc-bar" style="margin-top:8px">
                  <div class="sc-bar-fill" style="width:74%;background:#8b5cf6"></div>
                </div>
                <div style="font-size:10px;color:#a1a1aa;margin-top:4px;text-align:right">↑ +4 ms vs moy. →</div>
              </div>

            </div>

            <!-- Weekly EA mini chart -->
            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
                <div class="card-title" style="margin-bottom:0">Énergie disponible · semaine</div>
                <div style="font-size:10px;color:#a1a1aa">kcal/jour</div>
              </div>
              <div class="wbar-chart">
                ${D.weekEA.map((ea, i) => weekBar(ea, D.weekLabels[i], i === 3)).join('')}
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- ══ NUTRITION ══ -->
      <div class="tab-content" id="tab-nutrition">
        <div class="nut-grid">
          <div style="display:flex;flex-direction:column;gap:14px">

            <div class="card">
              <div class="card-title">Bilan calorique</div>
              <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span style="font-size:12px;color:#71717a">Consommé</span>
                <span style="font-family:'DM Mono',monospace;font-size:14px;font-weight:500;color:#09090b">${D.consumed} kcal</span>
              </div>
              <div class="cal-bar">
                <div class="cal-seg" style="width:${Math.round(D.bmr/D.consumed*100)}%;background:#e0e0e0"></div>
                <div class="cal-seg" style="width:${Math.round(D.exercise/D.consumed*100)}%;background:#fbbf24"></div>
                <div class="cal-seg" style="width:${Math.round(D.ea/D.consumed*100)}%;background:#16a34a"></div>
              </div>
              <div class="cal-legend">
                <div class="cal-leg"><div class="cal-dot" style="background:#e0e0e0"></div>BMR ${D.bmr} kcal</div>
                <div class="cal-leg"><div class="cal-dot" style="background:#fbbf24"></div>Exercice ${D.exercise} kcal</div>
                <div class="cal-leg"><div class="cal-dot" style="background:#16a34a"></div>EA +${D.ea} kcal</div>
              </div>
            </div>

            <div class="card">
              <div class="card-title">Macronutriments</div>
              ${D.macros.map(macroBar).join('')}
            </div>

          </div>
          <div class="card">
            <div class="card-title">Repas du jour</div>
            ${D.meals.map(m => `
            <div class="meal-item">
              <div class="meal-time">${m.time}</div>
              <div class="meal-name">${m.name}</div>
              <div style="text-align:right">
                <div class="meal-kcal">${m.kcal} kcal</div>
                <div class="meal-macro">${m.macro}</div>
              </div>
            </div>`).join('')}
          </div>
        </div>
      </div>

      <!-- ══ READINESS ══ -->
      <div class="tab-content" id="tab-readiness">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
          <div class="card">
            <div class="card-title">Score global</div>
            <div class="read-hero">
              <svg class="read-score-ring" viewBox="0 0 90 90">
                <circle cx="45" cy="45" r="38" fill="none" stroke="#f0f0f0" stroke-width="10"/>
                <circle cx="45" cy="45" r="38" fill="none" stroke="#16a34a" stroke-width="10"
                  stroke-dasharray="${(D.readiness/100 * 2*Math.PI*38).toFixed(1)} ${(2*Math.PI*38).toFixed(1)}"
                  stroke-dashoffset="0" transform="rotate(-90 45 45)" stroke-linecap="round"/>
                <text x="45" y="49" text-anchor="middle" font-family="DM Mono,monospace" font-size="16" font-weight="500" fill="#09090b">${D.readiness}</text>
              </svg>
              <div>
                <div class="read-score-num">${D.readiness}</div>
                <div class="read-score-label">Récupération optimale</div>
              </div>
            </div>
            <hr class="divider">
            <div class="card-title">Composantes</div>
            ${D.readinessDim.map(radBar).join('')}
          </div>
          <div style="display:flex;flex-direction:column;gap:14px">
            <div class="card">
              <div class="card-title">Métriques clés</div>
              <div class="read-grid">
                <div class="read-cell"><div class="read-cell-label">HRV</div><div class="read-cell-val" style="color:#16a34a">${D.hrv} ms</div></div>
                <div class="read-cell"><div class="read-cell-label">FC repos</div><div class="read-cell-val">${D.restHR} bpm</div></div>
                <div class="read-cell"><div class="read-cell-label">Sommeil</div><div class="read-cell-val" style="color:#3b82f6">${D.sleep.total}</div></div>
                <div class="read-cell"><div class="read-cell-label">Temp. corp.</div><div class="read-cell-val">${D.bodyTemp}</div></div>
              </div>
            </div>
            <div class="card">
              <div class="card-title">Recommandation</div>
              <div style="font-size:13px;color:#3f3f46;line-height:1.6">
                Votre corps est bien reposé. C'est une bonne journée pour une séance à haute intensité. La charge d'entraînement planifiée (Tempo progressif, 55 min) est bien adaptée à votre état de récupération actuel.
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ SOMMEIL ══ -->
      <div class="tab-content" id="tab-sommeil">
        <div class="sleep-hero">
          <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <div class="card-title" style="margin-bottom:0">Nuit du 9 au 10 avril</div>
              <div style="font-size:11px;color:#71717a">${D.sleep.bed} → ${D.sleep.wake}</div>
            </div>
            <div class="sleep-timeline">
              <div class="sleep-seg" style="width:5%;background:#f0f0f0"></div>
              <div class="sleep-seg" style="width:28%;background:#6366f1;opacity:0.7"></div>
              <div class="sleep-seg" style="width:14%;background:#1d4ed8"></div>
              <div class="sleep-seg" style="width:22%;background:#6366f1;opacity:0.7"></div>
              <div class="sleep-seg" style="width:10%;background:#1d4ed8"></div>
              <div class="sleep-seg" style="width:21%;background:#6366f1;opacity:0.7"></div>
            </div>
            <div style="display:flex;gap:14px;margin-bottom:14px">
              <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#71717a"><div style="width:9px;height:9px;border-radius:2px;background:#1d4ed8"></div>Profond</div>
              <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#71717a"><div style="width:9px;height:9px;border-radius:2px;background:#6366f1;opacity:0.8"></div>REM</div>
              <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#71717a"><div style="width:9px;height:9px;border-radius:2px;background:#f0f0f0;border:1px solid #e4e4e7"></div>Léger / éveil</div>
            </div>
            <div class="sleep-grid">
              <div class="sleep-cell"><div class="sleep-cell-label">Durée totale</div><div class="sleep-cell-val">${D.sleep.total}</div></div>
              <div class="sleep-cell"><div class="sleep-cell-label">Profond</div><div class="sleep-cell-val" style="color:#1d4ed8">${D.sleep.deep}</div></div>
              <div class="sleep-cell"><div class="sleep-cell-label">REM</div><div class="sleep-cell-val" style="color:#6366f1">${D.sleep.rem}</div></div>
              <div class="sleep-cell"><div class="sleep-cell-label">Léger</div><div class="sleep-cell-val">${D.sleep.light}</div></div>
              <div class="sleep-cell"><div class="sleep-cell-label">Score</div><div class="sleep-cell-val">${D.sleep.score}/100</div></div>
              <div class="sleep-cell"><div class="sleep-cell-label">Coucher</div><div class="sleep-cell-val">${D.sleep.bed}</div></div>
            </div>
          </div>
          <div class="card">
            <div class="card-title">Analyse</div>
            <div style="font-size:13px;color:#3f3f46;line-height:1.65;margin-bottom:16px">
              Bonne nuit de sommeil avec une durée suffisante. Le sommeil profond (1h 45) est légèrement en dessous de l'objectif de 2h mais reste dans la zone acceptable. Le REM (1h 52) est optimal pour la consolidation mémoire et la récupération cognitive.
            </div>
            <hr class="divider">
            <div class="card-title">Objectifs</div>
            <div style="display:flex;flex-direction:column;gap:8px">
              <div style="display:flex;justify-content:space-between;font-size:12px"><span style="color:#71717a">Durée cible</span><span style="font-family:'DM Mono',monospace">8h 00</span></div>
              <div style="display:flex;justify-content:space-between;font-size:12px"><span style="color:#71717a">Profond cible</span><span style="font-family:'DM Mono',monospace">2h 00</span></div>
              <div style="display:flex;justify-content:space-between;font-size:12px"><span style="color:#71717a">Coucher cible</span><span style="font-family:'DM Mono',monospace">22h 00</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ HRV ══ -->
      <div class="tab-content" id="tab-hrv">
        <div class="hrv-hero">
          <div class="hrv-card" style="border-top:3px solid #8b5cf6">
            <div class="hrv-card-label">HRV · RMSSD</div>
            <div class="hrv-card-val" style="color:#8b5cf6">${D.hrv}</div>
            <div class="hrv-card-unit">ms</div>
            <div class="hrv-card-trend">↑ +4 ms vs moyenne 30j</div>
          </div>
          <div class="hrv-card" style="border-top:3px solid #16a34a">
            <div class="hrv-card-label">FC au repos</div>
            <div class="hrv-card-val" style="color:#16a34a">${D.restHR}</div>
            <div class="hrv-card-unit">bpm</div>
            <div class="hrv-card-trend">↓ −2 bpm vs hier</div>
          </div>
          <div class="hrv-card" style="border-top:3px solid #f59e0b">
            <div class="hrv-card-label">Température corp.</div>
            <div class="hrv-card-val" style="color:#f59e0b;font-size:22px">${D.bodyTemp}</div>
            <div class="hrv-card-unit">variation</div>
            <div class="hrv-card-trend" style="color:#71717a">Zone normale</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
          <div class="card">
            <div class="card-title">Interprétation HRV</div>
            <div style="font-size:13px;color:#3f3f46;line-height:1.65">
              Votre HRV de 68 ms est au-dessus de votre moyenne sur 30 jours (64 ms). Cela indique un système nerveux autonome bien équilibré et une bonne tolérance au stress d'entraînement. Une valeur en hausse avant un entraînement intense est un bon signal.
            </div>
          </div>
          <div class="card">
            <div class="card-title">Tendances 7 jours</div>
            <div style="display:flex;flex-direction:column;gap:8px">
              ${[68,72,61,65,70,63,68].map((v,i) => {
                const days=['L','M','M','J','V','S','D'];
                const isToday = i===3;
                return `<div style="display:flex;align-items:center;gap:10px">
                  <span style="font-size:11px;color:#a1a1aa;width:14px">${days[i]}</span>
                  <div style="flex:1;height:6px;background:#f4f4f5;border-radius:3px;overflow:hidden">
                    <div style="height:100%;width:${Math.round(v/90*100)}%;background:${isToday?'#8b5cf6':'#d8b4fe'};border-radius:3px"></div>
                  </div>
                  <span style="font-family:'DM Mono',monospace;font-size:11px;color:${isToday?'#8b5cf6':'#3f3f46'};width:34px;text-align:right">${v} ms</span>
                </div>`;
              }).join('')}
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 3/12 — /energy · 1280×800px
</div>

<script>
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.textContent.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'') === name));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + name));
}
// Fix: match button text to tab name
document.querySelectorAll('.tab-btn').forEach(b => {
  const map = {'résumé':'resume','nutrition':'nutrition','readiness':'readiness','sommeil':'sommeil','hrv':'hrv'};
  b.onclick = () => switchTab(map[b.textContent.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'')]);
});
</script>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/energy-v2.html', html);
console.log('done');
