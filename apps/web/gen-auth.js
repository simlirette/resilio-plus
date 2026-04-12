const fs = require('fs');

const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Resilio+ — Connexion</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=DM+Mono:wght@400;500&family=Playfair+Display:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'DM Sans',system-ui; background:#e8e8e8; display:flex; align-items:center; justify-content:center; min-height:100vh; padding:32px; }
.frame { width:1280px; height:800px; background:#fafafa; border-radius:16px; box-shadow:0 12px 64px rgba(0,0,0,0.16); display:flex; overflow:hidden; }

/* ── LEFT PANEL ── */
.left {
  flex:1; background:#fff; border-right:1px solid #e4e4e7;
  display:flex; flex-direction:column; justify-content:space-between;
  padding:52px 60px; position:relative; overflow:hidden;
}

/* Subtle dot grid */
.left::before {
  content:'';
  position:absolute; inset:0;
  background-image: radial-gradient(circle, #d4d4d8 1px, transparent 1px);
  background-size:28px 28px;
  opacity:0.45;
  pointer-events:none;
}

/* Green glow */
.left::after {
  content:'';
  position:absolute;
  width:480px; height:480px; border-radius:50%;
  background:radial-gradient(circle, rgba(22,163,74,0.08) 0%, transparent 68%);
  bottom:-80px; left:-60px;
  pointer-events:none;
}

.left-logo { position:relative; z-index:1; }
.logo-text { font-family:'Playfair Display',serif; font-size:26px; color:#09090b; }
.logo-plus { color:#16a34a; }

.left-center { position:relative; z-index:1; }
.left-tagline { font-family:'Playfair Display',serif; font-size:40px; color:#09090b; line-height:1.2; letter-spacing:-0.03em; margin-bottom:18px; }
.left-tagline em { color:#16a34a; font-style:italic; }
.left-sub { font-size:14px; color:#71717a; line-height:1.65; max-width:360px; }

.left-bottom { position:relative; z-index:1; }

/* Stats */
.stats-row { display:flex; gap:36px; margin-bottom:28px; }
.stat-val { font-family:'DM Mono',monospace; font-size:20px; font-weight:500; color:#09090b; }
.stat-label { font-size:10px; color:#a1a1aa; text-transform:uppercase; letter-spacing:0.1em; margin-top:3px; }

/* Sport pills */
.sport-pills { display:flex; gap:7px; flex-wrap:wrap; }
.sport-pill { display:flex; align-items:center; gap:5px; padding:5px 11px; border-radius:20px; border:1px solid #e4e4e7; background:#fafafa; font-size:12px; color:#52525b; }
.sport-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }

/* ── RIGHT PANEL ── */
.right { width:440px; min-width:440px; display:flex; flex-direction:column; justify-content:center; padding:60px 52px; }

.form-header { margin-bottom:32px; }
.form-title { font-family:'Playfair Display',serif; font-size:28px; color:#09090b; letter-spacing:-0.02em; margin-bottom:6px; }
.form-sub { font-size:14px; color:#71717a; }

/* Fields */
.field { margin-bottom:14px; }
.field-label { font-size:12px; font-weight:500; color:#3f3f46; margin-bottom:6px; display:block; }
.field-input {
  width:100%; padding:12px 14px; border:1px solid #e4e4e7; border-radius:9px;
  font-family:'DM Sans',system-ui; font-size:14px; color:#09090b; background:#fff;
  outline:none; transition:border-color 0.15s;
}
.field-input:focus { border-color:#a1a1aa; }
.field-input::placeholder { color:#d4d4d8; }
.field-input.filled { border-color:#d4d4d8; }

.field-password { position:relative; }
.field-password .field-input { padding-right:44px; }
.field-eye { position:absolute; right:13px; top:50%; transform:translateY(-50%); cursor:pointer; }

.forgot { text-align:right; margin-top:-6px; margin-bottom:22px; }
.forgot a { font-size:12px; color:#71717a; text-decoration:none; }
.forgot a:hover { color:#09090b; }

.submit-btn {
  width:100%; padding:13px; border-radius:10px; border:none; cursor:pointer;
  background:#18181b; color:#fff; font-family:'DM Sans',system-ui;
  font-size:14px; font-weight:500; transition:background 0.15s; margin-bottom:20px;
}
.submit-btn:hover { background:#3f3f46; }

.divider-row { display:flex; align-items:center; gap:12px; margin-bottom:20px; }
.divider-line { flex:1; height:1px; background:#e4e4e7; }
.divider-text { font-size:11px; color:#a1a1aa; white-space:nowrap; }

.signup-row { text-align:center; font-size:13px; color:#71717a; }
.signup-row a { color:#09090b; font-weight:500; text-decoration:none; }
.signup-row a:hover { text-decoration:underline; }

.onboarding-note { margin-top:28px; padding:13px 15px; background:#f4f4f5; border-radius:9px; font-size:12px; color:#71717a; line-height:1.55; }
.onboarding-note strong { color:#09090b; }
</style>
</head>
<body>
<div class="frame">

  <!-- LEFT: branding -->
  <div class="left">
    <div class="left-logo">
      <span class="logo-text">Resilio<span class="logo-plus">+</span></span>
    </div>

    <div class="left-center">
      <div class="left-tagline">
        Entraîne-toi<br>plus <em>intelligemment</em>,<br>pas plus fort.
      </div>
      <div class="left-sub">
        Un coach IA qui orchestre 7 agents spécialisés pour créer ton plan d'entraînement personnalisé — adapté chaque semaine à ta récupération et tes performances.
      </div>
    </div>

    <div class="left-bottom">
      <div class="stats-row">
        <div>
          <div class="stat-val">7</div>
          <div class="stat-label">Agents IA</div>
        </div>
        <div>
          <div class="stat-val">4</div>
          <div class="stat-label">Sports</div>
        </div>
        <div>
          <div class="stat-val">HRV</div>
          <div class="stat-label">Biomarqueurs</div>
        </div>
        <div>
          <div class="stat-val">↺</div>
          <div class="stat-label">Adaptatif</div>
        </div>
      </div>
      <div class="sport-pills">
        <div class="sport-pill"><div class="sport-dot" style="background:#3b82f6"></div>Course</div>
        <div class="sport-pill"><div class="sport-dot" style="background:#f59e0b"></div>Vélo</div>
        <div class="sport-pill"><div class="sport-dot" style="background:#06b6d4"></div>Natation</div>
        <div class="sport-pill"><div class="sport-dot" style="background:#8b5cf6"></div>Musculation</div>
      </div>
    </div>
  </div>

  <!-- RIGHT: form -->
  <div class="right">
    <div class="form-header">
      <div class="form-title">Bon retour</div>
      <div class="form-sub">Connecte-toi à ton espace coach</div>
    </div>

    <div class="field">
      <label class="field-label">Adresse email</label>
      <input class="field-input filled" type="email" value="simon@example.com">
    </div>

    <div class="field">
      <label class="field-label">Mot de passe</label>
      <div class="field-password">
        <input class="field-input" type="password" placeholder="••••••••">
        <svg class="field-eye" viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M2 10s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6z" stroke="#a1a1aa" stroke-width="1.4"/>
          <circle cx="10" cy="10" r="2.5" stroke="#a1a1aa" stroke-width="1.4"/>
        </svg>
      </div>
    </div>

    <div class="forgot"><a href="#">Mot de passe oublié ?</a></div>

    <button class="submit-btn">Se connecter →</button>

    <div class="divider-row">
      <div class="divider-line"></div>
      <div class="divider-text">Pas encore de compte ?</div>
      <div class="divider-line"></div>
    </div>

    <div class="signup-row"><a href="#">Créer un compte</a></div>

    <div class="onboarding-note">
      <strong>Première connexion ?</strong> Un court questionnaire de 5 minutes te permettra de personnaliser ton profil athlète et lancer ton premier plan d'entraînement.
    </div>
  </div>

</div>

<div style="text-align:center;margin-top:18px;font-size:11px;color:#71717a;font-family:'DM Sans',system-ui">
  Page 5/12 — /auth · 1280×800px
</div>
</body>
</html>`;

fs.writeFileSync('C:/Users/simon/resilio-plus/.superpowers/brainstorm/268-1775885848/content/auth.html', html);
console.log('done');
