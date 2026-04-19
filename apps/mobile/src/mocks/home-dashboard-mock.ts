/**
 * Home Dashboard mock data — P6 rewrite (2026-04-19)
 * 3 états: normal (Readiness 78), ideal (92), recovery (45)
 * Source visuelle: docs/design/homedashboard/dashboard.jsx DATA.*
 *
 * Toggle DEV: tap avatar "SR" dans le header → cycle entre les 3 états.
 * REPLACED with real API in FE-MOBILE-BACKEND-WIRING.
 */

export type DashState = 'normal' | 'ideal' | 'recovery';

export interface SessionTarget {
  label: string;
  value: string;
}

export interface HomeDashSession {
  type: 'run' | 'bike' | 'lift' | 'swim' | 'recovery';
  /** Card header label */
  cardLabel: 'SÉANCE DU JOUR' | 'RÉCUPÉRATION';
  /** Right-side timestamp or "Aujourd'hui" */
  time: string;
  /** Discipline name displayed prominently */
  discipline: string;
  /** Duration string */
  duration: string;
  /** 2-line description */
  brief: string;
  /** Sport-specific targets (empty for recovery) */
  targets: SessionTarget[];
}

export interface HomeDashData {
  firstName: string;
  /** Uppercase date e.g. "SAM. 18 AVR." */
  dateLabel: string;
  readiness: {
    value: number;
    /** Positive or negative delta vs yesterday */
    delta: number;
  };
  nutrition: {
    kcal: number;
    target: number;
  };
  strain: {
    /** Display string e.g. "14.2" */
    displayValue: string;
    /** Raw numeric for semantic color thresholds: ≥18=red, ≥14=yellow, <14=green */
    semanticValue: number;
  };
  sleep: {
    /** Formatted duration e.g. "7h32" */
    duration: string;
    /** 0-100 score for semantic color: ≥80=green, ≥65=yellow, <65=red */
    score: number;
  };
  cognitiveLoad: {
    /** 0-100: ≥70=red, ≥45=yellow, <45=green */
    value: number;
    label: string;
    context: string;
  };
  session: HomeDashSession;
}

export const DASH_MOCK: Record<DashState, HomeDashData> = {
  normal: {
    firstName: 'Simon',
    dateLabel: 'SAM. 18 AVR.',
    readiness: { value: 78, delta: 4 },
    nutrition: { kcal: 2140, target: 2600 },
    strain: { displayValue: '14.2', semanticValue: 14.2 },
    sleep: { duration: '7h32', score: 82 },
    cognitiveLoad: { value: 52, label: 'Modérée', context: '62 / 100' },
    session: {
      type: 'run',
      cardLabel: 'SÉANCE DU JOUR',
      time: '09:00',
      discipline: 'Course',
      duration: '52 min',
      brief: 'Endurance fondamentale. Zone 2 stricte. Respiration nasale privilégiée.',
      targets: [
        { label: 'Allure', value: '5:42/km' },
        { label: 'FC cible', value: '142 bpm' },
        { label: 'TSS', value: '58' },
      ],
    },
  },

  ideal: {
    firstName: 'Simon',
    dateLabel: 'DIM. 19 AVR.',
    readiness: { value: 92, delta: 7 },
    nutrition: { kcal: 2480, target: 2600 },
    strain: { displayValue: '8.6', semanticValue: 8.6 },
    sleep: { duration: '8h14', score: 94 },
    cognitiveLoad: { value: 28, label: 'Basse', context: '34 / 100' },
    session: {
      type: 'bike',
      cardLabel: 'SÉANCE DU JOUR',
      time: '07:30',
      discipline: 'Vélo',
      duration: '2h10',
      brief: "Sortie sweet-spot. 3×15 min à 88% FTP. Fenêtre physiologique ouverte.",
      targets: [
        { label: 'Puissance', value: '265 W' },
        { label: 'NP', value: '248 W' },
        { label: 'TSS', value: '124' },
      ],
    },
  },

  recovery: {
    firstName: 'Simon',
    dateLabel: 'SAM. 18 AVR.',
    readiness: { value: 45, delta: -18 },
    nutrition: { kcal: 1820, target: 2400 },
    strain: { displayValue: '19.8', semanticValue: 19.8 },
    sleep: { duration: '5h48', score: 54 },
    cognitiveLoad: { value: 82, label: 'Élevée', context: '88 / 100' },
    session: {
      type: 'recovery',
      cardLabel: 'RÉCUPÉRATION',
      time: "Aujourd'hui",
      discipline: 'Récupération active',
      duration: '20–30 min',
      brief:
        "Séance prescrite annulée. HRV en baisse, Strain cumulé élevé. Mobilité, marche, sauna si dispo. Hydratation +500ml.",
      targets: [],
    },
  },
};

/** Cycle helper for the DEV avatar toggle */
export function nextDashState(current: DashState): DashState {
  const cycle: DashState[] = ['normal', 'ideal', 'recovery'];
  return cycle[(cycle.indexOf(current) + 1) % cycle.length] ?? 'normal';
}
