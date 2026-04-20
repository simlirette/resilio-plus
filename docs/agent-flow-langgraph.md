# Flow agent et orchestration LangGraph — Resilio+

> **Version 1 (livrable A2).** Document de référence décrivant l'orchestration multi-agents et la topologie LangGraph du système. Référence pour Phase B (schémas), Phase C (agents individuels) et Phase D (implémentation backend). Dérivé de `user-flow-complete.md` v4 et du graphe `plan_generation` existant.

## Objet et périmètre

Ce document formalise l'orchestration des agents et la topologie LangGraph nécessaires pour exécuter le flow utilisateur défini en session A1. Il décrit :

1. Le modèle à deux couches séparant le pipeline LangGraph de la couche agent.
2. La topologie hub-and-spoke enrichie de la couche agent et ses trois modes d'intervention.
3. Le state machine macro `journey_phase` qui conditionne le routage.
4. L'architecture du service d'orchestration (`CoordinatorService`) et du service de monitoring.
5. Les cinq graphes LangGraph qui composent le système et leurs interactions.
6. Les points d'interruption human-in-the-loop, les transitions inter-graphes et les transitions souterraines entre agents.
7. Le delta par rapport au graphe `plan_generation` existant.

Ne décrit pas : les prompts système par agent (Phase C), les schémas détaillés des sous-modèles (Phase B), ni le code d'implémentation (Phase D).

---

## Modèle à deux couches

Le système opère à deux niveaux d'abstraction qu'il est critique de ne pas confondre.

### Couche pipeline LangGraph

LangGraph gère le **flow de contrôle** : nodes, edges conditionnels, interrupts HITL, checkpoints. Un graphe LangGraph est un pipeline avec entrée, sorties, points de pause, et state sérialisable. Les nodes peuvent invoquer des LLM, consulter la DB, transformer des données, mais ne sont pas eux-mêmes des « agents » au sens conversationnel.

Cette couche répond aux questions : *où en est-on dans le pipeline ? que doit-on exécuter ensuite ? doit-on pauser pour attendre un input humain ? comment reprendre ?*

### Couche agents (hub-and-spoke)

La couche agent gère **qui parle à qui côté LLM**. Le Head Coach est le hub et la façade utilisateur. Les spécialistes (Onboarding, Lifting, Running, Swimming, Biking, Nutrition, Recovery, Energy) sont les spokes. Cette topologie est conceptuelle ; elle se matérialise dans le code comme des appels LLM distincts avec des prompts système et des `_AGENT_VIEWS` de l'`AthleteState` différents.

Cette couche répond aux questions : *quel agent produit la réponse ? quel agent détient le tour conversationnel ? l'utilisateur voit-il le spécialiste ou seulement le Head Coach ?*

### Raison de la séparation

Un même node LangGraph peut invoquer zéro, un ou plusieurs agents selon le mode. Le node `delegate_specialists` du graphe `plan_generation` existant invoque plusieurs coachs disciplines en parallèle en mode consultation silencieuse. À l'inverse, plusieurs nodes peuvent être gérés par le même agent (l'Onboarding Coach pilote plusieurs nodes successifs du graphe onboarding). La correspondance node ↔ agent n'est pas biunivoque.

Dans la suite du document, « graphe » désigne toujours la couche pipeline LangGraph. « Agent » désigne toujours la couche LLM conversationnelle.

---

## Topologie de la couche agents

### Hub-and-spoke enrichi

**Hub.** Head Coach. Façade constante côté utilisateur par défaut. Point de routage des intents en chat, présentation des plans, surface des anomalies, arbitrage cross-discipline.

**Spokes.**
- Onboarding Coach.
- Lifting Coach.
- Running Coach.
- Swimming Coach.
- Biking Coach.
- Nutrition Coach.
- Recovery Coach.
- Energy Coach (V3).

### Trois modes d'intervention

Chaque appel d'un spoke par le hub s'inscrit dans l'un des trois modes suivants, qui diffèrent par qui détient le tour et par la visibilité façade.

| Mode | Propriétaire du tour | Visibilité façade | Structure LangGraph |
|---|---|---|---|
| **Consultation silencieuse** | Head Coach | Identité Head Coach uniquement | Node LangGraph qui invoque le spécialiste en parallèle ou en sous-routine, récupère un output structuré, puis Head Coach reformule |
| **Délégation sous-graphe** | Spécialiste | Identité coach unifié (nommage préservé) | Sous-graphe compilé qui détient le flow de contrôle pendant plusieurs tours, avec ses propres interrupts HITL |
| **Takeover explicite UX** | Spécialiste | Identité spécialiste visible, cadre visuel distinct | Sous-graphe compilé en overlay, mute un état overlay sur `AthleteState`, cadre façade change côté frontend |

### Mapping phase × mode × spoke

