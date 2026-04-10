# RESILIO+ V3 — Document Maître
# Orchestrateur de l'Énergie Humaine Complète

> **Statut** : Document de vision et d'architecture V3. Ne pas implémenter avant la completion de la V2.
> **Prérequis** : V2 complète et stable sur branche `main`.
> **Repo** : `C:\Users\simon\resilio-plus` — branche `v3` (créer depuis `main`)

---

## TABLE DES MATIÈRES

1. Vision V3 — Ce qui change fondamentalement
2. Nouveaux agents et agents étendus
3. Energy Coach — Architecture complète
4. Cycle Hormonal Féminin — Intégration transversale
5. Charge Allostatique — Modélisation
6. Energy Availability (EA) — Seuils et veto
7. AthleteState V3 — Nouveaux champs
8. Différenciateurs commerciaux
9. Plan d'exécution Superpowers V3

---

# 1. VISION V3 — CE QUI CHANGE FONDAMENTALEMENT

## 1.1 De prescripteur à orchestrateur d'énergie

La V2 est un **prescripteur de workouts** : elle génère des plans exacts, gère la fatigue physique, orchestre les agents.

La V3 est un **orchestrateur de l'énergie humaine complète** : elle traite le corps comme un système énergétique total où la fatigue cognitive, hormonale et professionnelle ont le même statut que la fatigue musculaire.

| Dimension | V2 | V3 |
|-----------|----|----|
| Fatigue modélisée | Musculaire + CNS + ACWR | + Cognitive + Hormonale + Allostatic Load |
| Variables d'entrée | Strava, Hevy, HRV, sommeil | + Stress professionnel, cycle menstruel, EA |
| Agents | 6 (Head, Running, Lifting, Recovery, Nutrition, Swimming/Biking) | + Energy Coach |
| Veto Recovery Coach | Basé sur HRV + ACWR | + EA + Allostatic Score + Phase cycle |
| Profil athlète | Physique + historique sportif | + Profil hormonal + charge de vie |

## 1.2 Principe fondateur V3

> "Le corps ne distingue pas la fatigue d'une réunion de 4 heures et la fatigue d'un tempo run. Les deux épuisent les mêmes systèmes de récupération."

Aucun outil mainstream (TrainingPeaks, Whoop, Garmin Coach) ne modélise ceci. C'est le différenciateur central de Resilio+ V3.

---

# 2. NOUVEAUX AGENTS ET AGENTS ÉTENDUS

## 2.1 Architecture V3 — Hub-and-Spoke étendu

```
HEAD COACH (orchestre, arbitre, communique)
    │
    ├── RUNNING COACH (inchangé V2 + intégration EA)
    ├── LIFTING COACH (inchangé V2 + ajustements phase cycle)
    ├── SWIMMING COACH (inchangé V2)
    ├── BIKING COACH (inchangé V2)
    ├── NUTRITION COACH (étendu V3 — EA central)
    ├── RECOVERY COACH (étendu V3 — veto élargi)
    └── ENERGY COACH (nouveau V3 — charge allostatique + hormones)
```

## 2.2 Recovery Coach V3 — Veto élargi

**V2 :** Veto basé sur HRV (RMSSD) + ACWR.

**V3 :** Veto basé sur HRV + ACWR + **Energy Availability (EA)** + **Allostatic Score** + **Phase du cycle menstruel** (si applicable).

Seuils de veto V3 :
- 🟢 Vert : HRV normal + ACWR 0.8-1.3 + EA > 45 kcal/kg FFM + Allostatic Score < 60
- 🟡 Jaune : Un indicateur hors zone → intensité réduite -15%
- 🔴 Rouge : Deux indicateurs hors zone OU EA < 30 kcal/kg FFM → séance bloquée

## 2.3 Nutrition Coach V3 — EA comme métrique centrale

**V2 :** Macros périodisées par type de jour, timing péri-workout, hydratation.

**V3 :** Tout ce qui précède + **calcul EA quotidien** comme métrique de santé prioritaire. Le Nutrition Coach alerte le Recovery Coach si EA < 30 kcal/kg FFM.

---

# 3. ENERGY COACH — ARCHITECTURE COMPLÈTE

## 3.1 Rôle

L'Energy Coach est le **spécialiste de la charge de vie totale**. Il ne prescrit pas de workouts. Il modélise la fatigue invisible — cognitive, professionnelle, hormonale — et la traduit en un **Allostatic Score** normalisé (0-100) que le Head Coach intègre dans ses décisions.

