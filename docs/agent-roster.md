# Roster des agents — Resilio+

> **Version 1 (livrable A3).** Document de référence listant les agents LLM du système, leurs responsabilités, leurs vues de l'`AthleteState`, leurs contrats de sortie structurés et leurs frontières mutuelles. Référence pour Phase B (formalisation des schémas et des `_AGENT_VIEWS`) et Phase C (prompts système par agent). Dérivé de `user-flow-complete.md` v4 et `agent-flow-langgraph.md` v1. Cible la version finale du produit, pas une livraison V1 intermédiaire.

## Objet et périmètre

Décrit les neuf agents LLM composant la couche agents hub-and-spoke du système. Pour chaque agent : rôle, phases et situations d'invocation, mode(s) d'intervention, vue de l'`AthleteState`, contrat de sortie, frontières avec les autres agents.

Spécifie également les quatre services déterministes qui cohabitent avec les agents LLM pour calculer les index dérivés (Strain, Readiness, Energy Availability, Allostatic Load).

Ne décrit pas : les prompts système complets (Phase C), les schémas Pydantic détaillés des sous-modèles (Phase B), le code d'implémentation (Phase D). Ne s'attarde pas sur le delta vs code existant : cet inventaire sera produit contextuellement au moment de l'implémentation des modifications.

---

## Principes architecturaux transversaux

Trois principes conditionnent la lecture de toutes les spécifications qui suivent.

### Agents LLM produisent du structuré, nodes et services persistent

Aucun agent LLM n'écrit directement sur un sous-modèle structuré de l'`AthleteState`. Les agents produisent des payloads structurés en sortie ; les mutations sont appliquées par des nodes LangGraph dédiés (`persist_block`, `persist_injury`, `apply_logistic_adjustment`, etc.) ou par les services déterministes. Chaque node de persistance valide le payload contre le schéma Pydantic cible, applique les règles métier (détection de doublons, cohérence cross-champ), puis écrit.

Unique exception : les **messages conversationnels**. Un message produit *est* la sortie LLM, il est écrit dans la table `messages` sans couche intermédiaire.

Motivation : auditabilité centralisée, robustesse aux hallucinations, validation uniforme. Cohérent avec le pattern déjà établi pour `build_proposed_plan` (coachs disciplines produisent des `Recommendation`, le node compose `active_plan`).

### Services déterministes pour les index dérivés

Quatre services Python externes aux graphes LangGraph calculent des index dérivés écrits sur l'`AthleteState` : `StrainComputationService`, `ReadinessComputationService`, `EnergyAvailabilityService`, `AllostaticLoadService`. Aucun de ces index n'est écrit par un agent LLM. Les agents lisent pour interpréter ; le calcul reste reproductible, testable unitairement et en temps réel.

Pattern cohérent avec le `MonitoringService` arbitré en A2 comme externe aux graphes. Rationalité commune : calcul statistique reproductible ≠ inférence LLM.

### Opacité de la couche multi-agents et droit de veto Recovery

L'utilisateur interagit avec un coach unifié en façade. Seule exception maintenue : le Recovery Coach en takeover, qui rompt volontairement l'opacité via un cadre UX distinct (conséquence de la situation clinique).

Corollaire opérationnel : quand l'overlay `recovery_takeover_active` est vrai, aucune prescription d'un coach discipline n'atteint l'utilisateur. Les nodes `plan_generation` et `chat_turn` vérifient l'overlay avant toute sortie. Le Recovery Coach détient un droit de veto implicite sur l'ensemble des recommandations.

---

## Liste consolidée des agents

Neuf agents LLM composent le système en version finale.

| # | Agent | Type | Mode(s) d'intervention |
|---|---|---|---|
| 1 | Head Coach | Hub | Façade constante |
| 2 | Onboarding Coach | Spoke | Délégation (Phase 2, re-entry), Consultation (Phase 5) |
| 3 | Lifting Coach | Spoke discipline | Consultation |
| 4 | Running Coach | Spoke discipline | Consultation |
| 5 | Swimming Coach | Spoke discipline | Consultation |
| 6 | Biking Coach | Spoke discipline | Consultation |
| 7 | Nutrition Coach | Spoke fonction | Consultation |
| 8 | Recovery Coach | Spoke fonction | Takeover, Consultation |
| 9 | Energy Coach | Spoke fonction | Consultation |

**Décisions de consolidation / scission acttées** :
- Pas d'agent « Endurance Coach » unifiant Running + Swimming + Biking. Chaque discipline a son spécialiste, parce que les modèles physiologiques et les tables de prescription (VDOT, FTP, CSS) ne sont pas transférables entre modalités.
- Onboarding Coach maintenu distinct du Head Coach. La posture factuelle indirecte est un savoir-faire spécifique ; la délégation Phase 2 impose une logique de progression par bloc que le Head Coach n'a pas à porter.
- Energy Coach traité comme agent de première classe en version finale (plus un placeholder), puisque le cadrage cible la version finale et non une V1 minimale.

