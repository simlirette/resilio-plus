const fs = require('fs');

const settings = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');
const runner   = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');

const chevL = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9 3L5 7L9 11" stroke="#52525b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const chevR = `<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3L9 7L5 11" stroke="#52525b" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// Mock data — Jeudi 10 avril, jour d'entraînement (haute glucides)
const data = {
  dayType: 'Haute glucides',
  dayTypeColor: '#16a34a',
  dayTypeBg: '#f0fdf4',
  dayTypeBorder: '#bbf7d0',

  // Calories
  bmr: 2200,
  exerciseBurn: 450,
  totalBurn: 2650,
  consumed: 2840,
  ea: +245,  // Energy Availability (consumed - totalBurn + adjustment)

  // Macros: [label, target, actual, unit, color]
  macros: [
    { label: 'Glucides', target: 320, actual: 280, unit: 'g', color: '#3b82f6' },
    { label: 'Protéines', target: 160, actual: 145, unit: 'g', color: '#f59e0b' },
    { label: 'Lipides',   target: 70,  actual: 65,  unit: 'g', color: '#8b5cf6' },
  ],

  // Meals
  meals: [
    { time: '7h15', name: 'Déjeuner pré-séance', kcal: 520, carbs: 78, prot: 28, fat: 12 },
    { time: '10h30', name: 'Collation récup.', kcal: 380, carbs: 52, prot: 24, fat: 8 },
    { time: '13h00', name: 'Dîner', kcal: 780, carbs: 95, prot: 48, fat: 22 },
    { time: '16h30', name: 'Collation après-midi', kcal: 290, carbs: 38, prot: 18, fat: 9 },
    { time: '19h30', name: 'Souper', kcal: 870, carbs: 117, prot: 52, fat: 24 },
  ],

  // Sleep
  sleepTotal: '7h 42',
  sleepScore: 82,
  sleepDeep: '1h 45',
  sleepREM: '1h 52',
  sleepLight: '4h 05',
  bedtime: '22h 30',
  wakeup: '6h 12',

  // Recovery
  hrv: 68,
  readiness: 84,
  restingHR: 48,
  bodyTemp: '+0.1°C',

  // Weekly EA trend (Mon–Sun)
  weekEA: [+245, +180, -60, null, +310, -120, -200],
  weekLabels: ['L', 'M', 'M', 'J', 'V', 'S', 'D'],
};

function macroBar(m) {
  const pct = Math.min(100, Math.round(m.actual / m.target * 100));
  return `
  <div class="macro-row">
    <div class="macro-label-row">
      <span class="macro-name">${m.label}</span>
      <span class="macro-vals"><span style="color:${m.color};font-weight:600">${m.actual}${m.unit}</span> <span class="macro-target">/ ${m.target}${m.unit}</span></span>
    </div>
    <div class="macro-track">
      <div class="macro-fill" style="width:${pct}%;background:${m.color}"></div>
    </div>
  </div>`;
}

function weekBar(ea, label, isToday) {
  const maxAbs = 350;
  const barH = Math.round(Math.abs(ea || 0) / maxAbs * 36);
  const color = ea === null ? '#e4e4e7' : ea >= 0 ? '#16a34a' : '#f87171';
  const todayCls = isToday ? ' today' : '';
  return `
  <div class="week-bar-col${todayCls}">
    <div class="week-bar-wrap">
      ${ea !== null ? `<div class="week-bar" style="height:${barH}px;background:${color}"></div>` : `<div class="week-bar rest-bar"></div>`}
    </div>
    <div class="week-bar-label">${label}</div>
    ${ea !== null ? `<div class="week-bar-val" style="color:${color}">${ea > 0 ? '+' : ''}${ea}</div>` : `<div class="week-bar-val" style="color:#a1a1aa">—</div>`}
  </div>`;
}