## 3.2 Concept : Charge Allostatique

La charge allostatique = l'accumulation de stress biologique de toutes sources combinées.

**Sources modélisées :**
- Stress professionnel (type de journée : bureau léger / bureau intense / travail physique / télétravail)
- Charge cognitive (réunions, présentations, décisions importantes)
- Charge émotionnelle (événements de vie déclarés)
- Qualité et durée du sommeil (Apple Health)
- Récupération autonomique (HRV/RMSSD)
- Phase du cycle menstruel (si applicable)
- Nutrition insuffisante (EA < 30 kcal/kg FFM)

**Règle fondatrice :**
```
Allostatic Score = Σ (poids_source × valeur_normalisée_source) / total_poids
```

Seuils :
- 0-40 : Charge légère → entraînement normal
- 41-60 : Charge modérée → vérifier ACWR avant séance intense
- 61-80 : Charge élevée → réduire intensité -15%, pas de PR attempts
- 81-100 : Charge critique → séance légère seulement (Z1/Z2 ou technique)

## 3.3 Input utilisateur

L'Energy Coach collecte ses données de deux façons :

**Automatique (Apple Health + intégrations) :**
- Sommeil : durée, phases, efficacité
- HRV matinal (RMSSD)
- FC repos
- Pas (proxy d'activité globale)

**Manuel (check-in quotidien — max 60 secondes) :**
```
Questions du check-in quotidien :
1. "Comment s'est passée ta journée de travail ?" 
   → Légère / Normale / Intense / Épuisante
2. "As-tu eu des facteurs de stress importants aujourd'hui ?"
   → Non / Oui, léger / Oui, significatif
3. "Phase de cycle ?" (si profil féminin activé)
   → Menstruelle / Folliculaire / Ovulation / Lutéale
```

## 3.4 Skills de l'Energy Coach

| Skill | Input | Output |
|-------|-------|--------|
| `calculate_allostatic_score` | HRV, sommeil, check-in, cycle | Score 0-100 + composantes |
| `assess_cognitive_load` | Type de journée, check-in | Score cognitif 0-100 |
| `calculate_energy_availability` | Apport calorique, EAT | EA kcal/kg FFM |
| `predict_recovery_capacity` | Score allostatic + historique | Capacité de récup % |
| `generate_energy_report` | Toutes sources | Rapport hebdo pour Head Coach |

## 3.5 Intégration avec les autres agents

L'Energy Coach produit un `EnergySnapshot` qui est attaché à l'`AthleteState` :

```python
class EnergySnapshot(BaseModel):
    timestamp: datetime
    allostatic_score: float          # 0-100
    cognitive_load: float            # 0-100
    energy_availability: float       # kcal/kg FFM
    cycle_phase: Optional[str]       # "follicular" | "ovulation" | "luteal" | "menstrual"
    sleep_quality: float             # 0-100
    recommended_intensity_cap: float # % de l'intensité normale (ex: 0.85 = -15%)
    veto_triggered: bool             # True si EA < 30 ou score > 80
    veto_reason: Optional[str]       # Explication si veto
```

---

# 4. CYCLE HORMONAL FÉMININ — INTÉGRATION TRANSVERSALE

## 4.1 Principe

Le cycle menstruel influence directement les variables que Resilio+ modélise déjà. L'intégrer correctement fait de Resilio+ un outil réellement personnalisé pour les femmes — aucun concurrent ne le fait au niveau de prescription exacte.

**Aucun outil mainstream (TrainingPeaks, Whoop, Garmin Coach) ne modélise ceci au niveau de la prescription exacte.** C'est le deuxième différenciateur commercial majeur de la V3.

## 4.2 Les 4 phases et leur impact sur l'entraînement

### Phase Menstruelle (Jours 1-5)
**Physiologie :** Estrogène et progestérone au plus bas. Prostaglandines élevées (crampes, inflammation).

**Impact entraînement :**
- Force maximale légèrement réduite (-5 à -10%)
- Tolérance à la douleur réduite
- Fatigue perçue augmentée
- Récupération ralentie

**Ajustements Resilio+ :**
- Lifting Coach : RPE cible réduit de 1 point, pas de 1RM attempts
- Running Coach : Remplacer les fractionnés intensifs par Z2 si douleurs importantes
- Recovery Coach : Seuil veto 🔴 abaissé à 40% (au lieu de 50%)
- Nutrition Coach : Augmenter fer (viande rouge, épinards), magnésium, oméga-3

### Phase Folliculaire (Jours 6-13)
**Physiologie :** Estrogène en hausse. Sensibilité à l'insuline améliorée. Récupération optimale.

**Impact entraînement :**
- Phase optimale pour les gains de force
- Tolérance à la charge d'entraînement maximale
- Récupération la plus rapide du cycle
- Humeur et énergie en hausse

**Ajustements Resilio+ :**
- Lifting Coach : Semaine idéale pour PR attempts et sessions lourdes
- Running Coach : Fractionnés à haute intensité — timing optimal
- Recovery Coach : Seuils normaux ou légèrement assouplis
- Nutrition Coach : Glucides modérés OK, sensibilité insuline favorise le stockage glycogène

### Phase Ovulatoire (Jours 14-15)
**Physiologie :** Pic d'estrogène + LH. Force maximale absolue du cycle. Risque accru de blessure ligamentaire (laxité ligamentaire liée à l'estrogène).