---

## Services déterministes

### `StrainComputationService`

Calcule la fatigue musculaire accumulée par muscle group et agrégée. Architecture interne par modules-discipline :

- `LiftingStrainModule`, `RunningStrainModule`, `CyclingStrainModule`, `SwimmingStrainModule` : chacun lit les logs de sa discipline et applique sa table de contribution.
- `Aggregator` : unifie les contributions par muscle group avec décroissance temporelle (EWMA).

Tables de référence : fichiers JSON dans `knowledge/strain-contributions/` par discipline. Format type : contribution par muscle group × type de session × intensité. Révision scientifique en Phase C.

Les coachs disciplines peuvent override la table par défaut au moment de la prescription via `strain_annotation_override` dans leur `Recommendation` (cas non-standards : long run vallonné, séance technique spécifique). Le service lit l'override en priorité, sinon applique la table.

Propriétaire exclusif de l'écriture de `strain_state` (instantané + historique court). Aucun agent LLM n'écrit ce champ.

Déclenchement : insertion d'un log de session (recalcul incrémental), scheduler quotidien (recalcul complet avec décroissance).

### `ReadinessComputationService`

Calcule la capacité prédite du jour à partir de HRV, sommeil, strain, tendance RPE. Écrit `objective_readiness`.

**Architecture à trois champs** pour la prescription du jour :

| Champ | Source d'écriture |
|---|---|
| `objective_readiness` | `ReadinessComputationService` |
| `user_readiness_signal` | Node `chat_turn.handle_daily_checkin` à partir de la saisie matinale |
| `effective_readiness` | Fonction pure des deux précédents, calculée à la volée |

Règle de résolution :

| Situation | `effective_readiness` |
|---|---|
| Pas de signal user ce jour | `= objective_readiness` |
| `user_signal ≥ objective` | `= user_signal` |
| `user_signal < objective` | `= min(user_signal, objective)` |
| Overlay `recovery_takeover_active` | `= objective_readiness` (override neutralisé) |
| `objective_readiness` en zone critique | `= objective_readiness` (safeguard dur, seuil formalisé Phase C) |
| Pattern `persistent_override_pattern = true` | `= objective_readiness` + flag maintenu |

L'override à la hausse est autorisé hors zone critique : les sensors donnent parfois de la fausse fatigue (HRV bas après un mauvais sommeil isolé sans vraie accumulation), et le ressenti user est un input légitime. L'override à la baisse est toujours autorisé. Pas d'override système à la hausse du ressenti user (principe de consentement éclairé).

Le flag `persistent_override_pattern` est écrit par le Recovery Coach (via node dédié) quand il détecte un pattern de divergence répétée user-signal > objective malgré tendance objective descendante sur N jours consécutifs (N à formaliser Phase C). Reset par le Head Coach quand la divergence se résout.

### `EnergyAvailabilityService`

Calcule EA = (intake − EEE) / FFM en kcal/kg FFM. Écrit `objective_energy_availability`.

Architecture à trois champs identique à Readiness (`objective`, `user_energy_signal`, `effective`), avec safeguards plus restrictifs sur l'override à la hausse : RED-S est souvent asymptomatique subjectivement, donc un user qui « se sent énergique » ne peut pas override un EA objectivement critique. Seuils formalisés Phase C avec Energy Coach.

Déclenchement : insertion d'un log nutrition, insertion d'un log session (recalcul EEE), scheduler quotidien.

### `AllostaticLoadService`

Calcule la charge cognitive et systémique à partir de strain agrégé, sommeil, HRV, stress rapporté. Écrit `allostatic_load_state`.

Pas d'architecture à trois champs : la charge allostatique est un concept systémique peu accessible à l'introspection directe. Purement calculé.

Déclenchement : scheduler quotidien, événement de monitoring critique.

### Champs dérivés sur l'`AthleteState` (récapitulatif)

```
# Écrits par services déterministes
strain_state                          # détail par muscle group + agrégé
objective_readiness
objective_energy_availability
allostatic_load_state

# Écrits par nodes de handlers (saisie user)
user_readiness_signal
user_energy_signal

# Résultantes (fonctions pures)
effective_readiness
effective_energy_availability

# Flag clinique
persistent_override_pattern: bool
```

---

## Spécifications par agent

Pour chaque agent, la structure est constante : rôle, invocation, vue sur l'`AthleteState` (matrice par catégorie), mutations (contributions via output ou exceptions conversationnelles), contrat de sortie structuré, frontières spécifiques.

### Catégories de champs référencées