| Phase | Spoke invoqué | Mode | Note |
|---|---|---|---|
| 0 | — | — | Pas d'agent |
| 1 | — | — | Head Coach seul |
| 2 | Onboarding Coach | Délégation | Pilote 15–20 min, checkpoint par bloc |
| 3 | Coachs disciplines actifs | Consultation | Génération du plan baseline |
| 4 | Recovery Coach (conditionnel) | Takeover | Déclenché sur blessure |
| 5 | Onboarding Coach | Consultation | Génère les questions, Head Coach pose |
| 6 | Coachs disciplines actifs | Consultation | Génération du plan personnalisé |
| 6 | Onboarding Coach | Délégation | Si ajustement objectif/direction (overlay re-entry) |
| 7 | Coachs disciplines / Nutrition / Energy | Consultation | Régénération de bloc, check-ins, rapport hebdo |
| 7 | Recovery Coach | Takeover | Sur blessure ou sommeil dégradé persistant critique |
| 7 | Onboarding Coach | Délégation | Sur changement d'objectif ou de contraintes (overlay re-entry) |

Le Head Coach est présent dans toutes les phases. Les coachs disciplines sont presque toujours en consultation ; ils ne sont jamais en délégation ni en takeover en V1.

---

## État macro `journey_phase`

### Localisation

Porté par l'`AthleteState`. Lu par le `CoordinatorService` à chaque événement entrant pour décider quel graphe invoquer. Lu par le Head Coach à chaque tour de chat pour décider du routage interne.

### Valeurs principales (mutuellement exclusives)

| Valeur | Phase | Graphe actif |
|---|---|---|
| `signup` | 0 | Aucun (logique service) |
| `scope_selection` | 1 | Aucun (logique service) |
| `onboarding` | 2 | `onboarding` |
| `baseline_pending_confirmation` | 3 | `plan_generation` (mode baseline) |
| `baseline_active` | 4 | Aucun (monitoring actif) |
| `followup_transition` | 5 | `followup_transition` |
| `steady_state` | 6 post-confirmation + 7 | `plan_generation` (mode first ou bloc) + `chat_turn` |

### Overlays (booléens indépendants)

| Champ | Déclenché par | Effet |
|---|---|---|
| `recovery_takeover_active` | Blessure, sommeil dégradé critique, pause clinique | `recovery_takeover` graph actif, plan principal suspendu |
| `onboarding_reentry_active` | Changement d'objectif ou de contraintes | `onboarding` graph actif en mode partiel sur blocs concernés, plan principal maintenu |

### Règle de mutation

**Chaque graphe qui se termine mute `journey_phase` avant son node `END`.** Le `CoordinatorService` lit l'état post-graphe pour décider du routage suivant. Les graphes sont donc conscients du state machine macro mais le sont uniquement pour déclarer leur propre transition de sortie, pas pour décider la transition entière.

Exceptions à la règle :
- Les overlays sont mutés par l'événement déclencheur (détection blessure ouvre `recovery_takeover_active`, sortie du `recovery_takeover` graph ferme l'overlay).
- Le `chat_turn` graph ne mute pas `journey_phase` (il n'existe qu'en `steady_state`).

### Transitions valides

```
signup ──────────────▶ scope_selection
scope_selection ─────▶ onboarding        (si ≥ 1 domaine en "full")
onboarding ──────────▶ baseline_pending_confirmation
baseline_pending ────▶ baseline_active
baseline_active ─────▶ followup_transition   (conditions de sortie remplies)
baseline_active ─────▶ baseline_active       (pause courte, extension baseline)
baseline_active ─────▶ onboarding            (sous-compliance > 45j, re-onboarding partiel)
followup_transition ─▶ steady_state
steady_state ────────▶ baseline_pending      (interruption longue au-delà seuils)
steady_state ────────▶ steady_state          (tous tours chat + régénération bloc)
```

Les overlays peuvent s'activer depuis n'importe quel état principal à partir de `baseline_active`.

---

## Architecture `CoordinatorService`

### Rôle

Le `CoordinatorService` est le point d'entrée unique pour toute requête de l'utilisateur ou tout événement système. Il lit `journey_phase`, décide quel graphe invoquer, gère le thread_id du graphe choisi, récupère l'output, et maintient la cohérence des transitions inter-graphes.

**Ce n'est pas un graphe LangGraph.** C'est une classe de service backend. Le faire vivre hors LangGraph évite de mélanger deux hiérarchies d'orchestration et garde la responsabilité du routing inter-graphes claire.

### Responsabilités

1. Recevoir les événements entrants (chat utilisateur, monitoring système).
2. Déterminer le graphe cible à partir de `journey_phase`, du type d'événement et des overlays actifs.
3. Gérer les thread_ids par graphe (création, reprise, purge).
4. Invoquer le graphe avec le state d'entrée approprié et récupérer l'output.
5. Lire `journey_phase` post-exécution pour valider la transition et logger.
6. Appliquer les mutations `AthleteState` hors graphe si nécessaire (Phase 0, Phase 1).
7. Enforcer le plafond de pro-activité Head Coach (≤ 2 messages/semaine).