**Impact entraînement :**
- Force et puissance au maximum
- Risque de blessure ACL et ligaments augmenté

**Ajustements Resilio+ :**
- Lifting Coach : Maximiser performance, mais insister sur la technique (pas de fatigue technique)
- Running Coach : Éviter les changements de direction brusques et terrains instables
- Recovery Coach : Note de risque ligamentaire ajoutée aux recommandations
- Nutrition Coach : Maintenir hydratation optimale (rétention d'eau possible)

### Phase Lutéale (Jours 16-28)
**Physiologie :** Progestérone élevée. Température basale +0.3-0.5°C. Catabolisme musculaire augmenté. Rétention d'eau possible. Syndrome prémenstruel (SPM) variable.

**Impact entraînement :**
- Force réduite progressivement (-5 à -15% en fin de phase)
- Besoin en protéines augmenté (catabolisme accru)
- Thermorégulation moins efficace (chaleur)
- Fatigue et irritabilité possibles

**Ajustements Resilio+ :**
- Lifting Coach : Volume maintenu, intensité réduite progressivement, RPE cible -1 en fin de phase
- Running Coach : Hydratation augmentée, éviter les séances dans la chaleur
- Recovery Coach : Augmenter vigilance sur signes de surentraînement
- Nutrition Coach : Protéines +0.2g/kg/jour, calories légèrement augmentées (+200 kcal), fer et magnésium

## 4.3 Input et tracking

**Sources de données :**
- Déclaration manuelle via check-in quotidien (Energy Coach)
- Apple Health (si cycle tracking activé — Cycle Tracking app)
- Déclaration du jour 1 des règles pour recalibrer automatiquement

**Profil hormonal dans AthleteState :**
```python
class HormonalProfile(BaseModel):
    enabled: bool                    # False si non applicable ou non souhaité
    cycle_length_days: int           # Durée moyenne du cycle (défaut: 28)
    current_cycle_day: Optional[int] # Jour actuel dans le cycle
    current_phase: Optional[str]     # "menstrual" | "follicular" | "ovulation" | "luteal"
    last_period_start: Optional[date]
    tracking_source: str             # "manual" | "apple_health"
    notes: Optional[str]             # Notes personnelles (SPM sévère, cycle irrégulier, etc.)
```

---

# 5. CHARGE ALLOSTATIQUE — MODÉLISATION DÉTAILLÉE

## 5.1 Pourquoi la charge cognitive compte

La recherche montre que la fatigue cognitive augmente le RPE perçu pour une même charge physique. Un athlète qui sort d'une journée de travail intense à 6h RPE ressent 7-8 RPE. Le Recovery Coach de la V2 ne voit pas ça — il voit seulement le HRV et l'ACWR.

**Sources scientifiques :**
- Mental fatigue impairs physical performance (Marcora et al., 2009)
- Cognitive fatigue and sport performance (Pageaux & Lepers, 2018)
- Allostatic load and athletic performance (PMC — multiples études)

## 5.2 Modèle de calcul

```python
def calculate_allostatic_score(
    hrv_deviation: float,       # % déviation vs baseline (négatif = pire)
    sleep_quality: float,       # 0-100
    work_intensity: str,        # "light" | "normal" | "heavy" | "exhausting"
    stress_level: str,          # "none" | "mild" | "significant"
    cycle_phase: Optional[str], # Impact spécifique par phase
    ea_status: str,             # "adequate" | "low" | "critical"
) -> float:
    
    # Poids des composantes
    weights = {
        "hrv": 0.30,
        "sleep": 0.25,
        "work": 0.20,
        "stress": 0.15,
        "cycle": 0.05,
        "ea": 0.05
    }
    
    # Scores normalisés 0-100 (100 = charge maximale)
    scores = {
        "hrv": max(0, -hrv_deviation * 2),  # -15% HRV = score 30
        "sleep": 100 - sleep_quality,
        "work": {"light": 10, "normal": 30, "heavy": 65, "exhausting": 90}[work_intensity],
        "stress": {"none": 0, "mild": 30, "significant": 70}[stress_level],
        "cycle": {"menstrual": 40, "follicular": 10, "ovulation": 15, "luteal": 35}.get(cycle_phase, 20),
        "ea": {"adequate": 0, "low": 40, "critical": 80}[ea_status]
    }
    
    return sum(weights[k] * scores[k] for k in weights)
```

## 5.3 Impact sur la prescription

| Allostatic Score | Action Head Coach |
|------------------|-------------------|
| 0-40 | Plan normal |
| 41-60 | Avertissement affiché, plan inchangé |
| 61-80 | Intensité -15%, durée -10%, note au user |
| 81-100 | Séance légère seulement (Z1/Z2 ou technique) |
| + EA critique | Veto automatique indépendamment du score |

---

# 6. ENERGY AVAILABILITY (EA) — SEUILS ET VETO

## 6.1 Formule

```
EA = (Apport calorique − EAT) / kg FFM

EAT = Énergie dépensée à l'entraînement (kcal)
FFM = Fat-Free Mass (masse maigre en kg)
```

## 6.2 Seuils cliniques

| EA | Statut | Action |
|----|--------|--------|
| > 45 kcal/kg FFM | Optimal | Aucune action |
| 30-45 kcal/kg FFM | Sous-optimal | Alerte Nutrition Coach |
| < 30 kcal/kg FFM | Critique (femmes) | Veto Recovery Coach + alerte |
| < 25 kcal/kg FFM | Critique (hommes) | Veto Recovery Coach + alerte |

## 6.3 RED-S (Relative Energy Deficiency in Sport)

La V3 intègre le cadre RED-S (anciennement "Female Athlete Triad") comme protocole d'alerte :

**Signaux RED-S à détecter :**
- EA < seuil pendant 3 jours consécutifs
- Perte de poids > 0.5kg/semaine non intentionnelle
- HRV en déclin persistant (>5 jours)
- Trouble du sommeil persistant

**Action :**
- Alerte dans l'interface utilisateur (non alarmiste)
- Réduction automatique de la charge d'entraînement
- Recommandation de consulter un professionnel de santé (non automatique, suggéré seulement)

## 6.4 Calcul dans le workflow

Le Nutrition Coach calcule l'EA **en temps réel** après chaque synchronisation :
1. Pull de l'apport calorique du jour (USDA/OFF/FCÉN + déclaration manuelle)
2. Pull de l'énergie dépensée à l'entraînement (Strava + Hevy)
3. Calcul EA → push vers `AthleteState.energy_snapshot.energy_availability`
4. Si EA < seuil → notification Recovery Coach → décision veto

---

# 7. ATHLETESTATE V3 — NOUVEAUX CHAMPS

## 7.1 Additions à l'objet AthleteState

```python
class AthleteStateV3(AthleteState):  # Hérite de V2
    
    # Nouveaux champs V3
    energy_snapshot: Optional[EnergySnapshot]      # Snapshot Energy Coach
    hormonal_profile: Optional[HormonalProfile]    # Profil cycle menstruel
    allostatic_history: List[AllostaticEntry]       # Historique 28 jours
    
    # Champs étendus V3
    recovery_coach_veto: RecoveryVetoV3            # Veto élargi (inclut EA + allostatic)

class AllostaticEntry(BaseModel):
    date: date
    allostatic_score: float
    components: dict                    # Détail des composantes
    intensity_cap_applied: float        # Cap réellement appliqué

class RecoveryVetoV3(BaseModel):
    status: str                         # "green" | "yellow" | "red"
    hrv_component: str                  # Statut HRV
    acwr_component: str                 # Statut ACWR
    ea_component: str                   # Statut EA (nouveau V3)
    allostatic_component: str           # Statut allostatic (nouveau V3)
    cycle_component: Optional[str]      # Statut cycle (nouveau V3)
    final_intensity_cap: float          # Cap final (pire des composantes)
    veto_triggered: bool
    veto_reasons: List[str]
```

## 7.2 get_agent_view() V3

```python
def get_agent_view(agent: str) -> dict:
    views = {
        "head_coach": "FULL",           # Accès complet incluant V3
        "energy_coach": [               # Nouveau V3
            "energy_snapshot",
            "hormonal_profile", 
            "allostatic_history",
            "sleep_data",
            "nutrition_summary"
        ],
        "recovery_coach": [             # Étendu V3
            "hrv_data",
            "sleep_data", 
            "acwr",
            "energy_snapshot",          # Nouveau V3
            "hormonal_profile",         # Nouveau V3
            "fatigue_snapshots"
        ],
        "nutrition_coach": [            # Étendu V3
            "nutrition_profile",
            "training_today",
            "energy_snapshot",          # EA en temps réel
            "hormonal_profile",         # Besoins nutritionnels par phase
            "body_composition"
        ],
        # Autres agents inchangés vs V2
    }
```

---

# 8. DIFFÉRENCIATEURS COMMERCIAUX V3

## 8.1 Ce que personne d'autre ne fait

| Différenciateur | Resilio+ V3 | TrainingPeaks | Whoop | Garmin Coach |
|-----------------|-------------|---------------|-------|--------------|
| Charge allostatique | ✅ Modélisée + prescriptive | ❌ | ❌ | ❌ |
| Cycle hormonal → prescription | ✅ Par phase | ❌ | ⚠️ Tracking seulement | ❌ |
| Energy Availability (EA) | ✅ Calcul quotidien + veto | ❌ | ❌ | ❌ |
| Hybride multi-sport | ✅ Natif | ⚠️ Partiel | ❌ | ⚠️ Partiel |
| Prescriptions exactes (non vagues) | ✅ Natif V2 | ⚠️ Variable | ❌ | ⚠️ Variable |

## 8.2 Utilisateur cible V3

**Profil principal :** Athlète hybride sérieux (3-8 séances/semaine, 2+ sports), avec une vie professionnelle active, qui veut une optimisation réelle — pas des recommandations génériques.

**Profil secondaire :** Femme athlète sérieuse qui en a marre que son plan ignore son cycle.

**Ne pas cibler :** L'athlète casual (2 séances/semaine, pas d'objectif précis). Le message précis pour un créneau étroit convertit infiniment mieux qu'un message large.