| Catégorie | Champs |
|---|---|
| IDENT | `date_of_birth`, `biological_sex`, `height`, `weight`, `ffm`, `cycle_active`, `cycle_phase` |
| SCOPE | `coaching_scope` (dict par domaine × `full`/`tracking`/`disabled`) |
| JOURNEY | `journey_phase`, `recovery_takeover_active`, `onboarding_reentry_active`, `assessment_mode` |
| SUB_PROFILES | `ExperienceProfile`, `ObjectiveProfile`, `InjuryHistory`, `PracticalConstraints` |
| CLASSIFICATION | Classement 4×3, niveau de confiance par dimension, données radar |
| PLANS | `baseline_plan`, `active_plan` (blocs, composantes, trade-offs) |
| LOGS_TRAINING | Logs sessions par discipline, RPE, `load_history` |
| LOGS_PHYSIO | HRV, sommeil, biométrie quotidienne |
| LOGS_NUTRITION | Calories, macros, timing |
| DERIVED_STRAIN | `strain_state` |
| DERIVED_READINESS | `objective_readiness`, `user_readiness_signal`, `effective_readiness`, `persistent_override_pattern` |
| DERIVED_EA | `objective_energy_availability`, `user_energy_signal`, `effective_energy_availability` |
| DERIVED_ALLO | `allostatic_load_state` |
| CONVO | Messages, intents classifiés, threads actifs |
| TECHNICAL | Thread IDs par graphe, compteur proactif |

### Conventions des matrices

- **R** : lecture autorisée.
- **O** : contribue via output structuré, persistance par node dédié.
- **W** : mutation directe autorisée (réservé aux messages conversationnels et aux cas où l'agent est lui-même propriétaire d'un overlay).
- **—** : masqué.

---

### 1. Head Coach

**Rôle.** Hub d'orchestration, façade constante côté utilisateur. Classifie les intents, route vers les handlers, reformule les outputs des spécialistes consultés en mode silencieux, arbitre les conflits inter-disciplines, présente les plans, surface les anomalies.