### Thread lifecycle par graphe

| Graphe | Thread | Justification |
|---|---|---|
| `plan_generation` | Persistent (un thread par génération) | Interrupt HITL entre génération et approbation, peut nécessiter plusieurs itérations de révision |
| `onboarding` | Persistent (un thread par parcours onboarding) | Interrupt par bloc, peut être repris après abandon partiel |
| `followup_transition` | Persistent (un thread par transition) | Série de tours conversationnels avec interrupts |
| `chat_turn` | Court (un thread par tour, purgé après réponse) | Pas d'interrupt mid-flow, mémoire conversationnelle dans `AthleteState` + table messages |
| `recovery_takeover` | Persistent (un thread par épisode clinique) | Interrupts HITL successifs sur le protocole, durée variable |

Les thread_ids persistents suivent le format `"{athlete_id}:{graph_name}:{uuid4}"` et sont stockés sur `AthleteState` dans des champs dédiés (`active_onboarding_thread_id`, etc.) pour permettre la reprise après reconnexion.

### Matrice de routage du Coordinator

| Événement entrant | `journey_phase` | Overlay actif | Graphe invoqué | Mode d'appel |
|---|---|---|---|---|
| Chat user | `signup` | — | Aucun (validation service) | — |
| Chat user | `scope_selection` | — | Aucun (logique service) | — |
| Chat user | `onboarding` | — | `onboarding` | Délégation |
| Chat user | `baseline_pending_confirmation` | — | `plan_generation` (resume si pending) | Consultation |
| Chat user | `baseline_active` | — | `chat_turn` (mode observation) | Consultation |
| Chat user | `followup_transition` | — | `followup_transition` | Consultation (Onboarding Coach backend) |
| Chat user | `steady_state` | — | `chat_turn` | Variable selon intent |
| Chat user | Tout | `recovery_takeover_active` | `recovery_takeover` | Takeover |
| Chat user | Tout | `onboarding_reentry_active` | `onboarding` (partiel) | Délégation |
| Event système (silencieux) | Tout | — | Aucun (mutation `AthleteState`) | — |
| Event système (proactif) | `baseline_active` ou `steady_state` | — | `chat_turn` avec seed message | Consultation |
| Event système (blessure détectée) | Tout | — | Active overlay + `recovery_takeover` | Takeover |

---

## Service de monitoring (externe aux graphes)

### Rôle

Évalue les seuils Phase 7 sur l'`AthleteState` sans passer par LangGraph. Pousse ses sorties au `CoordinatorService` sous forme d'événements typés.

### Justification hors-graphe

