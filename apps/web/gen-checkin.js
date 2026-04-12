const fs = require('fs');

const settings = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/settings.png').toString('base64');
const runner   = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/runner.png').toString('base64');
const biker    = 'data:image/png;base64,' + fs.readFileSync('C:/Users/simon/resilio-plus/frontend/public/icons/biker.png').toString('base64');

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
    <div class="nav-item"><div class="nav-icon" style="opacity:0.45"><img src="${settings}" style="width:18px;height:18px;object-fit:contain"></div>Paramètres</div>
  </div>
  <div class="sidebar-footer">
    <div class="avatar">S</div>
    <div><div class="avatar-name">Simon</div><div class="avatar-status">Récupération optimale</div></div>
  </div>
</div>`;

// Slider component
function slider(id, label, leftLabel, rightLabel, value, color='#18181b') {
  const pct = ((value - 1) / 4) * 100;
  return `<div class="slider-group">
    <div class="slider-header">
      <span class="slider-label">${label}</span>
      <span class="slider-val" style="color:${color}">${value}/5</span>
    </div>
    <div class="slider-track">
      <div class="slider-fill" style="width:${pct}%;background:${color}"></div>
      <div class="slider-thumb" style="left:${pct}%;background:${color}"></div>
    </div>
    <div class="slider-ends">
      <span>${leftLabel}</span>
      <span>${rightLabel}</span>
    </div>
  </div>`;
}

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

.main { flex:1; display:flex; flex-direction:column; overflow:hidden; }

/* Header */
.page-header { padding:20px 32px 18px; border-bottom:1px solid #e4e4e7; flex-shrink:0; display:flex; align-items:flex-end; justify-content:space-between; }
.page-title { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; letter-spacing:-0.02em; }
.page-sub { font-size:12px; color:#a1a1aa; margin-top:3px; }
.step-indicator { display:flex; align-items:center; gap:6px; }
.step-dot { width:7px; height:7px; border-radius:50%; background:#e4e4e7; }
.step-dot.done { background:#18181b; }
.step-dot.active { background:#18181b; width:20px; border-radius:4px; }

/* Scroll */
.content-scroll { flex:1; overflow-y:auto; display:flex; }
.content-scroll::-webkit-scrollbar { width:4px; }
.content-scroll::-webkit-scrollbar-thumb { background:#e4e4e7; border-radius:2px; }

/* Two-panel layout */
.left-panel { width:420px; min-width:420px; padding:24px 28px; border-right:1px solid #e4e4e7; overflow-y:auto; display:flex; flex-direction:column; gap:20px; }
.right-panel { flex:1; padding:24px 28px; overflow-y:auto; display:flex; flex-direction:column; gap:18px; }

/* Section title */
.section-title { font-size:11px; text-transform:uppercase; letter-spacing:0.1em; color:#a1a1aa; margin-bottom:12px; }

/* Yesterday's sessions confirm */
.session-confirm { background:#fff; border:1px solid #e4e4e7; border-radius:10px; overflow:hidden; }
.sc-header { display:flex; align-items:center; justify-content:space-between; padding:12px 14px; border-bottom:1px solid #f4f4f5; }
.sc-sport { display:flex; align-items:center; gap:10px; }
.sc-icon { width:32px; height:32px; border-radius:8px; background:#e4e4e7; display:flex; align-items:center; justify-content:center; }
.sc-icon img { width:20px; height:20px; object-fit:contain; }
.sc-name { font-size:13px; font-weight:500; color:#09090b; }
.sc-meta { font-size:11px; color:#71717a; }
.sc-toggle { display:flex; gap:0; border:1px solid #e4e4e7; border-radius:7px; overflow:hidden; }
.sc-btn { font-size:11px; font-weight:500; padding:5px 11px; border:none; background:#fff; cursor:pointer; color:#71717a; }
.sc-btn.yes { background:#f0fdf4; color:#16a34a; }
.sc-btn.no  { background:#fff5f5; color:#ef4444; }
.sc-rpe { padding:10px 14px; display:flex; align-items:center; justify-content:space-between; }
.rpe-label { font-size:11px; color:#71717a; }
.rpe-pills { display:flex; gap:4px; }
.rpe-pill { width:24px; height:24px; border-radius:6px; border:1px solid #e4e4e7; background:#fff; font-size:10px; font-weight:600; display:flex; align-items:center; justify-content:center; cursor:pointer; color:#71717a; }
.rpe-pill.selected { background:#18181b; color:#fff; border-color:#18181b; }

/* Sliders */
.slider-group { margin-bottom:6px; }
.slider-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.slider-label { font-size:13px; font-weight:500; color:#3f3f46; }
.slider-val { font-family:'DM Mono',monospace; font-size:12px; font-weight:600; }
.slider-track { position:relative; height:5px; background:#f0f0f0; border-radius:3px; margin:0 6px; }
.slider-fill { position:absolute; top:0; left:0; height:100%; border-radius:3px; }
.slider-thumb { position:absolute; top:50%; transform:translate(-50%,-50%); width:14px; height:14px; border-radius:50%; border:2px solid #fff; box-shadow:0 1px 4px rgba(0,0,0,0.2); }
.slider-ends { display:flex; justify-content:space-between; font-size:10px; color:#a1a1aa; margin-top:5px; }

/* Notes textarea */
.notes-area { width:100%; border:1px solid #e4e4e7; border-radius:10px; padding:12px 14px; font-family:'DM Sans',system-ui; font-size:13px; color:#3f3f46; resize:none; height:80px; outline:none; background:#fff; }
.notes-area:focus { border-color:#a1a1aa; }
.notes-area::placeholder { color:#c4c4c4; }

/* Submit button */
.submit-btn { background:#18181b; color:#fff; border:none; border-radius:10px; padding:13px 0; width:100%; font-family:'DM Sans',system-ui; font-size:14px; font-weight:500; cursor:pointer; letter-spacing:0.01em; }
.submit-btn:hover { background:#3f3f46; }

/* Right panel: AI insight card */
.insight-card { background:#fff; border:1px solid #e4e4e7; border-radius:12px; padding:16px 18px; }
.insight-header { display:flex; align-items:center; gap:8px; margin-bottom:10px; }
.insight-icon { width:28px; height:28px; border-radius:7px; background:#f4f4f5; display:flex; align-items:center; justify-content:center; font-size:14px; }
.insight-title { font-size:12px; font-weight:500; color:#09090b; }
.insight-sub { font-size:10px; color:#a1a1aa; }
.insight-body { font-size:12px; color:#52525b; line-height:1.65; }

/* Trend mini chart */
.trend-row { display:flex; align-items:flex-end; gap:4px; height:40px; margin:10px 0 4px; }
.trend-bar { flex:1; border-radius:2px 2px 0 0; min-height:3px; }
.trend-labels { display:flex; gap:4px; }
.trend-label { flex:1; text-align:center; font-size:9px; color:#a1a1aa; }

/* Muscle map */
.muscle-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; }
.muscle-chip { border-radius:7px; padding:6px 8px; text-align:center; }
.muscle-chip-label { font-size:10px; font-weight:500; }
.muscle-chip-val { font-size:9px; margin-top:1px; }

/* Divider */
.divider { border:none; border-top:1px solid #f4f4f5; }
</style>
</head>
<body>
<div class="frame">
  ${SIDEBAR}
  <div class="main">

    <div class="page-header">
      <div>
        <div class="page-title">Check-in du jour</div>
        <div class="page-sub">Jeudi 10 avril 2026 · Prend 2 minutes</div>
      </div>
      <div class="step-indicator">
        <div class="step-dot done"></div>
        <div class="step-dot active"></div>
        <div class="step-dot"></div>
        <div class="step-dot"></div>
      </div>
    </div>

    <div class="content-scroll">

      <!-- LEFT PANEL: Form -->
      <div class="left-panel">

        <!-- Confirm yesterday's sessions -->
        <div>
          <div class="section-title">Séances d'hier — Confirmer</div>
          <div style="display:flex;flex-direction:column;gap:8px">

            <div class="session-confirm">
              <div class="sc-header">
                <div class="sc-sport">
                  <div class="sc-icon"><img src="${runner}" alt=""></div>
                  <div>
                    <div class="sc-name">Sortie facile</div>
                    <div class="sc-meta">Mer 09 · 45 min · Z1–Z2</div>
                  </div>
                </div>
                <div class="sc-toggle">
                  <button class="sc-btn yes">✓ Fait</button>
                  <button class="sc-btn">Modif.</button>
                  <button class="sc-btn">Raté</button>
                </div>
              </div>
              <div class="sc-rpe">
                <span class="rpe-label">Effort perçu (RPE)</span>
                <div class="rpe-pills">
                  ${[1,2,3,4,5,6,7,8,9,10].map(n => `<div class="rpe-pill${n===4?' selected':''}">${n}</div>`).join('')}
                </div>
              </div>
            </div>

            <div class="session-confirm">
              <div class="sc-header">
                <div class="sc-sport">
                  <div class="sc-icon"><img src="${biker}" alt=""></div>
                  <div>
                    <div class="sc-name">Zone 2 vélo</div>
                    <div class="sc-meta">Mer 09 · 1h 15 · Zone 2</div>
                  </div>
                </div>
                <div class="sc-toggle">
                  <button class="sc-btn yes">✓ Fait</button>
                  <button class="sc-btn">Modif.</button>
                  <button class="sc-btn">Raté</button>
                </div>
              </div>
              <div class="sc-rpe">
                <span class="rpe-label">Effort perçu (RPE)</span>
                <div class="rpe-pills">
                  ${[1,2,3,4,5,6,7,8,9,10].map(n => `<div class="rpe-pill${n===5?' selected':''}">${n}</div>`).join('')}
                </div>
              </div>
            </div>

          </div>
        </div>

        <hr class="divider">

        <!-- Subjective state sliders -->
        <div>
          <div class="section-title">Comment tu te sens aujourd'hui ?</div>
          <div style="display:flex;flex-direction:column;gap:14px">
            ${slider('fatigue',    'Fatigue générale',     'Épuisé',    'Frais',    4, '#16a34a')}
            ${slider('motivation', 'Motivation',           'Nulle',     'Maximale', 4, '#3b82f6')}
            ${slider('soreness',   'Courbatures',          'Intenses',  'Aucune',   3, '#f59e0b')}
            ${slider('stress',     'Stress / Vie quotid.', 'Élevé',     'Faible',   4, '#8b5cf6')}
          </div>
        </div>

        <hr class="divider">

        <!-- Notes -->
        <div>
          <div class="section-title">Note libre (optionnel)</div>
          <textarea class="notes-area" placeholder="Ex : jambes lourdes au réveil, bonne énergie après le café..."></textarea>
        </div>

        <button class="submit-btn">Soumettre le check-in →</button>

      </div>

      <!-- RIGHT PANEL: AI insights -->
      <div class="right-panel">

        <!-- AI summary -->
        <div class="insight-card">
          <div class="insight-header">
            <div class="insight-icon">✦</div>
            <div>
              <div class="insight-title">Analyse du coach IA</div>
              <div class="insight-sub">Basé sur tes données des 7 derniers jours</div>
            </div>
          </div>
          <div class="insight-body">
            Ton HRV de 68 ms et ta FC repos de 48 bpm indiquent une bonne récupération. Tes scores subjectifs (fatigue 4/5, motivation 4/5) sont cohérents avec tes données biologiques. <strong>La séance Tempo de ce soir est bien adaptée.</strong> Maintiens un échauffement progressif de 12–15 min avant les intervalles.
          </div>
        </div>

        <!-- Fatigue trend -->
        <div class="insight-card">
          <div class="insight-header">
            <div class="insight-icon">📈</div>
            <div>
              <div class="insight-title">Tendance fatigue — 7 jours</div>
              <div class="insight-sub">Score subjectif moyen</div>
            </div>
          </div>
          <div class="trend-row">
            ${[3,2,4,3,4,3,4].map((v,i) => {
              const h = Math.round(v/5*36);
              const isToday = i===6;
              return `<div class="trend-bar" style="height:${h}px;background:${isToday?'#18181b':'#e4e4e7'}"></div>`;
            }).join('')}
          </div>
          <div class="trend-labels">
            ${['J-6','J-5','J-4','J-3','J-2','J-1','Auj.'].map(l => `<div class="trend-label">${l}</div>`).join('')}
          </div>
        </div>

        <!-- Muscle soreness map -->
        <div class="insight-card">
          <div class="insight-header">
            <div class="insight-icon">💪</div>
            <div>
              <div class="insight-title">État musculaire perçu</div>
              <div class="insight-sub">Zones de courbatures signalées</div>
            </div>
          </div>
          <div class="muscle-grid">
            ${[
              { zone:'Quadriceps', level:2, color:'#fef3c7', textColor:'#92400e' },
              { zone:'Mollets',    level:1, color:'#fef9ee', textColor:'#ca8a04' },
              { zone:'Ischio',     level:3, color:'#fee2e2', textColor:'#dc2626' },
              { zone:'Fessiers',   level:1, color:'#fef9ee', textColor:'#ca8a04' },
              { zone:'Dos',        level:0, color:'#f4f4f5', textColor:'#a1a1aa' },
              { zone:'Épaules',    level:0, color:'#f4f4f5', textColor:'#a1a1aa' },
              { zone:'Abdos',      level:1, color:'#fef9ee', textColor:'#ca8a04' },
              { zone:'Adducteurs', level:2, color:'#fef3c7', textColor:'#92400e' },
            ].map(m => `<div class="muscle-chip" style="background:${m.color}">
              <div class="muscle-chip-label" style="color:${m.textColor}">${m.zone}</div>
              <div class="muscle-chip-val" style="color:${m.textColor}">${['OK','Léger','Moyen','Fort'][m.level]}</div>
            </div>`).join('')}
          </div>
        </div>

        <!-- Today's plan context -->
        <div class="insight-card" style="background:#f9f9f9;border-color:#f0f0f0">
          <div class="insight-header" style="margin-bottom:6px">
            <div class="insight-icon" style="background:#fff">🏃</div>
            <div>
              <div class="insight-title">Séance prévue ce soir</div>
              <div class="insight-sub">17h00 · Tempo progressif · 55 min</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <div style="flex:1;background:#fff;border-radius:8px;padding:8px 10px;text-align:center">
              <div style="font-size:10px;color:#a1a1aa;margin-bottom:2px">Zone cible</div>
              <div style="font-family:'DM Mono',monospace;font-size:13px;font-weight:500;color:#09090b">Z3–Z4</div>
            </div>
            <div style="flex:1;background:#fff;border-radius:8px;padding:8px 10px;text-align:center">
              <div style="font-size:10px;color:#a1a1aa;margin-bottom:2px">Charge est.</div>
              <div style="font-family:'DM Mono',monospace;font-size:13px;font-weight:500;color:#09090b">68 TSS</div>
            </div>
            <div style="flex:1;background:#fff;border-radius:8px;padding:8px 10px;text-align:center">
              <div style="font-size:10px;color:#a1a1aa;margin-bottom:2px">Allure T</div>
              <div style="font-family:'DM Mono',monospace;font-size:13px;font-weight:500;color:#09090b">4:52/km</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 4/12 — /check-in · 1280×800px
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/1005-1775853957/content/checkin.html', html);
console.log('done');