---

# 9. PLAN D'EXÉCUTION SUPERPOWERS V3

## 9.1 Prérequis avant de lancer

- [ ] V2 complète, stable, et tous les tests passent
- [ ] Branche `v3` créée depuis `main`
- [ ] Ce document dans `docs/resilio-v3-master.md`
- [ ] CLAUDE.md mis à jour avec les décisions V3 via `/revise-claude-md`

## 9.2 Sessions V3

| # | Module | Focus | Livrable |
|---|--------|-------|----------|
| V3-1 | AthleteState V3 | Nouveaux champs + get_agent_view() étendu + migrations Alembic | `models/athlete_state_v3.py` |
| V3-2 | Energy Coach | Agent complet + 5 skills + check-in quotidien | `agents/energy_coach/` |
| V3-3 | Cycle hormonal | HormonalProfile + ajustements par phase dans tous les agents | `core/hormonal.py` + patches agents |
| V3-4 | EA + RED-S | Calcul EA temps réel + alertes + veto Recovery Coach étendu | `core/energy_availability.py` |
| V3-5 | Allostatic Score | Calcul + historique + impact sur prescription | `core/allostatic.py` |
| V3-6 | Recovery Coach V3 | Veto élargi intégrant tous les nouveaux signaux | Patch `agents/recovery_coach/` |
| V3-7 | Frontend V3 | Dashboard énergie + check-in quotidien + vue cycle | `frontend/app/energy/` |
| V3-8 | Tests + polish | Tests E2E V3 + documentation | `tests/v3/` |

## 9.3 Protocole par session

```
/superpowers:brainstorm
[Coller le contexte de la session depuis ce document]
→ Valider le spec
/superpowers:write-plan
→ Valider le plan
/superpowers:execute-plan
→ À la fin : /revise-claude-md
```

---

*Document créé le 2026-04-10. Version finale pour lancement V3 après completion V2.*
*Ne pas modifier CLAUDE.md avec ce contenu avant la fin de V2.*
