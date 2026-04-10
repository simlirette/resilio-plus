# RESILIO V3 — Specs des Fichiers JSON de Connaissances

> Ces fichiers sont à créer dans `data/` pendant les sessions V3.
> Ils complètent les 7 fichiers JSON existants de la V2.

---

## Fichiers V2 existants (ne pas modifier)

| Fichier | Contenu | Agent utilisateur |
|---------|---------|-------------------|
| `vdot_paces.json` | Table VDOT 20-85 avec allures | Running Coach |
| `volume_landmarks.json` | MEV/MAV/MRV par muscle | Lifting Coach |
| `muscle_overlap.json` | Matrice chevauchement inter-sports | Head Coach |
| `agent_view_map.json` | Token economy par agent | Tous |
| `nutrition_targets.json` | Macros par type de journée | Nutrition Coach |
| `running_zones.json` | Zones Seiler 3-zone + Daniels 5-zone | Running Coach |
| `food_database_cache.json` | Cache aliments Québec/Canada | Nutrition Coach |

---

## Nouveaux fichiers V3 à créer

### 1. `data/allostatic_weights.json`
**Utilisé par :** Energy Coach
**Contenu :**
```json
{
  "version": "1.0",
  "component_weights": {
    "hrv_deviation": 0.30,
    "sleep_quality": 0.25,
    "work_intensity": 0.20,
    "stress_level": 0.15,
    "cycle_phase": 0.05,
    "ea_status": 0.05
  },
  "work_intensity_scores": {
    "light": 10,
    "normal": 30,
    "heavy": 65,
    "exhausting": 90
  },
  "stress_level_scores": {
    "none": 0,
    "mild": 30,
    "significant": 70
  },
  "cycle_phase_scores": {
    "menstrual": 40,
    "follicular": 10,
    "ovulation": 15,
    "luteal": 35,
    "null": 20
  },
  "ea_status_scores": {
    "optimal": 0,
    "suboptimal": 40,
    "critical": 80
  },
  "intensity_cap_thresholds": {
    "0-40": 1.0,
    "41-60": 1.0,
    "61-80": 0.85,
    "81-100": 0.70
  }
}
```

---

### 2. `data/hormonal_adjustments.json`
**Utilisé par :** Energy Coach, Lifting Coach, Running Coach, Nutrition Coach, Recovery Coach
**Contenu :**
```json
{
  "version": "1.0",
  "phases": {
    "menstrual": {
      "days": "1-5",
      "intensity_cap": 0.90,
      "rpe_adjustment": -1,
      "pr_attempts_allowed": false,
      "ligament_risk_note": false,
      "nutrition_adjustments": {
        "iron_priority": true,
        "magnesium_priority": true,
        "omega3_priority": true,
        "calorie_adjustment_kcal": 0
      },
      "recovery_veto_threshold_adjustment": -10,
      "notes": "Prostaglandines élevées, tolérance douleur réduite, récupération ralentie"
    },
    "follicular": {
      "days": "6-13",
      "intensity_cap": 1.0,
      "rpe_adjustment": 0,
      "pr_attempts_allowed": true,
      "ligament_risk_note": false,
      "nutrition_adjustments": {
        "iron_priority": false,
        "magnesium_priority": false,
        "omega3_priority": false,
        "calorie_adjustment_kcal": 0
      },
      "recovery_veto_threshold_adjustment": 0,
      "notes": "Phase optimale. Estrogène en hausse, sensibilité insuline maximale, récupération rapide"
    },
    "ovulation": {
      "days": "14-15",
      "intensity_cap": 1.0,
      "rpe_adjustment": 0,
      "pr_attempts_allowed": true,
      "ligament_risk_note": true,
      "nutrition_adjustments": {
        "iron_priority": false,
        "magnesium_priority": false,
        "omega3_priority": false,
        "calorie_adjustment_kcal": 0
      },
      "recovery_veto_threshold_adjustment": 0,
      "notes": "Force maximale. Risque ligamentaire augmenté (laxité estrogène). Insister sur la technique."
    },
    "luteal": {
      "days": "16-28",
      "intensity_cap_early": 0.95,
      "intensity_cap_late": 0.85,
      "rpe_adjustment": -1,
      "pr_attempts_allowed": false,
      "ligament_risk_note": false,
      "nutrition_adjustments": {
        "iron_priority": false,
        "magnesium_priority": true,
        "omega3_priority": false,
        "protein_increase_g_per_kg": 0.2,
        "calorie_adjustment_kcal": 200
      },
      "recovery_veto_threshold_adjustment": 0,
      "notes": "Progestérone élevée, catabolisme musculaire accru, thermorégulation réduite. Hydratation +"
    }
  },
  "sources": [
    "McNulty et al. Int J Sports Physiol Perform 2020",
    "Huiberts et al. Sports Med 2024 - interférence membres inférieurs",
    "Romero-Moraleda et al. 2019 - cycle et performance musculaire"
  ]
}
```

