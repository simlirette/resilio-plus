# RESILIO — Section Nutrition Coach (à ajouter au document maître après la section 6)

> Insérer cette section dans `resilio-master-v2.md` entre le Lifting Coach (section 6) et les Formats de Sortie (section 7).
> Remplace FatSecret par USDA + Open Food Facts + FCÉN comme sources de données.

---

# 6B. NUTRITION COACH — Connaissances Complètes & Output Exact

## 6B.1 Rôle
Le Nutrition Coach est le "pôle création d'énergie" du système. Il prescrit des plans nutritionnels EXACTS : macros quotidiennes ajustées par type de journée, timing des repas autour des entraînements, hydratation par séance, et protocoles péri-compétition. Il ne fonctionne PAS en vase clos : il reçoit le plan d'entraînement VALIDÉ du Head Coach avant de prescrire.

## 6B.2 Architecture Nutrition — Sources de Données (remplace FatSecret)

### 3 couches de données alimentaires :

| Source | Type | Couverture | API/Accès | Usage |
|--------|------|------------|-----------|-------|
| **USDA FoodData Central** | Gouvernementale | Aliments bruts (viande, légumes, céréales) | API REST gratuite (`api.nal.usda.gov`) | Référence scientifique, macros + micros détaillés |
| **Fichier canadien (FCÉN)** | Gouvernementale | Produits canadiens | Téléchargement CSV/XML (Santé Canada) | Marché local Québec/Canada |
| **Open Food Facts** | Collaborative | Produits commerciaux avec codes-barres (3M+ produits) | API REST gratuite (`world.openfoodfacts.org/api`) | Produits transformés, scan de codes-barres |

### Input en langage naturel
L'utilisateur tape ou dicte :
```
"2 oeufs, toast au beurre de peanut, café avec lait"
```

Claude parse ça en entités (aliment + quantité estimée), matche avec USDA/FCÉN/OFF, et retourne :
```json
{
  "meal_log": {
    "timestamp": "2026-04-01T07:30:00",
    "meal_type": "breakfast",
    "items": [
      {"food": "Egg, large, scrambled", "source": "USDA", "qty_g": 100, "kcal": 149, "protein_g": 10.6, "carbs_g": 1.6, "fat_g": 11.2},
      {"food": "Bread, whole wheat, toasted", "source": "FCEN", "qty_g": 30, "kcal": 79, "protein_g": 3.6, "carbs_g": 13.8, "fat_g": 1.1},
      {"food": "Peanut butter, smooth", "source": "USDA", "qty_g": 16, "kcal": 94, "protein_g": 3.6, "carbs_g": 3.6, "fat_g": 8.0},
      {"food": "Coffee with 2% milk", "source": "USDA", "qty_g": 250, "kcal": 25, "protein_g": 1.7, "carbs_g": 2.5, "fat_g": 1.0}
    ],
    "totals": {"kcal": 347, "protein_g": 19.5, "carbs_g": 21.5, "fat_g": 21.3}
  }
}
```

### Validation croisée des données (détection d'incohérences)
L'agent DOIT vérifier quotidiennement :
- Si kcal logués < 60% du TDEE → "Est-ce que tu as oublié de logger un repas ?"
- Si kcal logués > 150% du TDEE sans journée d'entraînement double → "Vérifie tes quantités"
- Si protéines < 1.2g/kg → alerte déficit protéique
- Si glucides < 3g/kg un jour d'entraînement intense → alerte carburant insuffisant

## 6B.3 Connaissances Fondamentales

### Calcul du TDEE (Dépense Énergétique Totale)
```python
# Mifflin-St Jeor (le plus précis pour population générale)
if sex == "M":
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
else:
    bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

# Multiplicateur d'activité
activity_multipliers = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extremely_active": 1.9
}

tdee = bmr * activity_multipliers[activity_level]
# Ajustement dynamique : +300-500kcal les jours d'entraînement double
```

### Périodisation Nutritionnelle par Type de Journée

