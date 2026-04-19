# RESILIO — Supplément Base de Connaissances Agents (v2)

> Ce document complète la Section 5 du blueprint original avec les lacunes identifiées.
> À placer dans le repo et à référencer dans le CLAUDE.md.

---

## LACUNES IDENTIFIÉES ET CORRECTIONS

Le blueprint original avait des bases solides mais manquait de profondeur dans 6 domaines critiques :

1. **Head Coach** : Pas de modèle de gestion de charge (ACWR), pas de règles de séquençage force/endurance
2. **Running Coach** : Pas de zones d'entraînement formalisées, pas de protocoles de fractionnés, pas de tapering
3. **Lifting Coach** : Pas de périodisation ondulatoire pour hybrides, pas de velocity-based training
4. **Biking Coach** : Manque de protocoles FTP test, de zones de puissance standardisées
5. **Nutrition Coach** : Pas de protocoles d'hydratation, pas de supplémentation basée sur l'évidence
6. **Tous agents** : Pas de modèle de périodisation macro (annuelle) coordonné

---

## 1. HEAD COACH — Ajouts critiques

### 1.1 Acute:Chronic Workload Ratio (ACWR)
**Concept manquant majeur.** Le Head Coach doit monitorer le ratio charge aiguë/chronique pour prévenir les blessures.

**Règles d'affaires à ajouter** :
- ACWR = charge aiguë (7 jours) / charge chronique (moyenne 28 jours)
- Sweet spot : ACWR entre 0.8 et 1.3 → risque de blessure minimal
- Danger zone : ACWR > 1.5 → risque multiplié par 2-4x dans les 7 jours suivants
- Undertraining : ACWR < 0.8 → déconditionnement, risque accru par manque de préparation
- Utiliser EWMA (Exponentially Weighted Moving Average) plutôt que Rolling Average pour plus de sensibilité
- Appliquer l'ACWR de manière unifiée sur TOUS les sports combinés (pas par sport isolé)
- Règle du 10% : ne jamais augmenter la charge hebdomadaire totale de plus de 10% d'une semaine à l'autre

**Sources** :
- Gabbett TJ. The training—injury prevention paradox. Br J Sports Med. 2016;50:273-280
- Acute:Chronic Workload Ratio meta-analysis (PMC 12487117) — 22 études, incidence de blessure 79% dans les structures tissulaires
- Load Management and Injury Prevention in Elite Athletes (Premier Science, 2025) — Sweet spot 0.8-1.3
- ACWR for predicting sports injury risk systematic review (BMC Sports Sci Med Rehabil. 2025)

### 1.2 Séquençage force/endurance — Règles précises
**Concept insuffisamment détaillé dans le blueprint original.**

**Règles d'affaires à ajouter** :
- Si endurance avant force : intervalle minimum de 3h pour éviter interférence moléculaire aiguë (mTOR/AMPK)
- Si force avant endurance : les gains de puissance explosive sont préservés (séquence préférée pour objectifs de force)
- L'endurance à faible intensité (Zone 2, MICT) ne provoque PAS d'interférence significative avec la force
- HIIT + force dans la même session : interférence maximale → à éviter absolument
- Natation comme endurance : moins d'inflammation que la course → moins d'interférence avec la force (Casuso et al.)
- Chez les femmes : l'interférence sur la force des membres inférieurs est absente (méta-analyse Huiberts et al. 2024)
- Chez les débutants : l'interférence est quasi inexistante → concurrent training sans restriction

**Sources** :
- Concurrent Strength and Endurance Training: Sex and Training Status Meta-Analysis (Sports Med 2024;54(2):485-503, PubMed 37847373)
- Effects of concurrent training sequence semi-systematic review (Frontiers in Sports, 2025, doi:10.3389/fspor.2025.1692399)
- Optimizing concurrent training programs (Medicine 2024;103(52):e41055, PMC 11688070)
- Concurrent exercise training: do opposites distract? (PMC 5407958)
- Muscle fatigue and interference phenomenon model (Medical Hypotheses 2025;197:111607)
- Barbell Medicine: Concurrent Training and the Interference Effect (2025)

### 1.3 Périodisation macro-annuelle pour multisport
**Concept totalement absent du blueprint.**