const SIDEBAR = `
<div class="sidebar">
  <div class="sidebar-logo">Resilio<span class="logo-plus">+</span></div>
  <div class="nav-section">
    <div class="nav-label">Principal</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><ellipse cx="10" cy="10" rx="8" ry="5" stroke="#52525b" stroke-width="1.5" fill="none"/><circle cx="10" cy="10" r="2.5" fill="#52525b"/><circle cx="10" cy="10" r="1" fill="white"/></svg></div>Aperçu</div>
    <div class="nav-item"><div class="nav-icon"><svg viewBox="0 0 20 20" fill="none"><rect x="3" y="4" width="14" height="12" rx="1" stroke="#52525b" stroke-width="1.4" fill="none"/><line x1="6" y1="8" x2="14" y2="8" stroke="#52525b" stroke-width="1"/><line x1="6" y1="11" x2="14" y2="11" stroke="#52525b" stroke-width="1"/><line x1="6" y1="14" x2="10" y2="14" stroke="#52525b" stroke-width="1"/></svg></div>Plan</div>
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

/* SIDEBAR */
.sidebar { width:260px; min-width:260px; background:#fff; border-right:1px solid #e4e4e7; display:flex; flex-direction:column; padding:32px 0 24px; flex-shrink:0; }
.sidebar-logo { font-family:'Playfair Display',serif; font-size:24px; color:#09090b; padding:0 28px 28px; border-bottom:1px solid #e4e4e7; }
.logo-plus { color:#16a34a; }
.nav-section { padding:20px 16px 4px; }
.nav-label { font-size:10px; text-transform:uppercase; letter-spacing:0.12em; color:#a1a1aa; padding:0 8px; margin-bottom:4px; }
.nav-item { display:flex; align-items:center; gap:10px; padding:11px 12px; border-radius:8px; font-size:14px; color:#52525b; margin-bottom:2px; border-left:2px solid transparent; }
.nav-item.active { background:#f4f4f5; color:#09090b; border-left:2px solid #18181b; font-weight:500; }
.nav-icon { width:22px; height:22px; display:flex; align-items:center; justify-content:center; flex-shrink:0; opacity:0.45; }
.nav-item.active .nav-icon { opacity:1; }
.nav-icon svg, .nav-icon img { width:18px; height:18px; }
.sidebar-footer { margin-top:auto; padding:16px 20px 0; border-top:1px solid #e4e4e7; display:flex; align-items:center; gap:12px; }
.avatar { width:36px; height:36px; border-radius:50%; background:#18181b; color:white; font-size:13px; font-weight:600; display:flex; align-items:center; justify-content:center; }
.avatar-name { font-size:13px; font-weight:500; color:#09090b; }
.avatar-status { font-size:11px; color:#16a34a; display:flex; align-items:center; gap:4px; }
.avatar-status::before { content:''; width:6px; height:6px; background:#16a34a; border-radius:50%; display:inline-block; }

/* MAIN */
.main { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }

/* Page header */
.page-header { padding:20px 28px 16px; border-bottom:1px solid #e4e4e7; flex-shrink:0; display:flex; align-items:center; justify-content:space-between; }
.page-title { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; letter-spacing:-0.02em; }
.page-date-nav { display:flex; align-items:center; gap:10px; }
.nav-arrow { width:28px; height:28px; border-radius:7px; border:1px solid #e4e4e7; background:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0; }
.nav-arrow:hover { background:#f4f4f5; }
.nav-arrow svg { display:block; }
.page-date { font-size:13px; font-weight:500; color:#09090b; }

/* Day type badge */
.day-type-badge {
  display:inline-flex; align-items:center; gap:6px;
  padding:4px 10px; border-radius:20px;
  background:${data.dayTypeBg}; border:1px solid ${data.dayTypeBorder};
  font-size:11px; font-weight:500; color:${data.dayTypeColor};
}
.day-type-dot { width:6px; height:6px; border-radius:50%; background:${data.dayTypeColor}; }

/* SCROLL AREA */
.content-scroll { flex:1; overflow-y:auto; padding:20px 28px 28px; }
.content-scroll::-webkit-scrollbar { width:4px; }
.content-scroll::-webkit-scrollbar-thumb { background:#e4e4e7; border-radius:2px; }

/* GRID LAYOUT */
.grid-top { display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:12px; margin-bottom:16px; }
.grid-mid { display:grid; grid-template-columns:1.3fr 1fr; gap:16px; margin-bottom:16px; }
.grid-bot { display:grid; grid-template-columns:1fr; gap:16px; }

/* CARD BASE */
.card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:16px; }
.card-title { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:10px; }

/* STAT CARD (top row) */
.stat-card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:16px 18px; }
.stat-label { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:6px; }
.stat-value { font-family:'DM Mono',monospace; font-size:22px; font-weight:500; color:#09090b; line-height:1; }
.stat-value.green  { color:#16a34a; }
.stat-value.blue   { color:#3b82f6; }
.stat-value.purple { color:#8b5cf6; }
.stat-sub { font-size:11px; color:#71717a; margin-top:4px; }

/* EA card special */
.ea-card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:16px 18px; position:relative; overflow:hidden; }
.ea-card::after { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:#16a34a; border-radius:12px 12px 0 0; }
.ea-pill { display:inline-flex; align-items:center; gap:5px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; padding:2px 8px; font-size:10px; font-weight:600; color:#16a34a; margin-top:4px; }

/* MACRO SECTION */
.macro-row { margin-bottom:10px; }
.macro-label-row { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px; }
.macro-name { font-size:12px; font-weight:500; color:#3f3f46; }
.macro-vals { font-size:12px; }
.macro-target { color:#a1a1aa; }
.macro-track { height:6px; background:#f4f4f5; border-radius:3px; overflow:hidden; }
.macro-fill { height:100%; border-radius:3px; transition:width 0.3s; }

/* CALORIES BREAKDOWN */
.cal-breakdown { display:flex; gap:0; margin-top:12px; border-radius:8px; overflow:hidden; height:10px; }
.cal-seg { height:100%; }
.cal-legend { display:flex; flex-wrap:wrap; gap:10px; margin-top:8px; }
.cal-leg-item { display:flex; align-items:center; gap:5px; font-size:10px; color:#71717a; }
.cal-leg-dot { width:8px; height:8px; border-radius:2px; flex-shrink:0; }

/* MEALS LIST */
.meal-item { display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f4f4f5; }
.meal-item:last-child { border-bottom:none; }
.meal-time { font-family:'DM Mono',monospace; font-size:10px; color:#a1a1aa; width:36px; flex-shrink:0; }
.meal-name { font-size:12px; color:#3f3f46; flex:1; padding:0 8px; }
.meal-kcal { font-family:'DM Mono',monospace; font-size:12px; color:#09090b; font-weight:500; }
.meal-macros { font-size:10px; color:#a1a1aa; text-align:right; }

/* SLEEP SECTION */
.sleep-timeline { display:flex; height:10px; border-radius:5px; overflow:hidden; margin:10px 0; gap:1px; }
.sleep-seg { height:100%; border-radius:2px; }
.sleep-stats-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.sleep-stat { background:#f9f9f9; border-radius:8px; padding:8px 10px; }
.sleep-stat-label { font-size:10px; color:#a1a1aa; margin-bottom:2px; }
.sleep-stat-val { font-family:'DM Mono',monospace; font-size:13px; font-weight:500; color:#09090b; }

/* RECOVERY METRICS */
.rec-row { display:flex; gap:10px; }
.rec-item { flex:1; background:#f9f9f9; border-radius:8px; padding:10px 12px; text-align:center; }
.rec-item-label { font-size:10px; color:#a1a1aa; margin-bottom:4px; }
.rec-item-val { font-family:'DM Mono',monospace; font-size:16px; font-weight:500; color:#09090b; }
.rec-item-val.green { color:#16a34a; }

/* WEEKLY EA CHART */
.week-ea-chart { display:flex; align-items:flex-end; gap:6px; height:80px; padding-bottom:20px; position:relative; }
.week-ea-chart::after { content:''; position:absolute; bottom:20px; left:0; right:0; height:1px; background:#e4e4e7; }
.week-bar-col { flex:1; display:flex; flex-direction:column; align-items:center; gap:3px; }
.week-bar-col.today .week-bar { outline:1.5px solid #16a34a; outline-offset:1px; border-radius:3px; }
.week-bar-wrap { flex:1; display:flex; align-items:flex-end; justify-content:center; width:100%; }
.week-bar { width:100%; max-width:32px; border-radius:3px 3px 0 0; }
.rest-bar { width:100%; max-width:32px; height:3px; background:#e4e4e7; border-radius:2px; margin-bottom:0; }
.week-bar-label { font-size:10px; color:#a1a1aa; }
.week-bar-val { font-family:'DM Mono',monospace; font-size:9px; color:#71717a; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}
  <div class="main">

    <div class="page-header">
      <div style="display:flex;align-items:center;gap:14px">
        <div class="page-title">Énergie</div>
        <div class="day-type-badge"><div class="day-type-dot"></div>${data.dayType}</div>
      </div>
      <div class="page-date-nav">
        <button class="nav-arrow">${chevL}</button>
        <div class="page-date">Jeudi 10 avril 2026</div>
        <button class="nav-arrow">${chevR}</button>
      </div>
    </div>

    <div class="content-scroll">

      <!-- TOP ROW: 4 key metrics -->
      <div class="grid-top">

        <!-- EA -->
        <div class="ea-card">
          <div class="stat-label">Énergie disponible</div>
          <div class="stat-value green">+${data.ea} kcal</div>
          <div class="ea-pill">↑ Zone optimale</div>
        </div>

        <!-- Readiness -->
        <div class="stat-card">
          <div class="stat-label">Readiness</div>
          <div class="stat-value">${data.readiness}<span style="font-size:13px;color:#a1a1aa"> /100</span></div>
          <div class="stat-sub">Récupération optimale</div>
        </div>

        <!-- Sleep -->
        <div class="stat-card">
          <div class="stat-label">Sommeil</div>
          <div class="stat-value blue">${data.sleepTotal}</div>
          <div class="stat-sub">Score ${data.sleepScore}/100</div>
        </div>

        <!-- HRV -->
        <div class="stat-card">
          <div class="stat-label">HRV (RMSSD)</div>
          <div class="stat-value purple">${data.hrv} <span style="font-size:13px">ms</span></div>
          <div class="stat-sub">FC repos ${data.restingHR} bpm</div>
        </div>

      </div>

      <!-- MID ROW: Nutrition left, Sleep right -->
      <div class="grid-mid">

        <!-- LEFT: Nutrition -->
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div class="card-title" style="margin-bottom:0">Nutrition du jour</div>
            <div style="font-size:11px;color:#71717a">${data.consumed} / ${data.totalBurn} kcal</div>
          </div>

          <!-- Calorie bar -->
          <div class="cal-breakdown">
            <div class="cal-seg" style="width:${Math.round(data.bmr/data.consumed*100)}%;background:#e4e4e7"></div>
            <div class="cal-seg" style="width:${Math.round(data.exerciseBurn/data.consumed*100)}%;background:#fbbf24"></div>
            <div class="cal-seg" style="width:${Math.round(data.ea/data.consumed*100)}%;background:#16a34a"></div>
          </div>
          <div class="cal-legend">
            <div class="cal-leg-item"><div class="cal-leg-dot" style="background:#e4e4e7"></div>Métabolisme de base ${data.bmr} kcal</div>
            <div class="cal-leg-item"><div class="cal-leg-dot" style="background:#fbbf24"></div>Exercice ${data.exerciseBurn} kcal</div>
            <div class="cal-leg-item"><div class="cal-leg-dot" style="background:#16a34a"></div>EA +${data.ea} kcal</div>
          </div>

          <div style="border-top:1px solid #f4f4f5;margin:12px 0 10px"></div>
          <div class="card-title">Macronutriments</div>
          ${data.macros.map(macroBar).join('')}

          <div style="border-top:1px solid #f4f4f5;margin:12px 0 10px"></div>
          <div class="card-title">Repas</div>
          ${data.meals.map(m => `
          <div class="meal-item">
            <div class="meal-time">${m.time}</div>
            <div class="meal-name">${m.name}</div>
            <div>
              <div class="meal-kcal">${m.kcal} kcal</div>
              <div class="meal-macros">G${m.carbs} · P${m.prot} · L${m.fat}</div>
            </div>
          </div>`).join('')}
        </div>

        <!-- RIGHT: Sleep + Recovery -->
        <div style="display:flex;flex-direction:column;gap:14px">

          <!-- Sleep card -->
          <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
              <div class="card-title" style="margin-bottom:0">Sommeil</div>
              <div style="font-size:11px;color:#71717a">${data.bedtime} → ${data.wakeup}</div>
            </div>

            <!-- Sleep timeline -->
            <div class="sleep-timeline">
              <div class="sleep-seg" style="width:22%;background:#e4e4e7;opacity:0.5"></div>
              <div class="sleep-seg" style="width:24%;background:#6366f1"></div>
              <div class="sleep-seg" style="width:12%;background:#1d4ed8"></div>
              <div class="sleep-seg" style="width:20%;background:#6366f1"></div>
              <div class="sleep-seg" style="width:8%;background:#1d4ed8"></div>
              <div class="sleep-seg" style="width:14%;background:#6366f1"></div>
            </div>
            <div style="display:flex;gap:12px;margin-bottom:12px">
              <div style="display:flex;align-items:center;gap:4px;font-size:10px;color:#71717a"><div style="width:8px;height:8px;border-radius:2px;background:#1d4ed8"></div>Profond ${data.sleepDeep}</div>
              <div style="display:flex;align-items:center;gap:4px;font-size:10px;color:#71717a"><div style="width:8px;height:8px;border-radius:2px;background:#6366f1"></div>REM ${data.sleepREM}</div>
              <div style="display:flex;align-items:center;gap:4px;font-size:10px;color:#71717a"><div style="width:8px;height:8px;border-radius:2px;background:#e4e4e7"></div>Léger ${data.sleepLight}</div>
            </div>

            <div class="sleep-stats-grid">
              <div class="sleep-stat">
                <div class="sleep-stat-label">Durée totale</div>
                <div class="sleep-stat-val">${data.sleepTotal}</div>
              </div>
              <div class="sleep-stat">
                <div class="sleep-stat-label">Score qualité</div>
                <div class="sleep-stat-val">${data.sleepScore}/100</div>
              </div>
            </div>
          </div>

          <!-- Recovery card -->
          <div class="card">
            <div class="card-title">Récupération</div>
            <div class="rec-row">
              <div class="rec-item">
                <div class="rec-item-label">HRV</div>
                <div class="rec-item-val green">${data.hrv} ms</div>
              </div>
              <div class="rec-item">
                <div class="rec-item-label">FC repos</div>
                <div class="rec-item-val">${data.restingHR} bpm</div>
              </div>
              <div class="rec-item">
                <div class="rec-item-label">Temp. corp.</div>
                <div class="rec-item-val">${data.bodyTemp}</div>
              </div>
            </div>
          </div>

          <!-- Weekly EA -->
          <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
              <div class="card-title" style="margin-bottom:0">Énergie disponible · semaine</div>
              <div style="font-size:10px;color:#a1a1aa">kcal / jour</div>
            </div>
            <div class="week-ea-chart">
              ${data.weekEA.map((ea, i) => weekBar(ea, data.weekLabels[i], i === 3)).join('')}
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
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/energy.html', html);
console.log('done');