| Type de journée | Glucides (g/kg) | Protéines (g/kg) | Lipides (g/kg) | Notes |
|----------------|-----------------|-------------------|-----------------|-------|
| **Jour de repos** | 3-4 | 1.6-2.0 | 1.0-1.2 | Aliments entiers, haute densité micronutritionnelle |
| **Jour lifting seul** | 4-5 | 1.8-2.2 | 0.8-1.0 | Protéines réparties en 4-5 prises de 30-40g |
| **Jour course facile (<60min)** | 4-5 | 1.6-2.0 | 0.8-1.0 | Pas de nutrition intra-effort |
| **Jour course longue (>90min)** | 6-8 | 1.6-2.0 | 0.8-1.0 | Nutrition intra-effort OBLIGATOIRE |
| **Jour course intense (intervalles/tempo)** | 5-7 | 1.6-2.0 | 0.8-1.0 | Glucides 2-3h avant, fenêtre post-effort |
| **Jour double (lift + course)** | 6-8 | 2.0-2.2 | 0.8-1.0 | Séparation des repas entre les séances |
| **Jour pré-compétition** | 8-10 | 1.6 | 0.6-0.8 | Carb loading, fibres réduites, lipides réduits |

### Timing Nutritionnel (Fenêtres Critiques)

**Pré-entraînement (2-3h avant) :**
- 1-2g/kg glucides, faible en fibres et lipides
- 20-30g protéines
- Ex concret : "Bol de riz blanc (200g) + poulet grillé (120g) + banane"