**Règles d'affaires à ajouter** :
- Phase préparatoire générale (8-12 sem) : TID pyramidale, volume élevé, force générale
- Phase préparatoire spécifique (6-8 sem) : TID mixte → polarisée, intensité augmente, volume diminue
- Phase pré-compétition (3-4 sem) : TID polarisée, force maintien, spécificité maximale
- Phase compétition (1-3 sem) : tapering, réduction volume 40-60%, maintien intensité
- Phase transition (2-4 sem) : récupération active, volume et intensité réduits
- Le séquençage PYR → POL produit les meilleurs résultats (+3% VO2max, +1.5% performance 5K) (Casado et al.)
- Polarisé optimal pour coureurs 1500m, pyramidal plus adapté pour marathoniens
- Block periodization : blocs de 2-4 semaines concentrés sur une qualité (force, seuil, VO2max)

**Sources** :
- Training Intensity Distribution theory review (Frontiers Physiol. 2025, doi:10.3389/fphys.2025.1657892, PMC 12568352)
- Polarized vs Other TID Models scoping review (J Strength Cond Res 2024)
- Effects of pyramidal and polarized TID in well-trained runners (PMC 9299127, PubMed 34792817)
- ML-based personalized training models marathon (Scientific Reports 2025, doi:10.1038/s41598-025-25369-7)
- Block periodization of endurance training meta-analysis (Mølmen & Øfsteng)

---

## 2. RUNNING COACH — Ajouts critiques

### 2.1 Zones d'entraînement formalisées
**Manquait complètement dans le blueprint.**

**Table de zones (modèle Daniels/Seiler hybride)** :
```json
{
  "zones": {
    "Z1_easy": {
      "description": "Endurance fondamentale, conversation facile",
      "hr_percent_max": [60, 74],
      "pace_reference": "Easy pace (Daniels)",
      "lactate_mmol": [0.8, 2.0],
      "volume_percent_weekly": [75, 80],
      "purpose": "Base aérobie, récupération active, adaptation mitochondriale"
    },
    "Z2_tempo": {
      "description": "Seuil lactique, confortablement difficile",
      "hr_percent_max": [80, 88],
      "pace_reference": "Tempo/Threshold pace (Daniels T-pace)",
      "lactate_mmol": [2.0, 4.0],
      "volume_percent_weekly": [5, 10],
      "purpose": "Amélioration seuil lactique, économie de course"
    },
    "Z3_vo2max": {
      "description": "Intervalles durs, respiration lourde",
      "hr_percent_max": [95, 100],
      "pace_reference": "Interval pace (Daniels I-pace)",
      "lactate_mmol": [6.0, 10.0],
      "volume_percent_weekly": [5, 8],
      "purpose": "VO2max, capacité aérobie maximale"
    },
    "Z4_repetition": {
      "description": "Sprints courts, vitesse pure",
      "hr_percent_max": "N/A (trop court)",
      "pace_reference": "Repetition pace (Daniels R-pace)",
      "volume_percent_weekly": [2, 5],
      "purpose": "Économie de course, recrutement fibres rapides"
    }
  }
}
```

### 2.2 Protocoles de séances clés manquants
- **Long run** : 20-33% du volume hebdomadaire, allure Z1, durée 90-150min
- **Tempo run** : 20-40min à T-pace, ou cruise intervals (3x10min à T-pace, 2min repos)
- **VO2max intervals** : 5-6 x 3-5min à I-pace, repos = durée de l'intervalle
- **Repetitions** : 8-12 x 200-400m à R-pace, repos complet (jog recovery)
- **Progression run** : commence en Z1, termine en Z2 sur les 20-30 dernières minutes
- **Tapering** : réduction volume 40-60% sur 2-3 semaines, maintien de 1-2 séances d'intensité courtes

### 2.3 Règle des 10% et progression
- Ne jamais augmenter le volume hebdomadaire de plus de 10%
- Semaine de décharge (deload) toutes les 3-4 semaines : -20-30% de volume
- Augmenter d'abord la fréquence, puis la durée, puis l'intensité (dans cet ordre)

