// Training history — ~10 weeks back from today (April 18, 2026)
// Hybrid athlete: run/lift/bike/swim + rest days. Realistic distribution.
// Each session has: date (YYYY-MM-DD), type, name, duration (min), load (TSS-like), rpe, distance?

(function () {
  // Today pinned to 2026-04-18 (Saturday) for deterministic rendering
  const TODAY = new Date(2026, 3, 18); // month is 0-indexed

  const fmt = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${dd}`;
  };

  // Hand-authored ~10 weeks of realistic hybrid training.
  // Pattern: ~5 sessions/week with at least one rest day, occasional doubles.
  // Key: each entry is {daysAgo: N, sessions: [...]}
  // Rest days are implicit (no entry for that date).
  const plan = [
    // ── Current week (W of Mon Apr 13) — Apr 18 is Saturday today ──
    { daysAgo: 0, sessions: [{ type: 'run', name: 'Sortie longue Z2', dur: 95, load: 88, rpe: 5, dist: 18.2 }] },
    { daysAgo: 1, sessions: [{ type: 'lift', name: 'Full body — Force', dur: 62, load: 55, rpe: 7 }] },
    { daysAgo: 2, sessions: [
      { type: 'swim', name: 'Technique + 8x100', dur: 45, load: 28, rpe: 4, dist: 2.1 },
      { type: 'bike', name: 'Home trainer Z2', dur: 60, load: 52, rpe: 5, dist: 28.4 },
    ]},
    { daysAgo: 3, sessions: [{ type: 'run', name: 'Seuil 3x8 min', dur: 58, load: 74, rpe: 8, dist: 11.6 }] },
    // Apr 14: rest
    { daysAgo: 5, sessions: [{ type: 'lift', name: 'Lower — Hypertrophie', dur: 70, load: 62, rpe: 7 }] },
    { daysAgo: 6, sessions: [{ type: 'run', name: 'Footing récup', dur: 35, load: 22, rpe: 3, dist: 6.4 }] },

    // ── W of Mon Apr 6 ──
    { daysAgo: 7, sessions: [
      { type: 'run', name: 'Sortie longue + côtes', dur: 105, load: 96, rpe: 6, dist: 19.5 },
    ]},
    { daysAgo: 8, sessions: [{ type: 'bike', name: 'Sweet spot 3x12', dur: 75, load: 89, rpe: 7, dist: 34.1 }] },
    { daysAgo: 9, sessions: [{ type: 'lift', name: 'Upper — Force', dur: 58, load: 52, rpe: 7 }] },
    // Apr 8: rest
    { daysAgo: 11, sessions: [{ type: 'swim', name: 'Endurance 2500m', dur: 50, load: 34, rpe: 5, dist: 2.5 }] },
    { daysAgo: 12, sessions: [{ type: 'run', name: 'VMA 8x400', dur: 48, load: 68, rpe: 9, dist: 9.2 }] },
    { daysAgo: 13, sessions: [{ type: 'lift', name: 'Full body — Volume', dur: 65, load: 58, rpe: 6 }] },

    // ── W of Mar 30 ──
    { daysAgo: 14, sessions: [{ type: 'run', name: 'Sortie longue Z2', dur: 88, load: 80, rpe: 5, dist: 16.8 }] },
    { daysAgo: 15, sessions: [
      { type: 'swim', name: 'Pull + kick', dur: 42, load: 26, rpe: 4, dist: 2.0 },
      { type: 'lift', name: 'Lower — Force', dur: 55, load: 48, rpe: 7 },
    ]},
    // Mar 31: rest
    { daysAgo: 17, sessions: [{ type: 'bike', name: 'Z2 long', dur: 95, load: 78, rpe: 5, dist: 42.3 }] },
    { daysAgo: 18, sessions: [{ type: 'run', name: 'Tempo 30 min', dur: 52, load: 64, rpe: 7, dist: 10.2 }] },
    { daysAgo: 19, sessions: [{ type: 'lift', name: 'Upper — Volume', dur: 62, load: 54, rpe: 6 }] },
    // Apr 4: rest

    // ── W of Mar 23 ──
    { daysAgo: 21, sessions: [{ type: 'run', name: 'Sortie longue progressive', dur: 92, load: 86, rpe: 6, dist: 17.4 }] },
    { daysAgo: 22, sessions: [{ type: 'lift', name: 'Full body — Force', dur: 60, load: 54, rpe: 7 }] },
    { daysAgo: 23, sessions: [{ type: 'swim', name: 'Seuil 6x200', dur: 48, load: 38, rpe: 7, dist: 2.2 }] },
    { daysAgo: 24, sessions: [{ type: 'bike', name: 'Intervalles 5x5', dur: 70, load: 92, rpe: 8, dist: 31.8 }] },
    // Mar 27: rest
    { daysAgo: 26, sessions: [{ type: 'run', name: 'VMA courte 12x200', dur: 45, load: 62, rpe: 9, dist: 8.4 }] },
    { daysAgo: 27, sessions: [{ type: 'lift', name: 'Lower — Hypertrophie', dur: 72, load: 64, rpe: 7 }] },

    // ── W of Mar 16 ──
    { daysAgo: 28, sessions: [{ type: 'run', name: 'Sortie longue Z2', dur: 85, load: 76, rpe: 5, dist: 16.2 }] },
    { daysAgo: 29, sessions: [{ type: 'bike', name: 'Sweet spot 2x20', dur: 80, load: 95, rpe: 7, dist: 36.4 }] },
    // Mar 21: rest
    { daysAgo: 31, sessions: [
      { type: 'swim', name: 'Technique', dur: 40, load: 24, rpe: 3, dist: 1.8 },
      { type: 'lift', name: 'Upper — Force', dur: 55, load: 50, rpe: 7 },
    ]},
    { daysAgo: 32, sessions: [{ type: 'run', name: 'Seuil 20 min continu', dur: 50, load: 70, rpe: 8, dist: 9.8 }] },
    { daysAgo: 33, sessions: [{ type: 'lift', name: 'Lower — Force', dur: 58, load: 52, rpe: 7 }] },
    { daysAgo: 34, sessions: [{ type: 'run', name: 'Footing récup', dur: 32, load: 20, rpe: 3, dist: 5.8 }] },

    // ── W of Mar 9 ──
    { daysAgo: 35, sessions: [{ type: 'run', name: 'Sortie longue 20k', dur: 110, load: 102, rpe: 6, dist: 20.1 }] },
    { daysAgo: 36, sessions: [{ type: 'lift', name: 'Full body — Force', dur: 62, load: 56, rpe: 7 }] },
    { daysAgo: 37, sessions: [{ type: 'swim', name: 'Endurance 3000m', dur: 55, load: 38, rpe: 5, dist: 3.0 }] },
    { daysAgo: 38, sessions: [{ type: 'bike', name: 'Z2 vallonné', dur: 90, load: 82, rpe: 6, dist: 38.2 }] },
    // Mar 13: rest
    // Mar 14: rest
    { daysAgo: 41, sessions: [{ type: 'run', name: 'VMA 10x300', dur: 50, load: 66, rpe: 9, dist: 9.0 }] },

    // ── W of Mar 2 ──
    { daysAgo: 42, sessions: [{ type: 'lift', name: 'Upper — Volume', dur: 65, load: 58, rpe: 6 }] },
    { daysAgo: 43, sessions: [{ type: 'run', name: 'Sortie longue Z2', dur: 90, load: 82, rpe: 5, dist: 17.0 }] },
    { daysAgo: 44, sessions: [{ type: 'bike', name: 'Intervalles courts', dur: 65, load: 86, rpe: 8, dist: 29.8 }] },
    // Mar 5: rest
    { daysAgo: 46, sessions: [{ type: 'swim', name: 'Seuil 8x150', dur: 45, load: 34, rpe: 7, dist: 2.0 }] },
    { daysAgo: 47, sessions: [
      { type: 'run', name: 'Tempo progressif', dur: 55, load: 68, rpe: 7, dist: 10.8 },
      { type: 'lift', name: 'Lower — Volume', dur: 60, load: 52, rpe: 6 },
    ]},
    // Mar 8: rest

    // ── W of Feb 23 ──
    { daysAgo: 49, sessions: [{ type: 'run', name: 'Sortie longue Z2', dur: 82, load: 74, rpe: 5, dist: 15.6 }] },
    { daysAgo: 50, sessions: [{ type: 'lift', name: 'Full body — Force', dur: 58, load: 52, rpe: 7 }] },
    { daysAgo: 51, sessions: [{ type: 'bike', name: 'Sweet spot 4x8', dur: 72, load: 88, rpe: 7, dist: 32.6 }] },
    // Feb 26: rest
    { daysAgo: 53, sessions: [{ type: 'swim', name: 'Technique + 6x100', dur: 42, load: 28, rpe: 4, dist: 1.9 }] },
    { daysAgo: 54, sessions: [{ type: 'run', name: 'VMA 6x600', dur: 55, load: 72, rpe: 9, dist: 10.4 }] },
    { daysAgo: 55, sessions: [{ type: 'lift', name: 'Upper — Force', dur: 56, load: 50, rpe: 7 }] },

    // ── W of Feb 16 ──
    { daysAgo: 56, sessions: [{ type: 'run', name: 'Sortie longue 18k', dur: 96, load: 88, rpe: 6, dist: 18.0 }] },
    { daysAgo: 57, sessions: [{ type: 'bike', name: 'Z2 long', dur: 100, load: 82, rpe: 5, dist: 44.1 }] },
    // Feb 19: rest
    { daysAgo: 59, sessions: [{ type: 'lift', name: 'Lower — Hypertrophie', dur: 68, load: 62, rpe: 7 }] },
    { daysAgo: 60, sessions: [{ type: 'swim', name: 'Endurance 2800m', dur: 52, load: 36, rpe: 5, dist: 2.8 }] },
    { daysAgo: 61, sessions: [{ type: 'run', name: 'Seuil 2x15 min', dur: 54, load: 72, rpe: 8, dist: 10.6 }] },
    { daysAgo: 62, sessions: [{ type: 'lift', name: 'Full body — Volume', dur: 60, load: 54, rpe: 6 }] },

    // ── W of Feb 9 — partial ──
    { daysAgo: 63, sessions: [{ type: 'run', name: 'Sortie longue Z2', dur: 86, load: 78, rpe: 5, dist: 16.4 }] },
    { daysAgo: 64, sessions: [{ type: 'lift', name: 'Upper — Force', dur: 58, load: 52, rpe: 7 }] },
    { daysAgo: 66, sessions: [{ type: 'bike', name: 'Sweet spot 3x10', dur: 70, load: 86, rpe: 7, dist: 31.4 }] },
    { daysAgo: 68, sessions: [{ type: 'run', name: 'VMA 8x400', dur: 48, load: 68, rpe: 9, dist: 9.2 }] },
  ];

  // Expand into { 'YYYY-MM-DD': [sessions] }
  const byDate = {};
  let idCounter = 1;
  plan.forEach(({ daysAgo, sessions }) => {
    const d = new Date(TODAY);
    d.setDate(d.getDate() - daysAgo);
    const key = fmt(d);
    byDate[key] = sessions.map(s => ({ ...s, id: idCounter++, dateKey: key }));
  });

  window.TRAINING_DATA = {
    today: TODAY,
    todayKey: fmt(TODAY),
    byDate,
    fmt,
  };
})();