**Intra-effort (pendant l'exercice) :**
| Durée de l'effort | Glucides/heure | Format |
|-------------------|----------------|--------|
| < 60 min | 0 (eau suffit) | Eau |
| 60-90 min | 30g | Boisson sportive ou 1 gel |
| 90-150 min | 30-60g | Gels + boisson isotonique |
| > 150 min | 60-90g (ratio glucose:fructose 2:1) | Mix gels + boisson + solides |

**Post-entraînement (fenêtre 30-60 min) :**
- 0.8-1.2g/kg glucides à indice glycémique élevé
- 0.3-0.4g/kg protéines (whey ou aliments rapides)
- Ratio glucides:protéines 3:1 ou 4:1
- Ex concret : "Smoothie : 1 banane + 300ml lait + 1 scoop whey + 2 c.s. miel"

**Récupération express (<4h entre 2 sessions) :**
- 1.2g/kg/heure de glucides à IG élevé immédiatement après la 1ère session
- 0.3g/kg protéines
- Continuer les glucides jusqu'à la prochaine session

**Pré-sommeil :**
- 30-40g caséine (protéine à digestion lente)
- Augmente la MPS nocturne sans inhiber la lipolyse
- Ex concret : "250g fromage cottage (quark) + 15g beurre d'amande"

### Hydratation

**Quotidien :**
- Baseline : 35-40ml/kg de poids corporel/jour
- Ex pour 78kg : 2.7-3.1L/jour (hors entraînement)

**Pré-exercice (2-4h avant) :**
- 5-7ml/kg (390-546ml pour 78kg)

**Pendant l'effort :**
- 400-800ml/heure selon température et sudation
- Sodium : 500-1000mg/L dans les boissons pour efforts >60min
- Indicateur simple : uriner avant la séance, couleur paille clair = hydraté

**Post-exercice :**
- 1.5L par kg de poids perdu pendant l'effort
- Ajouter sodium si sudation importante

### Supplémentation — Niveau A d'Évidence Uniquement

| Supplément | Dose | Timing | Bénéfice prouvé | Précautions |
|------------|------|--------|-----------------|-------------|
| **Créatine monohydrate** | 3-5g/jour | N'importe quand (pas de timing critique) | ↑ Puissance, ↑ récupération, ↑ masse maigre | Prise de poids hydrique initiale 1-2kg |
| **Caféine** | 3-6mg/kg | 30-60min pré-effort | ↑ Endurance, ↑ puissance, ↓ RPE | Pas après 14h si sommeil sensible |
| **Beta-alanine** | 3.2-6.4g/jour (doses fractionnées) | Chronique (4+ semaines) | Tamponne acidité pour efforts 1-10min | Picotements (paresthésie) = normal |
| **Nitrate (jus betterave)** | 6-8mmol (500ml jus) | 2-3h pré-effort | ↑ Économie de course 1-3% | Efficacité réduite chez élite |
| **Vitamine D** | 1000-2000 UI/jour | Avec un repas gras | Santé osseuse, immunitaire (si déficient) | Doser la 25(OH)D d'abord |
| **Oméga-3 (EPA+DHA)** | 2-4g/jour | Avec un repas | ↓ Inflammation post-effort concurrent | Éviter doses >5g |
| **Fer** | Selon prescription | Avec vitamine C, sans café/thé | Si ferritine <30ng/mL | UNIQUEMENT sur diagnostic de carence |

### Entraînement Gastro-Intestinal (Gut Training)

**Concept critique** : pour tolérer 60-90g glucides/heure en course, le système digestif doit être entraîné progressivement.

**Protocole (6-8 semaines pré-compétition) :**
- Semaine 1-2 : 20-30g glucides/heure pendant les sorties longues
- Semaine 3-4 : 30-45g/heure
- Semaine 5-6 : 45-60g/heure
- Semaine 7-8 : 60-90g/heure (ratio glucose:fructose 2:1)
- Tester le MÊME produit que le jour de la course (gels, boisson, etc.)
- Ne jamais tester un nouveau produit le jour de la compétition

### Race-Week Nutrition Protocol

**J-7 à J-3 : Phase normale**
- Maintenir les macros habituelles
- Hydratation normale
- Réduire les fibres progressivement

**J-2 et J-1 : Carb Loading**
- 10-12g/kg glucides/jour
- Sources : riz blanc, pâtes blanches, pain blanc, jus de fruits, miel
- Réduire les lipides à 0.5-0.6g/kg (pour faire de la place aux glucides)
- Réduire les fibres au minimum (<15g/jour)
- Protéines maintenues à 1.4-1.6g/kg
- Hydratation augmentée : +500ml vs normal

**Jour J : Matin de la course**
- 2-4h avant le départ : 1-4g/kg glucides
- Faible en fibres, faible en lipides, aliments testés
- Ex concret : "Bagel blanc avec confiture + banane + café"
- Dernière gorgée d'eau 15-20min avant le départ

## 6B.4 Système de Notifications Proactives (3 niveaux)

### Niveau 1 : Pré-entraînement (2-3h avant la séance)
Déclenché automatiquement quand une séance est planifiée.

```json
{
  "notification": {
    "type": "pre_workout",
    "trigger": "session_scheduled_in_2h",
    "session": "Intervals VO2max — Jeudi 18h",
    "message": "Tu as des intervalles ce soir. Assure-toi d'avoir mangé au moins 1-1.5g/kg de glucides dans les 2-3 dernières heures. Ex: 100g de riz + source de protéines.",
    "priority_macros": ["carbs"],
    "target_carbs_g": 117,
    "hydration_reminder": "500ml d'eau d'ici la séance"
  }
}
```

### Niveau 2 : Post-entraînement (fenêtre 30-60min)
Déclenché quand la séance est marquée comme complétée dans Strava/Hevy.

```json
{
  "notification": {
    "type": "post_workout",
    "trigger": "session_completed",
    "session": "Upper A — Force — Lundi",
    "message": "Ta séance de force est terminée. Priorise 30-40g de protéines + 0.8g/kg de glucides dans la prochaine heure. Ex: Smoothie whey + banane + lait.",
    "priority_macros": ["protein", "carbs"],
    "target_protein_g": 35,
    "target_carbs_g": 62,
    "window_minutes": 60
  }
}
```

### Niveau 3 : Prévention de déficit (quotidien, fin de journée)
Déclenché le soir si le bilan est insuffisant pour la séance du lendemain.

```json
{
  "notification": {
    "type": "deficit_alert",
    "trigger": "daily_review_20h",
    "tomorrow_session": "Long Run 14km — Samedi matin",
    "message": "Tu as un long run de 14km demain matin et tu es en déficit de 400kcal aujourd'hui, dont 80g de glucides manquants. Ajoute une collation riche en glucides ce soir. Ex: Bol de céréales avec lait ou toast avec miel et banane.",
    "current_vs_target": {
      "kcal": {"consumed": 2100, "target": 2500, "deficit": -400},
      "carbs_g": {"consumed": 280, "target": 360, "deficit": -80}
    }
  }
}
```

## 6B.5 Skills du Nutrition Coach (7 skills)

| Skill | Input | Output | Fallback |
|-------|-------|--------|----------|
| `search_food_database` | text query ou barcode | JSON food item (macros, micros) | Recherche dans cache local |
| `log_meal_nlp` | texte libre ("2 oeufs, toast...") | JSON meal_log avec macros calculées | Demander détail par item |
| `calculate_daily_targets` | athlete_state, training_plan_today | JSON macros cibles du jour | Template par type de jour |
| `generate_meal_plan` | macros_target, preferences, restrictions | JSON plan repas avec recettes | — |
| `plan_race_nutrition` | event_type, event_date, athlete_state | JSON protocole J-7 à Jour J | — |
| `calculate_hydration` | weight, session_type, temperature | JSON ml/h + sodium + timing | Formule standard |
| `evaluate_compliance` | meal_logs_7days, targets | JSON adhérence + alertes + recommandations | — |

## 6B.6 Format de Sortie — Plan Nutritionnel Journalier

```json
{
  "daily_nutrition_plan": {
    "date": "2026-04-06",
    "day_type": "lifting_and_easy_run",
    "training_sessions": [
      {"time": "07:00", "type": "lifting_upper_force", "duration_min": 55},
      {"time": "18:00", "type": "easy_run", "duration_min": 40}
    ],

    "targets": {
      "kcal": 2850,
      "protein_g": 156,
      "carbs_g": 390,
      "fat_g": 78,
      "water_ml": 3500,
      "fiber_g": 30
    },

    "meals": [
      {
        "time": "06:00",
        "label": "Pré-lifting",
        "items": ["Overnight oats (80g flocons + 200ml lait + 1 banane + 15g beurre d'amande)"],
        "macros": {"kcal": 520, "protein_g": 22, "carbs_g": 75, "fat_g": 16}
      },
      {
        "time": "08:15",
        "label": "Post-lifting (fenêtre 30min)",
        "items": ["Smoothie : 1 scoop whey (30g) + 300ml lait + 1 banane + 2 c.s. miel"],
        "macros": {"kcal": 450, "protein_g": 38, "carbs_g": 68, "fat_g": 5}
      },
      {
        "time": "12:00",
        "label": "Lunch",
        "items": ["200g poulet grillé + 250g riz + légumes sautés + 1 c.s. huile olive"],
        "macros": {"kcal": 680, "protein_g": 52, "carbs_g": 78, "fat_g": 18}
      },
      {
        "time": "15:30",
        "label": "Collation pré-run",
        "items": ["Bagel blanc + confiture (30g) + 1 banane"],
        "macros": {"kcal": 380, "protein_g": 10, "carbs_g": 78, "fat_g": 3}
      },
      {
        "time": "19:00",
        "label": "Dinner (post-run)",
        "items": ["150g saumon + 200g patates douces + salade verte + vinaigrette"],
        "macros": {"kcal": 580, "protein_g": 38, "carbs_g": 55, "fat_g": 24}
      },
      {
        "time": "21:30",
        "label": "Pré-sommeil",
        "items": ["250g fromage cottage + 15g beurre d'amande + 10g miel"],
        "macros": {"kcal": 280, "protein_g": 32, "carbs_g": 18, "fat_g": 12}
      }
    ],

    "hydration_plan": {
      "baseline_ml": 3100,
      "pre_lifting_ml": 400,
      "during_run_ml": 300,
      "post_run_ml": 500,
      "total_target_ml": 3500
    },

    "supplements": [
      {"name": "Créatine monohydrate", "dose": "5g", "timing": "avec le lunch"},
      {"name": "Oméga-3", "dose": "2g EPA+DHA", "timing": "avec le dinner"},
      {"name": "Vitamine D", "dose": "2000 UI", "timing": "avec le lunch"}
    ],

    "coaching_notes": [
      "C'est une journée double (lift + run). L'apport en glucides est plus élevé que d'habitude pour supporter les deux séances.",
      "Le smoothie post-lifting est dans la fenêtre de 30min — ne le saute pas.",
      "La collation pré-run est faible en fibres et lipides pour éviter l'inconfort gastrique.",
      "La caséine du fromage cottage avant le sommeil optimise la récupération musculaire nocturne."
    ]
  }
}
```

---

# MISE À JOUR DES RÉFÉRENCES — Fichiers JSON existants dans le repo

Le document maître section 10 (Fichiers de Données JSON Requis) doit être mis à jour pour refléter les fichiers EXISTANTS dans `resilio_docs/resilio_docs/` :

| Fichier existant | Agent | Contenu |
|-----------------|-------|---------|
| `head_coach_acwr_rules.json` | Head Coach | Règles ACWR, prévention blessures, entraînement en force préventif |
| `head_coach_interference_rules.json` | Head Coach | Règles d'entraînement concurrent, interférence HIIT/résistance |
| `running_coach_tid_rules.json` | Running Coach | Distribution d'intensité polarisée/pyramidale |
| `lifting_coach_volume_rules.json` | Lifting Coach | Drop-sets, volume hebdomadaire, créatine, BFR, VBT |
| `biking_coach_power_rules.json` | Biking Coach | HIIT vs MVICT, bike fitting, caféine pour cyclisme |
| `swimming_coach_biomechanics_rules.json` | Swimming Coach | Drafting, coût énergétique en brasse |
| `nutrition_coach_fueling_rules.json` | Nutrition Coach | Glucides intra-effort, épargne glycogène, stratégies GI |
| `recovery_coach_hrv_rules.json` | Recovery Coach | HRV comme indicateur parasympathique, CWI, techniques de récupération |
| `recovery_coach_sleep_cns_rules.json` | Recovery Coach | Sommeil, extension pré-compétition, siestes tactiques |

### Fichiers ENCORE À CRÉER :

| Fichier | Contenu | Utilisé par |
|---------|---------|-------------|
| `data/vdot_paces.json` | Table VDOT complète (20-85) avec toutes les allures | Running Coach |
| `data/exercise_database.json` | 400+ exercices avec muscles, tier, SFR, Hevy IDs | Lifting Coach |
| `data/volume_landmarks.json` | MEV/MAV/MRV par muscle (standard + hybride) | Lifting Coach |
| `data/muscle_overlap.json` | Table chevauchement musculaire entre sports | Head Coach |
| `data/nutrition_targets.json` | Macros par type de jour (intégrées dans cette section) | Nutrition Coach |
| `data/running_zones.json` | Zones FC par modèle (Seiler 3-zone, Daniels 5-zone) | Running Coach |
| `data/food_database_cache.json` | Cache local des aliments fréquents (USDA + FCÉN) | Nutrition Coach |

### APIs alimentaires à intégrer (remplacent FatSecret) :

| API | URL | Clé requise | Usage |
|-----|-----|-------------|-------|
| USDA FoodData Central | `api.nal.usda.gov/fdc/v1/` | Gratuite (inscription) | Aliments bruts |
| Open Food Facts | `world.openfoodfacts.org/api/v2/` | Aucune | Produits commerciaux/codes-barres |
| FCÉN (Santé Canada) | Téléchargement CSV | Aucune | Marché canadien |

### Mise à jour de l'écosystème API (section 1.2 du maître) :

Remplacer :
```
| **FatSecret** | Nutrition détaillée (aliments, macros, micros) | OAuth2 REST |
```

Par :
```
| **USDA FoodData Central** | Aliments bruts, macros/micros détaillés | API REST gratuite |
| **Open Food Facts** | Produits commerciaux, codes-barres | API REST gratuite |
| **FCÉN (Santé Canada)** | Aliments canadiens | CSV téléchargeable |
```

### Mise à jour du Workflow (étape 7 du maître) :

L'étape 7 (Nutrition) doit maintenant inclure :
- `search_food_database` pour résoudre les entrées NLP
- `calculate_daily_targets` basé sur le plan d'entraînement validé
- `plan_race_nutrition` si un événement est dans les 8 semaines
- Notifications proactives 3 niveaux (pré/post/déficit)
- `calculate_hydration` par séance

### Mise à jour du plan d'exécution Superpowers :

Ajouter une **Session 14 : Nutrition Coach** :
```
/superpowers:brainstorm
```
**Contexte** : "Implémenter le Nutrition Coach complet. Sources de données : USDA FoodData Central API + Open Food Facts API + cache FCÉN local. Input en langage naturel (Claude parse les repas en entités). Plan nutritionnel journalier avec macros par type de jour, timing pré/intra/post effort, hydratation, suppléments. Système de notifications 3 niveaux (pré-workout, post-workout, déficit quotidien). Protocole race-week et entraînement gastro-intestinal. Voir la section 6B du document maître."