**Sources additionnelles** :
- Daniels J. Daniels' Running Formula (4th ed.) — référence zones VDOT
- Pfitzinger P, Douglas S. Advanced Marathoning — plans marathon structurés
- Fitzgerald M. 80/20 Running — ratio 80% facile / 20% dur
- Seiler S. What is Best Practice for Training Intensity and Duration Distribution? (IJSPP 2010)

---

## 3. LIFTING COACH — Ajouts critiques

### 3.1 Périodisation ondulatoire pour athlètes hybrides
**Modèle recommandé quand la périodisation linéaire classique est trop rigide.**

**Règles d'affaires à ajouter** :
- Daily Undulating Periodization (DUP) : alterner force (3-5 reps), hypertrophie (8-12 reps), endurance musculaire (15-20 reps) dans la même semaine
- Pour hybrides : DUP simplifié → Jour A (force, 4-6 reps, 3-4 RIR) / Jour B (hypertrophie, 8-12 reps, 1-2 RIR)
- Avantage DUP pour hybrides : flexibilité pour adapter chaque séance selon la fatigue de la course
- Si la course a été intense la veille : basculer vers hypertrophie (moins coûteux en SNC) plutôt que force
- Fréquence optimale par groupe musculaire : 2x/semaine (stimulus minimum pour hypertrophie)

### 3.2 Velocity-Based Training (VBT)
**Concept émergent, pertinent pour monitoring de la fatigue.**

**Règles d'affaires** :
- Mesurer la vitesse de la barre pour évaluer la fatigue en temps réel
- Perte de vélocité de 20% → arrêter la série (optimal pour hybrides, minimise la fatigue)
- Perte de vélocité de 30-40% → trop de fatigue systémique pour un hybride
- Corrélation directe entre vitesse du 1RM et %1RM estimé

### 3.3 Exercices prioritaires pour hybrides (table étendue)
```json
{
  "tier_1_high_sfr_low_cns": [
    "Machine Leg Press", "Hack Squat Machine", "Seated Leg Curl",
    "Lat Pulldown", "Cable Row", "Machine Chest Press",
    "Cable Lateral Raise", "Overhead Cable Tricep Extension",
    "Incline Dumbbell Curl", "Leg Extension"
  ],
  "tier_2_moderate_sfr_moderate_cns": [
    "Romanian Deadlift (DB)", "Bulgarian Split Squat",
    "Dumbbell Bench Press", "Barbell Row", "Overhead Press (DB)",
    "Pull-ups", "Dips"
  ],
  "tier_3_low_sfr_high_cns_use_sparingly": [
    "Barbell Back Squat", "Conventional Deadlift", "Barbell Bench Press",
    "Barbell Overhead Press", "Power Clean"
  ],
  "notes": "En phase de volume course élevé, privilégier Tier 1. En phase base/off-season, Tier 2-3 acceptables."
}
```

**Sources additionnelles** :
- Zourdos MC et al. Novel Resistance Training-Specific RPE Scale (J Strength Cond Res 2016)
- Helms ER et al. RPE and Velocity Relationships (J Strength Cond Res 2017)
- Schoenfeld BJ. The Mechanisms of Muscle Hypertrophy (J Strength Cond Res 2010)
- Israetel M. Scientific Principles of Hypertrophy Training (Renaissance Periodization)
- Current Concepts in Periodization of Strength and Conditioning (PMC 4637911)

---

## 4. BIKING COACH — Ajouts critiques

### 4.1 Zones de puissance standardisées (modèle Coggan)
**Manquait complètement.**

```json
{
  "zones": {
    "Z1_active_recovery": {"percent_ftp": [0, 55], "description": "Récupération active"},
    "Z2_endurance": {"percent_ftp": [56, 75], "description": "Endurance, conversation possible"},
    "Z3_tempo": {"percent_ftp": [76, 90], "description": "Tempo, effort soutenu"},
    "Z4_threshold": {"percent_ftp": [91, 105], "description": "Seuil lactique, ~60min soutenable"},
    "Z5_vo2max": {"percent_ftp": [106, 120], "description": "VO2max, 3-8min"},
    "Z6_anaerobic": {"percent_ftp": [121, 150], "description": "Capacité anaérobie, 30s-3min"},
    "Z7_neuromuscular": {"percent_ftp": [150, 999], "description": "Sprint, <30s"}
  }
}
```