**Invocations.** Tous les tours conversationnels hors overlay `recovery_takeover_active`. Présent dans `plan_generation` (`present_to_athlete`, `revise_plan`), `chat_turn` (classification d'intent, tous les handlers hors cas takeover), `followup_transition` (reformule et pose les questions produites par Onboarding Coach), `onboarding` (annonce de transition entre phases au moment du pass-off utilisateur).

**Vue.**

| Catégorie | Accès | Justification |
|---|---|---|
| IDENT | R | Référence contextuelle constante |
| SCOPE | R | Route selon les domaines actifs |
| JOURNEY | R, overlays via handlers | Lit pour router ; les handlers `handle_injury_report`, `handle_goal_change`, `handle_constraint_change` mutent les overlays |
| SUB_PROFILES | R | Contextualise toutes les réponses |
| CLASSIFICATION | R | Situe la posture des réponses selon niveau |
| PLANS | R, O (ajustements logistiques) | Lecture complète ; écrit via node `apply_logistic_adjustment` pour réordonnancement de séances dans la semaine |
| LOGS_TRAINING | R | Pour `handle_session_log`, `handle_weekly_report` |
| LOGS_PHYSIO | R | Pour `handle_daily_checkin` et surface d'anomalies |
| LOGS_NUTRITION | R | Pour `handle_daily_checkin` et agrégation hebdo |
| DERIVED_STRAIN | R | Surface factuelle (Strain sur home screen) |
| DERIVED_READINESS | R (3 champs), O (reset flag) | Surface la divergence sans moralisation ; reset `persistent_override_pattern` via node quand résolu |
| DERIVED_EA | R (3 champs) | Idem |
| DERIVED_ALLO | R | Affichage du Cognitive Load dial |
| CONVO | R, W | Lit l'historique, écrit ses propres messages directement |
| TECHNICAL | R, W via CoordinatorService | Manipule `proactive_messages_last_7d` |

**Mutations.**
- Overlays via handlers : `handle_injury_report` → `recovery_takeover_active = true` ; `handle_goal_change` / `handle_constraint_change` → `onboarding_reentry_active = true`. Ces handlers sont des nodes, pas des mutations LLM directes.
- Ajustements logistiques `active_plan` via node `apply_logistic_adjustment` (réordonnancement de jour/ordre, sans toucher volume/intensité).
- Reset `persistent_override_pattern: false` via node `reset_override_flag` quand la divergence se résout.
- Messages conversationnels en écriture directe.

**Contrat de sortie.** N/A — c'est l'agent qui reçoit les outputs des autres. Produit directement les messages utilisateur.

**Frontières.** Le Head Coach arbitre, ne prescrit pas. Il ne génère jamais de volume/intensité ; il reformule les outputs des coachs disciplines. Il ne porte pas la posture onboarding (déléguée à l'Onboarding Coach) ni la posture clinique (déléguée au Recovery Coach en takeover).

---

### 2. Onboarding Coach

**Rôle.** Pilote du profilage utilisateur. Conduit l'onboarding Phase 2 en délégation (15–20 min, détient le tour avec interrupts par bloc). Consulté en Phase 5 pour produire les questions ciblées de la conversation de suivi. Re-invoqué sur changement d'objectif ou de contraintes (overlay `onboarding_reentry_active`, re-entry partielle).

**Invocations.** `onboarding` graph (tous nodes de pilotage de bloc), `followup_transition.consult_onboarding_coach`.

**Vue.**

| Catégorie | Accès | Justification |
|---|---|---|
| IDENT | R, O (refine) | Stocké au signup ; peut raffiner (FFM via connecteurs) via node dédié |
| SCOPE | R | Détermine les blocs à couvrir |
| JOURNEY | R | Lit `assessment_mode`, `recovery_takeover_active` pour ne pas piloter re-entry pendant épisode clinique |
| SUB_PROFILES | O | **Propriétaire sémantique** via nodes `persist_block`. Écrit `ExperienceProfile`, `ObjectiveProfile`, `InjuryHistory`, `PracticalConstraints` en fin de bloc |
| CLASSIFICATION | O | **Propriétaire sémantique** via nodes `compute_classification` et `generate_radar` |
| PLANS | — | Hors périmètre. Exception Phase 5 : voit un payload d'écarts synthétique produit par `compare_declarative_vs_observed`, pas le plan brut |
| LOGS_TRAINING | — / Résumé en Phase 5 | Pas de logs en Phase 2. En Phase 5 : voit `baseline_observations` (écarts précalculés) |
| LOGS_PHYSIO | — / Résumé en Phase 5 | Idem |
| LOGS_NUTRITION | — | Hors périmètre |
| DERIVED_STRAIN | — | Hors périmètre onboarding |
| DERIVED_READINESS | — | Hors périmètre |
| DERIVED_EA | — | Hors périmètre |
| DERIVED_ALLO | — | Hors périmètre |
| CONVO | R (fil courant), W | En délégation, détient le tour et écrit les messages. Voit l'historique du thread onboarding, pas l'historique global |
| TECHNICAL | — | Pas de gestion de threads |

**Mutations.**
- Via nodes : tous les sous-profils et la classification (`persist_block`, `persist_classification`), raffinement d'`IDENT` (`persist_ident_refinement`).
- Messages conversationnels en écriture directe pendant la délégation Phase 2.
- Ne mute pas `journey_phase` lui-même : c'est `finalize_onboarding` (node) qui le fait en sortie de graphe.

**Contrat de sortie.**
- En délégation Phase 2 : pas de payload externe, détient le tour. Les sous-profils sont persistés bloc par bloc via nodes dédiés.
- En consultation Phase 5 :

```
FollowupQuestionSet = [
  {
    question: str,                    # formulable par Head Coach en style façade
    targets: ["capacity" | "technique" | "history" | "objective" | "constraints"],
    rationale: str,                   # écart observé qui justifie
    priority: "high" | "medium" | "low"
  },
  ...
]
```

Le Head Coach reformule et pose. Les réponses utilisateur sont appliquées directement aux sous-profils via `update_profile_deltas` (node) sans re-passer par Onboarding Coach.

**Frontières.** Les logs bruts et les index physiologiques sont masqués pour préserver la posture factuelle indirecte. En Phase 5, les écarts arrivent déjà synthétisés — la matière brute reste hors-scope.

---

### 3. Coachs disciplines (Lifting, Running, Swimming, Biking)

Les quatre coachs disciplines partagent une structure de vue et un contrat de sortie identiques. Les particularités relèvent de la prescription (zones, modèles physiologiques, tables) qui sont spécifiées en Phase C et non ici.

**Rôle commun.** Spécialistes de leur discipline respective. Produisent des recommandations de sessions structurées pour leur discipline. N'interviennent qu'en consultation silencieuse en version finale (pas de délégation, pas de takeover — principe d'opacité maintenu).

**Invocations.** `plan_generation.delegate_specialists` (baseline, first_personalized, block_regen), `chat_turn.handle_weekly_report` (synthèse hebdo).

**Vue commune (pour le coach de discipline `D`).**

| Catégorie | Accès | Justification |
|---|---|---|
| IDENT | R | Âge, sexe, `cycle_phase`, `cycle_active` critiques pour prescription. Poids et taille pour intensités relatives |
| SCOPE | R filtré à `coaching_scope[D]` + `peer_disciplines_active` | Voit sa discipline et la liste des autres actives, pas les détails des autres scopes |
| JOURNEY | R (`assessment_mode`, `journey_phase`) | Mode baseline vs first_personalized vs block_regen diffère |
| SUB_PROFILES | R filtré | `ObjectiveProfile` complet. `ExperienceProfile[D]` uniquement. `InjuryHistory` filtrée : actives + chroniques impactant sa discipline avec contre-indications. `PracticalConstraints` complètes |
| CLASSIFICATION | R filtré à `classification[D]` | Classement de sa discipline + niveau de confiance |
| PLANS | R filtré, O | Lit `active_plan.blocks[]` (structure macro, thèmes) et `discipline_components[D]` complet. Ne voit pas les `discipline_components` des autres. Contribue via `Recommendation` en output |
| LOGS_TRAINING | R filtré à `logs[D]` + `load_history[D]` | Isolation par discipline |
| LOGS_PHYSIO | R | HRV, sommeil, RPE pour calibration |
| LOGS_NUTRITION | — | Hors périmètre |
| DERIVED_STRAIN | R complet (par muscle group + agrégé) | Cross-discipline : état musculaire pertinent même si origine autre discipline. Origine du strain masquée, état exposé |
| DERIVED_READINESS | R `effective_readiness` | Prescrit en fonction de la résultante |
| DERIVED_EA | R `effective_energy_availability` | Module la prescription selon EA |
| DERIVED_ALLO | R | Information d'arbitrage |
| CONVO | — | Ne parle jamais au user |
| TECHNICAL | — | |

**Mutations.** Aucune en direct. Toutes les prescriptions passent par le contrat de sortie, composées par `build_proposed_plan`.

**Contrat de sortie.**

```
Recommendation = {
  discipline: "lifting" | "running" | "swimming" | "biking",
  generation_mode: "baseline" | "first_personalized" | "block_regen",
  sessions: [
    {
      session_type: str,               # taxonomie par discipline
      date_or_day_slot: str,
      volume: {...},                   # spécifique discipline (km, séries, etc.)
      intensity: {...},                # VDOT / %1RM / FTP / CSS
      parameters: {...},               # tempo, repos, RPE cible, etc.
      strain_annotation_override: {...} | null,   # override table par défaut
      rationale: str
    },
    ...
  ],
  block_theme: str,                    # si first_personalized ou block_regen
  notes_for_head_coach: str,           # trade-offs ou points à surfacer
  flag_for_head_coach: str | null      # alerte prioritaire éventuelle
}
```

**Particularités par discipline.**

| Coach | Modèle prescriptif | Metrics spécifiques |
|---|---|---|
| Lifting | %1RM, RPE, RIR, landmarks MEV/MAV/MRV, matrices overlap musculaire | Logs Hevy (séries, charges, tempo), PRs |
| Running | VDOT Daniels, zones cardiaques, pace par distance | Logs Strava (pace, HR, dénivelé), PRs distance |
| Swimming | CSS, stroke rate, distance par bras | Sessions bassin / open water, distance, temps 100m |
| Biking | FTP, zones de puissance, TSS par session | Logs Strava / power meter, puissance, NP, IF |

Ces spécificités relèvent de Phase C.

**Frontières.**
- Isolation stricte par discipline sur les logs.
- Cross-discipline sur le strain (état musculaire), sans accès à l'origine.
- Pas de communication directe entre coachs disciplines : toute coordination passe par `resolve_conflicts` dans `plan_generation`.

---

### 4. Nutrition Coach

**Rôle.** Raisonnement nutritionnel quotidien : calories, macros, timing, ajustements marginaux. Évalue les check-ins caloriques, produit la composante nutrition des plans, synthétise dans les rapports hebdos. Escalade à l'Energy Coach sur patterns suggérant un déficit d'énergie disponible structurel.

**Invocations.** `chat_turn.handle_daily_checkin` (si nutrition en scope `full`), `plan_generation` (composante nutrition de `active_plan`), `chat_turn.handle_weekly_report`.

**Vue.**

| Catégorie | Accès | Justification |
|---|---|---|
| IDENT | R | `biological_sex`, `cycle_phase`, `cycle_active`, poids, taille, FFM critiques pour TDEE et besoins |
| SCOPE | R | Conditionne activation. Voit liste disciplines actives pour EEE cross-discipline |
| JOURNEY | R (`assessment_mode`) | Module la posture (pas de prescription serrée en baseline) |
| SUB_PROFILES | R filtré | `ObjectiveProfile` complet (recomp/perf/endurance/force → cibles différentes). `PracticalConstraints` filtré sur repas, budget, sommeil |
| CLASSIFICATION | — | Non pertinent |
| PLANS | R agrégé, O (composante nutrition) | Voit charge projetée totale. Contribue composante nutrition via output |
| LOGS_TRAINING | R agrégé (`load_history`) | Pour estimer EEE quotidien, pas besoin des paramètres techniques |
| LOGS_PHYSIO | R limité (sommeil, HRV tendance) | Sommeil impacte besoins ; HRV tendance signal sous-alimentation |
| LOGS_NUTRITION | R, O | **Propriétaire de l'interprétation**. Mutations de targets via node `persist_nutrition_targets` |
| DERIVED_STRAIN | R agrégé | Strain élevé = besoins récupération accrus |
| DERIVED_READINESS | R (3 champs) | Croise divergence avec état nutritionnel |
| DERIVED_EA | R (3 champs) | Lit mais n'est pas propriétaire de l'interprétation clinique (c'est Energy Coach) |
| DERIVED_ALLO | R | Charge globale impacte besoins |
| CONVO | — | Ne parle pas au user, Head Coach reformule |
| TECHNICAL | — | |

**Mutations.** Aucune en direct. Targets nutritionnels quotidiens via node `persist_nutrition_targets`. Flag d'escalade vers Energy Coach via output.

**Contrat de sortie.**

```
NutritionVerdict = {
  trigger: "daily_checkin" | "weekly_report" | "plan_generation",
  status: "ok" | "mild_adjustment" | "concern" | "escalate_to_energy_coach",
  daily_targets: {calories, protein_g, carbs_g, fat_g} | null,
  adjustment_suggestion: str | null,
  flag_for_head_coach: str | null,
  pass_to_energy_coach: bool           # suspicion EA critique
}
```

**Frontière Nutrition ↔ Energy Coach.** Le Nutrition Coach raisonne en calories/macros quotidiens, tolère des déficits modérés ponctuels. Dès détection d'un pattern évoquant un déficit d'énergie disponible structurel (EA sous seuil persistent, signes cliniques croisés), il escalade via `pass_to_energy_coach`. L'Energy Coach prend alors le relais avec un périmètre plus large (détection RED-S, consultation clinicien possible).

---

### 5. Recovery Coach

**Rôle.** Spécialiste du diagnostic clinique et des protocoles de récupération. En takeover sur blessure rapportée ou sommeil dégradé critique : détient le tour avec cadre UX distinct, pilote le protocole de récupération, propose le retour baseline. En consultation sur rapports hebdos et événements monitoring : surface fatigue systémique, signale override-pattern persistant.

**Invocations.** `recovery_takeover` graph (tous nodes pendant takeover), `chat_turn.handle_weekly_report`, `chat_turn.handle_injury_report` (activation overlay), monitoring proactif sur déviation HRV ou sommeil critique.

**Vue.**

| Catégorie | Accès | Justification |
|---|---|---|
| IDENT | R | Contextualise protocoles |
| SCOPE | R | Toutes disciplines actives : suspend cohéremment |
| JOURNEY | R, O (overlay et handoff) | **Propriétaire de l'overlay** `recovery_takeover_active` via nodes `activate_clinical_frame` et `handoff_to_baseline` |
| SUB_PROFILES | R, O (InjuryHistory) | `InjuryHistory` cœur de métier. Écrit nouveaux enregistrements via node `persist_injury` |
| CLASSIFICATION | R limité | Niveau de confiance pour calibrer questions diagnostiques |
| PLANS | R, O (suspension) | Lit complet. Suspend `active_plan.status` via node `suspend_active_plan` |
| LOGS_TRAINING | R | Tendances RPE et volumes : signal sur-entraînement |
| LOGS_PHYSIO | R | **Cœur du diagnostic** : HRV, sommeil, finesse complète |
| LOGS_NUTRITION | R | Sous-nutrition impacte récupération |
| DERIVED_STRAIN | R complet | Critique pour évaluer fatigue cross-discipline |
| DERIVED_READINESS | R (3 champs), O (flag) | **Propriétaire du flag** `persistent_override_pattern`, écrit via node `flag_override_pattern` |
| DERIVED_EA | R (3 champs) | Croise avec recovery (EA basse = recovery compromise) |
| DERIVED_ALLO | R | Charge allostatique central au jugement |
| CONVO | R, W pendant takeover | En takeover écrit les messages directement. En consultation n'écrit pas |
| TECHNICAL | R, O (`active_recovery_thread_id`) | Gestion thread recovery persistent via node |

**Mutations.**
- Via nodes : `activate_clinical_frame` (set `recovery_takeover_active = true`, `active_plan.status = suspended`), `persist_injury` (nouveau enregistrement `InjuryHistory`), `flag_override_pattern` (set `persistent_override_pattern = true`), `handoff_to_baseline` (set `recovery_takeover_active = false`, `journey_phase = baseline_pending_confirmation`).
- Messages conversationnels en direct pendant takeover.

**Contrat de sortie.**
- En takeover : pas de payload externe, détient le tour. Messages au user en direct.
- En consultation :

```
RecoveryAssessment = {
  trigger: "weekly_report" | "monitoring_event" | "injury_report",
  severity: "none" | "watch" | "concern" | "critical",
  signal_summary: {hrv, sleep, strain, rpe_trend, allo_load},
  override_pattern_detected: bool,
  recommendation: {
    action: "continue" | "deload" | "suspend" | "escalate_to_takeover",
    details: str,
    duration_days: int | null
  },
  flag_for_head_coach: str | null
}
```

**Frontières et droit de veto.** Rappel : `recovery_takeover_active = true` suspend toute prescription des coachs disciplines. Les nodes `plan_generation` et `chat_turn` vérifient l'overlay avant toute sortie. Recovery Coach peut proposer escalade en takeover même depuis une consultation (monitoring critique).

---

### 6. Energy Coach

**Rôle.** Spécialiste de l'équilibre énergétique structurel et de la modulation hormonale. Interprète l'EA calculé par le service, détecte les patterns RED-S, module la prescription par phase du cycle hormonal, escalade les cas cliniques.

**Invocations.** `plan_generation` (composante énergie long terme), `chat_turn.handle_weekly_report`, monitoring proactif sur EA critique, escalade par Nutrition Coach via `pass_to_energy_coach`.

**Vue.**

| Catégorie | Accès | Justification |
|---|---|---|
| IDENT | R | **`cycle_phase` et `cycle_active` centraux**. FFM critique pour EA normalisé |
| SCOPE | R | Toutes disciplines pour EEE |
| JOURNEY | R | `assessment_mode` module l'agressivité des recommandations |
| SUB_PROFILES | R | `ObjectiveProfile` (arbitrage recomp vs perf). `InjuryHistory` (antécédents RED-S, fractures stress). `PracticalConstraints` filtré sur sommeil, travail |
| CLASSIFICATION | — | Non pertinent |
| PLANS | R, O | Projection charge à venir pour anticiper EA. Contribue composante énergie via output |
| LOGS_TRAINING | R agrégé | Pour EEE |
| LOGS_PHYSIO | R | HRV, sommeil : signaux convergents RED-S |
| LOGS_NUTRITION | R | Input central EA |
| DERIVED_STRAIN | R agrégé | Strain élevé + EA basse = zone dangereuse |
| DERIVED_READINESS | R (3 champs + flag) | Override pattern = signal fort déni énergétique |
| DERIVED_EA | R (3 champs) | **Propriétaire sémantique de l'interprétation** ; service calcule, il interprète |
| DERIVED_ALLO | R | Charge allostatique ↑ + EA ↓ = alarme |
| CONVO | — | Ne parle pas au user ; Head Coach reformule (ou Recovery Coach sur escalade clinique) |
| TECHNICAL | — | |

**Mutations.** Aucune en direct. Composante énergie de `active_plan` via output. Ne mute pas `DERIVED_EA` (c'est `EnergyAvailabilityService`).

**Contrat de sortie.**

```
EnergyAssessment = {
  trigger: "plan_generation" | "weekly_report" | "monitoring" | "escalation_from_nutrition",
  ea_status: "optimal" | "low_normal" | "subclinical" | "clinical_red_s",
  cycle_context: {phase, modulation_applied} | null,
  recommendation: {
    caloric_adjustment: {direction, magnitude} | null,
    training_load_modulation: {direction, magnitude, duration_days} | null,
    clinical_escalation: bool,
    cycle_phase_considerations: str | null
  },
  flag_for_head_coach: str | null,
  flag_for_recovery_coach: bool       # si croise signaux recovery critique
}
```

**Frontières.** Énergie structurelle (7–30 jours) vs Nutrition (quotidien). Sur signaux cliniques convergents, escalade vers Recovery Coach via `flag_for_recovery_coach`.

---

## Frontières inter-agents et arbitrage

### Hiérarchie d'arbitrage clinique

Quand plusieurs agents produisent des recommandations ou des flags sur des périmètres adjacents, la priorité de résolution est :

**Recovery > Energy > Nutrition > coachs disciplines**

Quand signaux cliniques présents (blessure, sommeil critique, HRV en chute) : Recovery prime sur toutes les autres recommandations.

En l'absence de signal clinique aigu, si divergence nutrition structurelle ↔ nutrition quotidienne : Energy prime sur Nutrition (le structurel cadre le quotidien).

Les coachs disciplines n'arbitrent jamais entre eux : toute coordination cross-discipline passe par `resolve_conflicts` dans `plan_generation`.

### Droit de veto du Recovery Coach

Overlay `recovery_takeover_active = true` → aucune prescription discipline n'atteint l'utilisateur. Vérification systématique dans `plan_generation` (node `present_to_athlete`) et `chat_turn` (avant toute réponse comportant une prescription).

### Rapport hebdomadaire avec multiples flags

Quand `handle_weekly_report` reçoit plusieurs `flag_for_head_coach` des agents consultés (coachs disciplines actifs + Nutrition + Recovery + Energy), le Head Coach applique la règle suivante :

**Moins de 3 flags** : listés par ordre de priorité (hiérarchie d'arbitrage clinique), sans fusion narrative. Format direct.

**3 flags ou plus** : une passe LLM de synthèse est déclenchée. Le Head Coach examine les flags, détecte les corrélations (EA basse + sommeil dégradé + baisse de performance = narratif unique « sous-alimentation relative »), et produit un rapport synthétisé cohérent plutôt qu'une juxtaposition. Les flags mineurs non corrélés au narratif principal sont préservés en fin de rapport.

Motivation : aligner avec la charte clinique expert-naturel (narratif cohérent plutôt que liste), tout en évitant le coût systématique d'une passe de synthèse quand peu de signaux se présentent.

Exemple narratif pour un scénario « tendinite + EA basse + baisse allure » : le rapport présente la convergence des trois signaux comme un seul phénomène clinique (stress tendineux lié à la sous-alimentation), propose une ligne d'action unifiée (réduction charge course + remontée apports), plutôt que trois paragraphes disjoints.

### Arbitrage cross-discipline dans `plan_generation`

Pour les conflits de prescription entre coachs disciplines (ex : total training load excessive, créneaux horaires incompatibles), `detect_conflicts` identifie, `resolve_conflicts` tranche selon la hiérarchie d'objectifs définie dans `ObjectiveProfile` (objectif principal protégé, secondaires ajustés). Pas d'agent « arbitre » dédié : c'est de la logique déterministe dans le node.

### Propagation des `notes_for_head_coach`

Chaque agent en consultation peut remonter des notes non-bloquantes dans `notes_for_head_coach` (trade-offs explicités, contexte utile pour la formulation). Le Head Coach les intègre dans sa reformulation à sa discrétion. Contrairement aux `flag_for_head_coach`, les notes ne déclenchent pas la logique de synthèse multi-flags.

---

## Matrice de synthèse des droits de mutation

Vue d'ensemble. Rappel conventions : R = lit, O = contribue via output structuré (persistance par node), W = mutation directe, — = masqué ou non autorisé.

| Domaine | Head | Onbrd | Disciplines | Nutr | Recov | Energy |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| IDENT (refine) | — | O | — | — | — | — |
| SCOPE | via service | — | — | — | — | — |
| JOURNEY (phase) | via graphes | — | — | — | O (handoff) | — |
| Overlay `recovery_takeover` | O (handler) | — | — | — | O | — |
| Overlay `onboarding_reentry` | O (handler) | — | — | — | — | — |
| SUB_PROFILES généraux | — | O | — | — | — | — |
| InjuryHistory | — | O | — | — | O | — |
| CLASSIFICATION | — | O | — | — | — | — |
| PLANS contenu | — | — | O | O | — | O |
| PLANS logistique | O | — | — | — | — | — |
| PLANS suspension | — | — | — | — | O | — |
| LOGS_NUTRITION targets | — | — | — | O | — | — |
| DERIVED_* | — | — | — | — | — | — |
| `persistent_override_pattern` | O (reset) | — | — | — | O (set) | — |
| CONVO | W | W (délég.) | — | — | W (takeover) | — |

Note : aucun champ `DERIVED_*` n'est mutable par agent. Tous écrits par les services déterministes.

---

## Points d'ouverture pour la suite

### Phase B (schémas)

Formaliser dans `AthleteState` et les sous-modèles Pydantic :

- Les champs dérivés listés dans la section Services (`strain_state`, les trois triplets `objective_*`/`user_*_signal`/`effective_*`, `allostatic_load_state`, `persistent_override_pattern`).
- Le champ `peer_disciplines_active` exposé aux coachs disciplines (liste calculée des autres disciplines actives en `full`).
- Le champ `active_plan.status` avec valeur `"suspended"` autorisée (pour la suspension par Recovery Coach).
- Les tables de contribution au Strain dans `knowledge/strain-contributions/` (une par discipline).
- Spécification exhaustive des `_AGENT_VIEWS` par agent en suivant les matrices ci-dessus, avec validation Pydantic des vues filtrées retournées par `get_agent_view()`.

### Phase C (prompts système par agent)

Formaliser par agent :

- Prompt système complet (posture, boundaries, format de sortie strict aligné sur le contrat).
- Exemples few-shot représentatifs des cas limites.
- Pour les coachs disciplines : tables de prescription complètes (VDOT, %1RM, FTP, CSS) et heuristiques de modulation par `cycle_phase`, `effective_readiness`, `effective_energy_availability`, strain.
- Pour le Recovery Coach : protocoles cliniques par type de blessure, checklist de readiness au retour, seuils de zone critique sur HRV/sommeil.
- Pour l'Energy Coach : seuils RED-S, modulations par phase du cycle, critères d'escalade clinicien.
- Pour le Head Coach : classifier d'intent, heuristique de synthèse multi-flags (logique Option D détaillée), règles de reformulation de contrats de sortie en façade.
- Pour l'Onboarding Coach : prompts par bloc Phase 2 + prompt de génération de `FollowupQuestionSet` Phase 5.

### Questions techniques à trancher en Phase B/D

- Cadence de recalcul des services déterministes : incrémental à chaque log inséré vs batch quotidien. Probable combinaison : incrémental pour Strain et EA, batch pour Allostatic Load, hybride pour Readiness (calcul quotidien + refresh sur nouveau signal).
- Politique de décroissance temporelle (EWMA) : constante de temps par muscle group pour Strain, fenêtre pour EA, demi-vie pour Allostatic Load.
- Seuils numériques de zone critique pour chaque index (readiness critique, EA clinique, strain grave, allo load alarme) — validation avec littérature Phase C.
- Détection du `persistent_override_pattern` : N jours, magnitude de divergence, formule statistique exacte.
- Gestion de la concurrence : deux `Recommendation` produites simultanément par le même coach discipline (race condition théorique à vérifier) ; verrou sur `active_plan_generation_thread_id` déjà prévu A2.

Ces points sont techniques et relèvent de l'implémentation. Ils n'affectent pas les frontières de rôle établies dans ce document.