Les évaluations de monitoring sont des requêtes SQL et des calculs statistiques, pas des appels LLM. Les faire tourner dans un node LangGraph créerait un node qui ne fait pas d'inférence, consomme un checkpoint et complique l'orchestration sans bénéfice. De plus, le monitoring est déclenché par scheduler (cron ou stream d'événements), pas par input utilisateur — lui donner une entrée LangGraph forcerait à inventer un faux déclencheur pour chaque exécution.

### Exécution

Service Python distinct, invoqué par scheduler (cron quotidien à heure basse) ou par events de logs (sur insertion d'un log de session pour évaluation immédiate). Évalue :

- Déviation HRV sur 2 jours consécutifs > 1 écart-type.
- RPE systématique au-dessus du prescrit (> 3 sessions consécutives).
- Non-exécution répétée (> 2 séances manquées sur 7).
- Sommeil dégradé persistant.
- Déviation nutritionnelle persistante (V3).
- Approche d'échéance.
- Ghosting progressif (logique 7/14/21 jours).
- Interruption longue au-delà des seuils (14j / 28j lifting).

### Types de sortie

**Mutation silencieuse.** Ajustement marginal directement sur `AthleteState` ou sur `active_plan` (ex : réduction de volume de 10 % sur la semaine suivante suite à HRV basse 2 jours). Logué, pas de message utilisateur.

**Event Coordinator proactif.** Pousse un événement typé au `CoordinatorService` qui invoque `chat_turn` avec un seed message prescrit. Compte dans le plafond 2/semaine. Exemples : « le Head Coach veut te parler de ta compliance cette semaine », « rapport de sommeil dégradé, Recovery Coach prend la main ».

**Event Coordinator critique.** Bypasse le plafond 2/semaine pour les situations cliniques (HRV en chute libre sur > 5 jours, sommeil dégradé persistant critique). Déclenche directement un overlay `recovery_takeover_active` et le `recovery_takeover` graph.

### Plafond de pro-activité

Implémenté par le `CoordinatorService`, pas par le monitoring. Le monitoring peut émettre plus d'events qu'autorisé ; le Coordinator garde trace des messages proactifs envoyés dans les 7 derniers jours et drop les events non-critiques au-delà du plafond (les events critiques passent toujours).

---

## Les cinq graphes LangGraph

### 1. `plan_generation` (existant, à étendre)

**Rôle.** Générer un plan d'entraînement avec validation humaine. Existant pour la génération baseline et la régénération de bloc, à étendre pour le plan personnalisé Phase 6.

**Entrée.** `athlete_id`, `athlete_dict`, `load_history`, `generation_mode: "baseline" | "first_personalized" | "block_regen"`, DB session.

**Nodes existants** (voir `LANGGRAPH-FLOW.md`) : `analyze_profile`, `compute_acwr`, `delegate_specialists`, `merge_recommendations`, `detect_conflicts`, `resolve_conflicts`, `build_proposed_plan`, `present_to_athlete`, `revise_plan`, `apply_energy_snapshot`, `finalize_plan`.

**Delta nécessaire pour A2.**

1. **Paramètre `generation_mode` en entrée** avec trois valeurs :
   - `baseline` : plan sous-max diagnostique, sortie `baseline_plan`, durée 7–21j selon profil.
   - `first_personalized` : plan macrocycle complet post-baseline, avec horizon 4w / 12w / until_date.
   - `block_regen` : régénération du bloc suivant uniquement dans un plan existant.

2. **`build_proposed_plan` produit une structure `active_plan`** conforme à Phase 6 :
   - `blocks[]` énumérés et titrés, un seul `detail_level: "full"`.
   - `discipline_components` par discipline active.
   - `trade_offs_disclosed` explicite au niveau du plan.

3. **`present_to_athlete` classifie le feedback utilisateur en trois niveaux d'ajustement** :
   - Logistique (jours, ordre) : traité dans `revise_plan` avec re-boucle limitée.
   - Volume/intensité : refusé par `revise_plan` avec explication, pas de re-boucle.
   - Objectif/direction : `revise_plan` signale `redirect_to_onboarding_reentry` en sortie de graphe, le Coordinator active l'overlay et invoque `onboarding` en mode partiel.

4. **Sortie de graphe mute `journey_phase`** :
   - Mode baseline → `baseline_active`.
   - Mode first_personalized → `steady_state`.
   - Mode block_regen → conserve `steady_state`.

5. **Node `consult_onboarding_coach` conditionnel** en amont si `generation_mode == "first_personalized"` : consulte l'Onboarding Coach pour récupérer les mises à jour de profil post-baseline.

**Interrupts HITL.** Un seul : `interrupt_before=["present_to_athlete"]` (inchangé).

**Agents invoqués.**
- `delegate_specialists` : coachs disciplines actifs en consultation silencieuse (existant).
- `consult_onboarding_coach` (nouveau, mode first_personalized) : Onboarding Coach en consultation silencieuse.

**Thread.** Persistent. Un thread par génération.

---

### 2. `onboarding` (nouveau)

**Rôle.** Pilote la Phase 2 (onboarding complet ou partiel). Invoqué aussi pour les re-entrées partielles (overlay `onboarding_reentry_active`).

**Entrée.** `athlete_id`, `coaching_scope`, `blocks_to_cover: list[BlockType]`, `is_reentry: bool`, DB session.

**Nodes.**

| Node | Rôle |
|---|---|
| `initialize_onboarding` | Détermine la liste de blocs à couvrir selon `coaching_scope` et `is_reentry` |
| `propose_connectors` | Propose Hevy/Strava/Apple Health (skipppable, non bloquant) |
| `enter_block` | Annonce le bloc courant à l'utilisateur, posé par Onboarding Coach en délégation |
| `conduct_block_questions` | Boucle interne de questions factuelles indirectes, géré par l'Onboarding Coach |
| `evaluate_block_completion` | Vérifie si > 50 % des questions skippées → bloc marqué insuffisant |
| `persist_block` | Sauvegarde le bloc complété sur `AthleteState`, checkpoint |
| `detect_contradictions` | Croise les réponses avec les blocs précédents, surface sans résolution silencieuse |
| `advance_to_next_block` | Sélectionne le prochain bloc ou termine |
| `compute_classification` | Après tous les blocs, produit le classement 4×3 + niveau de confiance par dimension |
| `generate_radar` | Produit les données du graphique radar |
| `finalize_onboarding` | Mute `journey_phase` vers `baseline_pending_confirmation` (ou maintient `steady_state` + ferme overlay si re-entry) |

**Interrupts HITL.** Un interrupt **entre chaque bloc complété et le bloc suivant**. Configurable via `interrupt_before=["enter_block"]`. Conséquence directe de la décision « checkpoint par bloc » : le graphe pause à l'entrée de chaque bloc, l'utilisateur peut abandonner, la reprise recommence le bloc en cours à sa première question.

**Agents invoqués.** Onboarding Coach en **délégation** pendant toute la durée. L'agent détient le tour conversationnel de `enter_block` à `persist_block` pour chaque bloc.

**Thread.** Persistent. Un thread par parcours onboarding. Réutilisé pour reprises après abandon partiel. Un nouveau thread est créé si délai > 14j déclenche revalidation.

**Transition de sortie.**
- Onboarding complet → `journey_phase = baseline_pending_confirmation`.
- Re-entry partielle (`is_reentry = true`) → `journey_phase` inchangé, `onboarding_reentry_active = false`.

**Modes d'échec gérés dans le graphe.**
- Abandon : checkpoint sur le dernier bloc complété, thread survit.
- Refus d'un bloc obligatoire (objectifs, blessures) : le graphe ne progresse pas, reste sur `conduct_block_questions` du bloc concerné.
- Bloc insuffisant (> 50 % skippés) : `evaluate_block_completion` annote le bloc, `finalize_onboarding` signale à Phase 3 d'étendre la baseline.

---

### 3. `followup_transition` (nouveau)

**Rôle.** Conversation de suivi Phase 5. Consultation de l'Onboarding Coach en backend, Head Coach pose les questions en façade.

**Entrée.** `athlete_id`, `baseline_observations`, DB session.

**Nodes.**

| Node | Rôle |
|---|---|
| `compare_declarative_vs_observed` | Calcule les écarts entre déclaratif onboarding et métriques baseline |
| `consult_onboarding_coach` | Invoque l'Onboarding Coach avec les écarts, récupère un set de questions ciblées structurées |
| `head_coach_ask_question` | Le Head Coach formule et pose une question en façade |
| `collect_response` | Interrupt HITL attend la réponse utilisateur |
| `update_profile_deltas` | Met à jour les sous-modèles `ExperienceProfile` / `ObjectiveProfile` / `PracticalConstraints` selon la réponse |
| `evaluate_conversation_completion` | Vérifie si toutes les questions prioritaires ont été posées |
| `evaluate_exit_conditions` | Vérifie les 6 conditions conjointes de sortie de baseline |
| `dispatch_to_plan_generation` | Si conditions OK, signale au Coordinator d'invoquer `plan_generation` en mode `first_personalized` |
| `extend_baseline` | Si conditions non atteintes, étend la baseline sans replanifier |
| `trigger_reentry_onboarding` | Si contradictions majeures, active overlay `onboarding_reentry_active` |

**Interrupts HITL.** Un interrupt par question posée (`interrupt_before=["collect_response"]`). Le nombre de questions est typiquement 2–5, déterminé par `consult_onboarding_coach`.

**Agents invoqués.**
- Onboarding Coach en **consultation silencieuse** (produit les questions).
- Head Coach en façade (pose les questions).

**Thread.** Persistent. Un thread par transition.

**Transition de sortie.**
- Conditions remplies + conversation complétée → mute `journey_phase = steady_state`, puis Coordinator invoque immédiatement `plan_generation` en mode `first_personalized`.
- Extension baseline → mute `journey_phase = baseline_active`.
- Re-entry onboarding → `onboarding_reentry_active = true`, `journey_phase` inchangé.

---

### 4. `chat_turn` (nouveau)

**Rôle.** Tour de chat en Phase 7 steady-state. Route l'intent, dispatche vers le handler approprié, produit une réponse. Utilisé aussi pour les messages proactifs déclenchés par le monitoring.

**Entrée.** `athlete_id`, `user_message` (ou `seed_message` si invocation proactive), `is_proactive: bool`, DB session.

**Nodes.**

| Node | Rôle |
|---|---|
| `load_recent_context` | Charge les N derniers messages + `AthleteState` |
| `classify_intent` | Head Coach classe l'intent du message en catégories |
| `route_intent` | Edge conditionnel vers le handler approprié |
| `handle_free_question` | Head Coach répond à partir de l'`AthleteState` |
| `handle_daily_checkin` | Head Coach enregistre sommeil/stress/énergie, accuse réception |
| `handle_session_log` | Head Coach enregistre la séance, compare au prescrit, réponse selon écart |
| `handle_weekly_report` | Head Coach produit le rapport hebdo (consulte coachs disciplines en consultation) |
| `handle_injury_report` | Mute `recovery_takeover_active = true`, signale au Coordinator d'invoquer `recovery_takeover` |
| `handle_goal_change` | Mute `onboarding_reentry_active = true`, signale au Coordinator d'invoquer `onboarding` partiel sur bloc objectifs |
| `handle_constraint_change` | Même mécanique, bloc contraintes |
| `handle_adjustment_request` | Head Coach évalue la légitimité (logistique / volume / objectif), répond ou redirige |
| `handle_block_end_trigger` | Détecte fin de bloc, signale au Coordinator d'invoquer `plan_generation` en mode `block_regen` |
| `persist_response` | Sauvegarde la réponse dans la table messages |

**Interrupts HITL.** Aucun. Le graphe exécute de bout en bout à chaque invocation.

**Agents invoqués.** Head Coach systématiquement. Coachs disciplines et autres spécialistes en **consultation silencieuse** selon le handler (ex : `handle_weekly_report` consulte coachs disciplines actifs).

**Thread.** Court. Créé à l'invocation, purgé après réponse. L'historique conversationnel vit dans la table `messages`, pas dans les checkpoints LangGraph.

**Transition de sortie.** Ne mute pas `journey_phase`. Mute les overlays si handlers concernés (`handle_injury_report`, `handle_goal_change`, `handle_constraint_change`). Signale au Coordinator les transitions vers d'autres graphes via des flags dans l'output.

---

### 5. `recovery_takeover` (nouveau)

**Rôle.** Gère l'épisode clinique (blessure, pause clinique, sommeil dégradé critique). Recovery Coach en takeover UX explicite.

**Entrée.** `athlete_id`, `trigger_reason: "user_reported" | "system_detected_hrv" | "system_detected_sleep"`, `injury_payload` (si applicable), DB session.

**Nodes.**

| Node | Rôle |
|---|---|
| `activate_clinical_frame` | Mute `recovery_takeover_active = true`, suspend `active_plan`, signale au frontend de changer le cadre visuel |
| `assess_situation` | Recovery Coach pose des questions diagnostiques (zone, intensité, durée, contexte) |
| `collect_diagnostic` | Interrupt HITL attend réponse utilisateur |
| `evaluate_severity` | Classe la gravité : léger / modéré / grave |
| `propose_protocol` | Recovery Coach propose un protocole : repos complet, repos partiel, travail adapté |
| `collect_protocol_decision` | Interrupt HITL attend validation ou contre-proposition utilisateur |
| `set_suspension_parameters` | Configure la durée de suspension, les contre-indications, les signaux de reprise |
| `monitor_recovery_loop` | Attente passive, réévaluations périodiques via reconvocation du graphe |
| `evaluate_recovery_readiness` | Checklist de reprise : douleur absente, mobilité restaurée, feu vert médical si applicable |
| `propose_return_plan` | Recovery Coach propose baseline partielle (discipline concernée) ou baseline totale |
| `handoff_to_baseline` | Ferme overlay `recovery_takeover_active = false`, mute `journey_phase = baseline_pending_confirmation`, signale au Coordinator d'invoquer `plan_generation` en mode `baseline` |

**Interrupts HITL.** Interrupts successifs sur les décisions cliniques (diagnostic, protocole, reprise). Nombre variable.

**Agents invoqués.** Recovery Coach en **takeover explicite** pendant toute la durée. Visibilité façade distincte, nommage explicite.

**Thread.** Persistent. Un thread par épisode clinique. Peut vivre plusieurs jours à plusieurs semaines.

**Transition de sortie.**
- Reprise validée → ferme overlay, mute `journey_phase = baseline_pending_confirmation`, Coordinator invoque `plan_generation` en mode `baseline` (partielle ou totale selon protocole).
- Abandon / refus de protocole → ferme overlay, `journey_phase` inchangé, note clinique persistée.

---

## Transitions inter-graphes (mapping phase par phase)

Le `CoordinatorService` gère ces transitions. Tableau de vérité complet :

| Graphe sortant | `journey_phase` post-exécution | Overlay post-exécution | Action Coordinator |
|---|---|---|---|
| (aucun) — logique service | `signup → scope_selection` | — | Déclenche présentation des modes au premier chat |
| (aucun) — logique service | `scope_selection → onboarding` | — | Invoque `onboarding` avec tous les blocs pertinents |
| `onboarding` (complet) | `baseline_pending_confirmation` | — | Invoque `plan_generation` en mode `baseline` |
| `onboarding` (re-entry) | Inchangé | `onboarding_reentry_active = false` | Reprise normale selon état principal |
| `plan_generation` (baseline) | `baseline_active` | — | Démarre monitoring actif |
| `plan_generation` (first) | `steady_state` | — | Reprise normale |
| `plan_generation` (block_regen) | Inchangé (`steady_state`) | — | Reprise normale |
| `followup_transition` (OK) | `steady_state` | — | Invoque `plan_generation` en mode `first_personalized` |
| `followup_transition` (extension) | `baseline_active` | — | Reprise normale |
| `followup_transition` (reentry) | Inchangé | `onboarding_reentry_active = true` | Invoque `onboarding` partiel |
| `chat_turn` | Inchangé | Peut muter overlays | Invoque graphe signalé si overlay mis à true |
| `recovery_takeover` (reprise) | `baseline_pending_confirmation` | `recovery_takeover_active = false` | Invoque `plan_generation` en mode `baseline` |
| `recovery_takeover` (abandon) | Inchangé | `recovery_takeover_active = false` | Reprise normale |

---

## Points d'interruption HITL détaillés

| Graphe | Node d'interrupt | Input attendu | Payload de reprise |
|---|---|---|---|
| `plan_generation` | `present_to_athlete` | `approved: bool`, `feedback: str?`, `adjustment_level: "logistics" \| "volume" \| "direction"?` | Mis à jour via `graph.update_state(as_node="present_to_athlete")` |
| `onboarding` | `enter_block` | Réponses aux questions du bloc (accumulées avant le prochain `enter_block`) | Bloc complété persisté, thread checkpoint à la sortie du bloc |
| `followup_transition` | `collect_response` | `response: str` | Réponse à la question courante |
| `chat_turn` | Aucun | — | — |
| `recovery_takeover` | `collect_diagnostic`, `collect_protocol_decision`, `evaluate_recovery_readiness` | Réponses aux questions diagnostiques, décisions de protocole, auto-évaluation de reprise | Selon node |

---

## Routing du Head Coach

Le Head Coach prend deux décisions de routing distinctes selon le contexte.

### Routing inter-phases (implicite via `journey_phase`)

Le Head Coach ne décide pas de la phase. Il consulte `journey_phase` et agit selon. C'est le `CoordinatorService` qui sélectionne le graphe à invoquer en amont de l'intervention du Head Coach.

### Routing intra-phase (dans `chat_turn`)

En `steady_state`, le Head Coach classifie l'intent du message utilisateur et route via le node `route_intent` vers l'un des handlers. La classification est faite par un appel LLM dédié avec un prompt système de classification (Phase C). Catégories d'intent V1 :

1. Question libre (information, clarification).
2. Check-in quotidien (sommeil, stress, énergie, calories).
3. Log de séance (soit complet, soit partiel).
4. Demande de rapport hebdo.
5. Rapport de blessure ou douleur.
6. Changement d'objectif.
7. Changement de contraintes.
8. Demande d'ajustement du plan (à classer en logistique / volume / direction).
9. Demande de pause volontaire.
10. Événement planifié (voyage, perturbation).

Certaines classifications sont mutuellement exclusives, d'autres peuvent coexister dans un même message (le handler traite alors l'intent primaire, les autres sont surfacés en réponse pour demander confirmation).

### Décision du mode d'intervention

Le Head Coach choisit le mode d'intervention du spoke selon une matrice simple :

| Situation | Mode par défaut |
|---|---|
| Génération de plan (toute phase) | Consultation silencieuse des coachs disciplines |
| Check-in nutrition | Consultation silencieuse de Nutrition Coach |
| Rapport de blessure | Takeover Recovery Coach |
| Sommeil dégradé persistant critique | Takeover Recovery Coach |
| Changement d'objectif ou contraintes | Délégation Onboarding Coach (overlay) |
| Tout autre tour chat | Réponse Head Coach directe, pas de spoke invoqué |

Le mode n'est pas négociable dans le flow V1 ; il découle mécaniquement de la situation.

---

## Transitions souterraines spoke → hub

Plusieurs points du flow impliquent qu'un spoke alimente le hub sans parler à l'utilisateur. Pattern commun : **output structuré du spécialiste → reformulation Head Coach en façade**.

### Phase 5 — Onboarding Coach alimente Head Coach

Dans `followup_transition`, le node `consult_onboarding_coach` invoque l'Onboarding Coach avec les écarts observés et récupère une liste structurée de questions (ex : `[{question: "Comment as-tu ressenti la séance de pyramides le jour 5 ?", targets: ["capacity", "technique"], priority: "high"}, ...]`). Le Head Coach formule ces questions en son propre style pour les poser. L'Onboarding Coach ne voit jamais les réponses brutes ; le node `update_profile_deltas` applique directement les mises à jour aux sous-modèles.

### Phases 3, 6, régénération de bloc — Coachs disciplines alimentent build_proposed_plan

Dans `plan_generation`, le node `delegate_specialists` invoque en parallèle les coachs disciplines actifs. Chaque coach produit une `Recommendation` structurée (sessions prescrites pour sa discipline, avec paramètres). Le node `build_proposed_plan` compose ces recommandations en un `active_plan` cohérent, arbitrant les conflits via `detect_conflicts` et `resolve_conflicts`. Le Head Coach présente le plan final en façade ; les coachs disciplines ne sont jamais visibles.

### Phase 7 steady_state — Nutrition Coach sur check-in calories

Dans `chat_turn.handle_daily_checkin`, si la nutrition est dans le `coaching_scope` en `full`, Nutrition Coach est consulté pour évaluer si les calories rapportées nécessitent un ajustement ou un commentaire. Output structuré (verdict + éventuelle recommandation), intégré par le Head Coach dans sa réponse de check-in.

### Phase 7 steady_state — Rapport hebdomadaire

Dans `chat_turn.handle_weekly_report`, tous les coachs disciplines actifs + Recovery + Nutrition sont consultés en parallèle pour produire leurs synthèses respectives. Le Head Coach compose le rapport final en façade.

---

## Delta d'implémentation vs graphe existant

### Ce qui est réutilisé tel quel

Le graphe `plan_generation` existant est le fondement. Ses composants sont tous conservés :
- Nodes : `analyze_profile`, `compute_acwr`, `delegate_specialists`, `merge_recommendations`, `detect_conflicts`, `resolve_conflicts`, `build_proposed_plan`, `present_to_athlete`, `revise_plan`, `apply_energy_snapshot`, `finalize_plan`.
- Logique de révision (compteur via messages, boucle vers `delegate_specialists` ou `build_proposed_plan` selon count).
- Checkpoint SQLite + format thread_id `{athlete_id}:{uuid4}`.
- Debug endpoint state snapshot.
- `log_node` decorator et logging structuré.

### Ce qui est étendu

| Élément | Modification |
|---|---|
| Entrée de graphe | Ajout paramètre `generation_mode: "baseline" \| "first_personalized" \| "block_regen"` |
| `build_proposed_plan` | Produit `active_plan` avec `blocks[]`, `discipline_components`, `trade_offs_disclosed` au lieu de `WeeklyPlan` seule (WeeklyPlan devient une composante des blocs) |
| `present_to_athlete` | Classification du feedback en 3 niveaux d'ajustement |
| `revise_plan` | Branche supplémentaire pour `adjustment_level == "direction"` → signale `redirect_to_onboarding_reentry` au Coordinator |
| Sortie de graphe | Mutation explicite de `journey_phase` selon `generation_mode` |
| Nouveau node optionnel | `consult_onboarding_coach` en amont si mode `first_personalized` |

### Ce qui est à créer

1. **Quatre nouveaux graphes** : `onboarding`, `followup_transition`, `chat_turn`, `recovery_takeover`. Chacun avec ses nodes, edges conditionnels, interrupts, tests d'intégration.

2. **`CoordinatorService`** : nouvelle classe de service backend. Responsabilités :
   - Matrice de routage décrite plus haut.
   - Thread management par graphe.
   - Enforcement du plafond de pro-activité.
   - Gestion des transitions inter-graphes.

3. **`MonitoringService`** : nouveau service Python indépendant. Évaluateurs de seuils Phase 7, scheduler, émetteur d'events vers le Coordinator.

4. **Extensions du schéma `AthleteState`** (Phase B) :
   - `journey_phase: enum`.
   - `recovery_takeover_active: bool`, `onboarding_reentry_active: bool`.
   - `active_onboarding_thread_id`, `active_plan_generation_thread_id`, `active_followup_thread_id`, `active_recovery_thread_id`.
   - Plafond de pro-activité : compteur `proactive_messages_last_7d`.

5. **Nouveaux `_AGENT_VIEWS`** (Phase B + A3) :
   - Onboarding Coach : vue complète en phase onboarding, vue observationnelle en phase followup.
   - Recovery Coach : vue clinique (blessures, HRV, sommeil, RPE) pendant takeover.

6. **Nouveaux prompts système** (Phase C) :
   - Head Coach : classifier d'intent + posture façade + handlers (un par catégorie).
   - Onboarding Coach : posture factuelle indirecte + bloc-specific.
   - Recovery Coach : posture clinique + protocoles de reprise.

7. **Endpoints API nouveaux** :
   - `POST /athletes/{id}/coach/chat` : entry point chat user → Coordinator.
   - `POST /athletes/{id}/coach/onboarding/resume` : reprise d'onboarding après abandon.
   - `GET /athletes/{id}/coach/journey_phase` : lecture de l'état macro.
   - `POST /internal/monitoring/event` : entry point monitoring → Coordinator (authentifié service-to-service).

### Ce qui disparaît

Rien. Le graphe `plan_generation` existant ne perd aucune responsabilité.

---

## Ouvertures Phase C et D

### Phase C — Par agent

À formaliser pour chaque agent :
- Prompt système complet (posture, boundaries, format de sortie).
- `_AGENT_VIEW` consommé par l'agent.
- Contrat de sortie structuré (schema Pydantic de ce que l'agent renvoie en mode consultation).
- Exemples few-shot si nécessaire.

### Phase D — Implémentation backend

Ordre d'implémentation recommandé pour minimiser le risque :

1. Extension de `plan_generation` avec `generation_mode` et structure `active_plan` (le graphe existe, ajout progressif).
2. `CoordinatorService` squelette avec routing par `journey_phase` sur graphes existants uniquement.
3. Graphe `chat_turn` (simple, pas d'interrupt, déverrouille la Phase 7 basique).
4. Graphe `onboarding` (interrupts par bloc, le plus structurant).
5. Graphe `followup_transition`.
6. Graphe `recovery_takeover`.
7. `MonitoringService`.

Chaque étape testable en isolation. Le système reste fonctionnel en dégradé à chaque étape (graphes non encore implémentés retournent un stub géré par le Coordinator).

### Questions ouvertes pour A3 et Phase B

- Définition opérationnelle précise du « Strain » (index de fatigue musculaire) : quel agent le calcule, à partir de quelles métriques, à quelle fréquence.
- Politique de compaction / purge des checkpoints LangGraph persistents longs (onboarding abandonné 6 mois, recovery_takeover clos).
- Stratégie de recovery sur erreur au milieu d'un graphe persistent (network failure pendant `onboarding`, retry policy, message utilisateur).
- Gestion de la concurrence : que se passe-t-il si l'utilisateur envoie un message de chat pendant que le monitoring déclenche un event proactif ?