### 4.2 Protocoles FTP
- **Test FTP 20min** : 20min all-out, FTP = 95% de la puissance moyenne
- **Ramp test** : incréments de 25W/min, FTP = 75% de la puissance max atteinte
- **Réévaluation** : toutes les 6-8 semaines ou après un bloc d'entraînement

### 4.3 Métriques clés via Strava/capteurs
- **Normalized Power (NP)** : puissance moyenne pondérée (lisse les variations)
- **Intensity Factor (IF)** : NP / FTP (>1.0 = au-dessus du seuil)
- **Training Stress Score (TSS)** : (durée × NP × IF) / (FTP × 3600) × 100
- **Chronic Training Load (CTL)** : moyenne exponentielle 42 jours du TSS
- **Acute Training Load (ATL)** : moyenne exponentielle 7 jours du TSS
- **Training Stress Balance (TSB)** : CTL - ATL (forme = positif, fatigue = négatif)
- Note : Strava utilise "Training Load" et "Relative Effort" (TRIMP), pas TSS directement. Le PPi (section originale) reste supérieur pour les efforts supramaximaux.

---

## 5. SWIMMING COACH — Ajouts critiques

### 5.1 Zones de natation (CSS-based)
**Critical Swim Speed (CSS)** = seuil lactique en natation, calculé à partir de tests 200m et 400m.

```
CSS = (Distance400 - Distance200) / (Time400 - Time200)
```

**Zones basées sur CSS** :
- Z1 (< 85% CSS) : Technique, échauffement, récupération
- Z2 (85-95% CSS) : Endurance aérobie
- Z3 (95-100% CSS) : Seuil (CSS pace)
- Z4 (100-105% CSS) : VO2max natation
- Z5 (> 105% CSS) : Sprint, vitesse pure

### 5.2 Séances types manquantes
- **Pull sets** : avec plaquettes, focus sur la propulsion bras → améliore DPS
- **Kick sets** : avec planche, renforcement des jambes pour la propulsion
- **Drill sets** : éducatifs techniques (catch-up, finger drag, fist drill)
- **Threshold sets** : 5-10 x 200m @ CSS pace, 15-20s repos
- **VO2max sets** : 8 x 100m @ Z4, 20s repos

---

## 6. NUTRITION COACH — Ajouts critiques

### 6.1 Hydratation (totalement absent du blueprint)
**Règles d'affaires** :
- Baseline quotidien : 35-40ml/kg de poids corporel
- Pré-exercice : 5-7ml/kg 2-4h avant
- Pendant l'effort : 400-800ml/h selon la sudation et la température
- Post-exercice : 1.5L par kg de poids perdu pendant l'effort
- Sodium : 500-1000mg/L dans les boissons d'effort (>60min)
- Surveiller la couleur de l'urine comme indicateur simple (paille clair = hydraté)

### 6.2 Supplémentation basée sur l'évidence
**Seuls les suppléments avec un niveau A d'évidence (ISSN/AIS)** :
- **Créatine monohydrate** : 3-5g/jour, améliore la puissance et la récupération (non réservé aux bodybuilders, bénéfique pour hybrides)
- **Caféine** : 3-6mg/kg 30-60min pré-effort, améliore la performance endurance et force
- **Beta-alanine** : 3.2-6.4g/jour (doses fractionnées), tamponne l'acidité pour efforts 1-10min
- **Bicarbonate de sodium** : 0.3g/kg 1-2h pré-effort, tamponne l'acidité (attention GI)
- **Nitrate (betterave)** : 6-8mmol 2-3h pré-effort, améliore l'économie de course de 1-3%
- **Vitamine D** : 1000-2000 UI/jour si déficience (fréquent chez les athlètes nordiques)
- **Fer** : uniquement sur diagnostic de carence (ferritine < 30ng/mL)
- **Oméga-3** : 2-4g EPA+DHA/jour, réduit l'inflammation systémique post-entraînement concurrent