---

### 3. `data/ea_thresholds.json`
**Utilisé par :** Energy Coach, Nutrition Coach, Recovery Coach
**Contenu :**
```json
{
  "version": "1.0",
  "thresholds": {
    "female": {
      "optimal_min": 45,
      "suboptimal_min": 30,
      "critical_max": 30,
      "danger_max": 25
    },
    "male": {
      "optimal_min": 45,
      "suboptimal_min": 35,
      "critical_max": 25,
      "danger_max": 20
    }
  },
  "reds_signal_days": 3,
  "formula": "EA = (Apport calorique - EAT) / kg FFM",
  "variables": {
    "EAT": "Énergie dépensée à l'entraînement (kcal)",
    "FFM": "Fat-Free Mass — masse maigre en kg"
  },
  "actions": {
    "suboptimal": "Alerte Nutrition Coach — augmenter apport calorique",
    "critical": "Veto Recovery Coach — séance annulée ou réduite",
    "reds_signal": "Escalade Head Coach — réduction charge + suggestion consultation"
  },
  "sources": [
    "Mountjoy et al. BJSM 2018 - RED-S consensus statement",
    "Loucks et al. 2003 - EA thresholds original research",
    "Burke et al. 2018 - EA female athletes"
  ]
}
```

---

### 4. `data/energy_coach_check_in_schema.json`
**Utilisé par :** Energy Coach (parsing du check-in quotidien)
**Contenu :**
```json
{
  "version": "1.0",
  "questions": [
    {
      "id": "work_intensity",
      "question_fr": "Comment s'est passée ta journée de travail ?",
      "options": ["light", "normal", "heavy", "exhausting"],
      "labels_fr": ["Légère", "Normale", "Intense", "Épuisante"],
      "required": true
    },
    {
      "id": "stress_level",
      "question_fr": "As-tu eu des facteurs de stress importants aujourd'hui ?",
      "options": ["none", "mild", "significant"],
      "labels_fr": ["Non", "Oui, léger", "Oui, significatif"],
      "required": true
    },
    {
      "id": "cycle_phase",
      "question_fr": "Phase de cycle ?",
      "options": ["menstrual", "follicular", "ovulation", "luteal"],
      "labels_fr": ["Menstruelle", "Folliculaire", "Ovulation", "Lutéale"],
      "required": false,
      "condition": "hormonal_profile.enabled == true"
    }
  ],
  "estimated_duration_seconds": 30,
  "frequency": "daily",
  "optimal_timing": "morning"
}
```

---

## Résumé — Fichiers à créer en V3

| Fichier | Session V3 | Priorité |
|---------|-----------|----------|
| `data/allostatic_weights.json` | V3-2 (Energy Coach) | 🔴 Haute |
| `data/hormonal_adjustments.json` | V3-3 (Cycle hormonal) | 🔴 Haute |
| `data/ea_thresholds.json` | V3-4 (EA + RED-S) | 🔴 Haute |
| `data/energy_coach_check_in_schema.json` | V3-2 (Energy Coach) | 🟡 Moyenne |