### 6.3 Nutrition péri-compétition
- **Carb loading** : 10-12g/kg/jour les 36-48h avant la compétition longue distance
- **Dernier repas** : 2-4h avant, 1-4g/kg glucides, faible en fibres et lipides
- **Intra-course** :
  - < 60 min : pas de nutrition nécessaire (eau suffit)
  - 60-150 min : 30-60g glucides/heure (boisson sportive ou gels)
  - > 150 min : 60-90g/h avec ratio glucose:fructose 2:1 (entraîner le gut)
  - > 3h : ajouter sodium 500-1000mg/h
- **Post-course** : fenêtre 30-60min, 1-1.2g/kg glucides + 0.3g/kg protéines

**Sources additionnelles** :
- ISSN Position Stand: Caffeine and Exercise Performance (JISSN 2021)
- ISSN Position Stand: Creatine Supplementation (JISSN 2017)
- Australian Institute of Sport (AIS) Supplement Classification System
- IOC Consensus Statement on Dietary Supplements (Br J Sports Med 2018)
- Jeukendrup AE. Training the Gut for Athletes (Sports Med 2017)
- Thomas DT et al. ACSM Joint Position Statement: Nutrition and Athletic Performance (Med Sci Sports Exerc 2016)

---

## 7. RECOVERY COACH — Ajouts critiques

### 7.1 Protocoles de récupération actifs
**Manquaient du blueprint.**
- Compression pneumatique (NormaTec) : 20-30min post-entraînement intense
- Bains froids / CWI (Cold Water Immersion) : 10-15°C pendant 10-15min → réduit les DOMS mais peut atténuer les adaptations d'hypertrophie (à utiliser uniquement en phase compétitive, pas en phase de construction)
- Massage / foam rolling : 10-15min pré/post, améliore la mobilité et la circulation
- Yoga/étirements dynamiques : récupération active les jours off

### 7.2 Readiness Score quotidien
**L'agent doit calculer un score de préparation composite :**
```
Readiness Score = f(HRV_RMSSD, sommeil_qualité, sommeil_durée, RPE_veille, humeur_subjective)

Catégories :
- Vert (>75%) : entraînement prévu OK, possibilité d'intensifier
- Jaune (50-75%) : maintenir le plan mais réduire l'intensité de 10-20%
- Rouge (<50%) : journée de récupération ou entraînement très léger Z1 uniquement
```

---

## RÉSUMÉ DES SOURCES AJOUTÉES (non présentes dans le blueprint original)

### Head Coach (6 nouvelles sources)
1. Gabbett TJ. The training—injury prevention paradox (BJSM 2016)
2. ACWR meta-analysis (PMC 12487117, 2025)
3. Load Management in Elite Athletes (Premier Science, 2025)
4. Concurrent training sequence review (Frontiers Sports 2025)
5. Concurrent training sex/status meta-analysis (Sports Med 2024)
6. TID theory advances review (Frontiers Physiol 2025, PMC 12568352)

### Running Coach (4 nouvelles sources)
7. Daniels' Running Formula (zones VDOT)
8. Seiler S. Best Practice for Training Intensity Distribution (IJSPP 2010)
9. Pyramidal→Polarized transition study (PMC 9299127)
10. ML-personalized marathon training (Scientific Reports 2025)

### Lifting Coach (3 nouvelles sources)
11. Zourdos MC. Novel RPE Scale for Resistance Training (JSCR 2016)
12. Current Concepts in Periodization S&C (PMC 4637911)
13. Israetel M. Scientific Principles of Hypertrophy Training (RP)

### Biking Coach (2 nouvelles sources)
14. Strava Engineering: Fitness & Freshness / TRIMP methodology
15. Coggan A. Training and Racing with a Power Meter (zones de puissance)

### Nutrition Coach (6 nouvelles sources)
16. ISSN Position Stand: Caffeine (JISSN 2021)
17. ISSN Position Stand: Creatine (JISSN 2017)
18. AIS Supplement Classification System
19. IOC Consensus: Dietary Supplements (BJSM 2018)
20. Jeukendrup AE. Training the Gut (Sports Med 2017)
21. ACSM Joint Position: Nutrition and Athletic Performance (2016)

### Recovery Coach (0 nouvelle source formelle, concepts de pratique clinique)

**Total** : 21 nouvelles sources → 67 sources totales pour l'ensemble des agents.
