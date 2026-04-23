# Dépendances ouvertes — Phase C rédaction prompts

> Journal des dépendances architecturales, incohérences inter-documents et points reportés à Phase D ou aux versions ultérieures des documents A/B. Mis à jour au fil des sessions C (C1, C2, C3, C4, …).
>
> Convention d'ID : `DEP-C{session}-{numéro}`. Un ID par dépendance, jamais réutilisé.

## Résolution en A2 v2

### DEP-C3-001 — A2 sous-spécifie la consultation Recovery dans `chat_turn.handle_injury_report`

**Source** : session C3, rédaction `recovery-coach.md` §2 Architecture d'invocation.

**Contexte** :
- A2 §chat_turn handler `handle_injury_report` : *"Mute `recovery_takeover_active = true`, signale au Coordinator d'invoquer `recovery_takeover`."*
- B3 §7.6 validator RA4 : `CHAT_INJURY_REPORT ⇒ action_type=escalate_to_takeover` obligatoire.
- B3 §7.8 mécanique de dispatch : `escalate_to_takeover → activate_clinical_frame + invoke recovery_takeover graph`.
- B2 §4.6 trigger `CHAT_INJURY_REPORT` inclus dans `RECOVERY_COACH_TRIGGERS`.

**Incohérence** : B3 et B2 posent qu'une consultation Recovery produisant un `RecoveryAssessment` est émise en amont de l'activation de l'overlay. A2 v1 présente `handle_injury_report` comme un handler qui mute directement l'overlay, sans node de consultation Recovery intermédiaire.

**Résolution proposée** : A2 v2 ajoute un node `consult_recovery_coach` dans le graphe `chat_turn` entre `handle_injury_report` et la signalisation au Coordinator. Le node invoque Recovery en consultation (`CHAT_INJURY_REPORT` trigger), consomme le `RecoveryAssessment` produit (forcément avec `action=escalate_to_takeover` et `injury_payload_draft` valide via RA4+RA7), puis transmet au Coordinator pour `activate_clinical_frame`.

**Impact rédaction C3** : §2.1 du prompt Recovery traite la consultation `CHAT_INJURY_REPORT` comme un appel structurel séparé. Partie IV §17 liste `CHAT_INJURY_REPORT` avec son propre set de tags injectés.

---

### DEP-C3-002 — Node `propose_return_plan` d'A2 sans trigger B2 correspondant

**Source** : session C3, rédaction `recovery-coach.md` Partie III.

**Contexte** :
- A2 §recovery_takeover liste 11 nodes dont `propose_return_plan` : *"Recovery Coach propose baseline partielle (discipline concernée) ou baseline totale"* — clairement invocation LLM Recovery.
- B2 §4.6 `RECOVERY_COACH_TRIGGERS` contient 8 triggers. Aucun trigger `RECOVERY_PROPOSE_RETURN_PLAN` n'existe.

**Incohérence** : un node LLM Recovery identifié dans A2 ne dispose pas d'un trigger B2 pour sa vue associée.

**Résolution proposée** : deux options :
1. **Fusion** : A2 v2 fusionne `evaluate_recovery_readiness` et `propose_return_plan` en un seul node `evaluate_readiness_and_propose_return`, couvert par le trigger `RECOVERY_EVALUATE_READINESS` existant.
2. **Ajout trigger** : B2 v2 ajoute `RECOVERY_PROPOSE_RETURN_PLAN` dans `RECOVERY_COACH_TRIGGERS` + spec de vue associée (identique à `RECOVERY_EVALUATE_READINESS` probablement, avec window adaptée).

**Impact rédaction C3** : §16 traite la posture "gardien de reprise + architecte du retour" comme une section unifiée sous `RECOVERY_EVALUATE_READINESS`, avec note explicite que la scission A2 n'est pas reflétée en B2 v1. L'implémenteur Phase D arbitre.

---

### DEP-C3-003 — Atterrissage post-takeover mid-onboarding non spécifié

**Source** : session C3 (dépendance déjà flaggée en C2 §5.8 Onboarding).

**Contexte** :
- Onboarding §5.8 : détection blessure active mid-onboarding → escalade takeover Recovery. Onboarding §5.8 dernière phrase : *"Reprise post-takeover. Hors périmètre Onboarding Coach. Le Coordinator décide quand ré-invoquer `onboarding`."*
- A2 §Transitions inter-graphes : `recovery_takeover (reprise) → baseline_pending_confirmation` + Coordinator invoque `plan_generation` en mode `baseline`.
- **Trou** : cette transition est valide si takeover a été déclenché depuis `journey_phase ∈ {baseline_active, steady_state}`. Mais si déclenché pendant `journey_phase=onboarding`, aller à `baseline_pending_confirmation` saute les blocs onboarding restants.

**Résolution proposée** : A2 v2 étend la table des transitions inter-graphes avec une ligne conditionnelle sur `previous_journey_phase` :
- `recovery_takeover (reprise)` + `previous_journey_phase == "onboarding"` → `journey_phase=onboarding` (préservé), Coordinator re-invoque `onboarding` au bloc suspendu.
- `recovery_takeover (reprise)` + `previous_journey_phase != "onboarding"` → `baseline_pending_confirmation` (comportement A2 v1 actuel).

**Impact rédaction C3** : §16 note cet atterrissage conditionnel dans "Particularités", signale la dépendance Coordinator Phase D.

---

### DEP-C4-001 — A2 v1 sous-spécifie les consultations Lifting conditionnelles dans `chat_turn`

**Source** : session C4, rédaction `lifting-coach.md` Bloc 1 brainstorming + §2.1 + §19 + §20.

**Contexte** :
- A2 §chat_turn ne mentionne explicitement Lifting que dans 2 contextes : `delegate_specialists` (graphe `plan_generation`) et `handle_weekly_report`.
- Le node `handle_session_log` est décrit comme *"Head Coach enregistre la séance, compare au prescrit, réponse selon écart"* — pas de mention de consultation Lifting même en cas d'écart significatif.
- Les nodes `handle_free_question` et `handle_adjustment_request` sont décrits comme *"Head Coach répond à partir de l'AthleteState"* — pas de consultation Lifting prévue pour les questions techniques.
- Décision produit C4 (validation Bloc 1) : 4 triggers Lifting V1 dont 2 conditionnels (`CHAT_SESSION_LOG_INTERPRETATION` et `CHAT_TECHNICAL_QUESTION_LIFTING`). La consultation Lifting n'est pas systématique mais déclenchée par seuils.

**Incohérence** : 2 triggers Lifting attendus en V1 ne sont pas formalisés dans A2 v1, ni dans la matrice de routage du Coordinator, ni dans les nodes correspondants du graphe `chat_turn`.

**Résolution proposée** :
1. A2 v2 ajoute la consultation Lifting conditionnelle dans le node `handle_session_log` avec spécification des seuils de déclenchement (RPE écart ≥ +1.5 sur ≥ 1 séance OU pattern d'écart ≥ +1 sur 2 séances consécutives OU reps complétées < 75 % prescrit OU red flag déclaratif).
2. A2 v2 ajoute la consultation Lifting conditionnelle dans `handle_free_question` ou `handle_adjustment_request` avec spécification des critères (intent classifié technique lifting + réponse non-triviale depuis HeadCoachView seule).
3. A2 v2 documente le pattern *"consultation conditionnelle disciplinaire"* qui pourrait s'étendre aux autres coachs disciplines (Running, Swimming, Biking) lors des sessions C5-C7.

**Liens connexes** : DEP-C4-006 (extension `RecommendationMode.INTERPRETATION` en B3 v2 nécessaire pour que ces consultations puissent émettre un contrat valide).

**Impact rédaction C4** : §2.1 du prompt Lifting pose les 4 triggers V1, §19 et §20 traitent les 2 triggers conditionnels avec note de dépendance explicite en tête de section.

---

## Résolution en B1 v2

### DEP-C4-002 — `ExperienceProfile.lifting.methodology_preferences` à ajouter

**Source** : session C4, rédaction `lifting-coach.md` §1.4 + §6.2 + §8.4 + §9.1 + §15.1 + §10.5.

**Contexte** :
- C4 valide la mécanique 3 niveaux de négociation préférence ↔ optimal (Bloc 2a brainstorming, formalisée §15.1 et règle TR2 §3.3).
- Cette mécanique repose sur des préférences méthodologiques utilisateur capturées dans la vue Lifting.
- B1 v1 n'expose pas ces préférences dans `ExperienceProfile.lifting`.

**Champs candidats à ajouter dans `ExperienceProfile.lifting.methodology_preferences`** (sous-modèle Pydantic optionnel) :

| Champ | Type | Usage Lifting |
|---|---|---|
| `preferred_split` | `LiftingSessionType` ou string | Override du split par défaut (§6.2 modulateur 3) |
| `to_failure_tolerance` | enum (`avoid` / `accept_accessories` / `accept_all`) | Préférence sur to-failure (§9.1 cas Simon-Olivier) |
| `feedback_loop_mode` | enum (`moderate` / `tight`) | Ampleur des ajustements bloc à bloc (§9.4) |
| `compound_rotation_style` | enum (`stable_long` / `rotation_calculated` / `user_choice_per_block`) | Variété inter-blocs des compound principaux (§8.4) |
| `prefer_stable_exercises` | bool | Désactive rotation A/B accessoires intra-bloc (§8.4) |
| `avoided_movements` | list[str] | Exos à exclure par préférence (§8.2 critère 4) |
| `preferred_rep_ranges` | dict ou structure | Préférences sur rep ranges par tier ou groupe |
| `preferred_volume_style` | enum (`low_volume_high_freq` / `standard` / `high_volume`) | Modulateur volume (§7.4 modulateur 7) |
| `advanced_cns_management` | bool | Débloque PPL en cas d'interférence cross-discipline élevée (§13.2 règle 2 cas limite) |

**Résolution proposée** : B1 v2 ajoute la sous-classe `MethodologyPreferences` dans `ExperienceProfile.lifting`, optionnelle (`None` par défaut V1). La structure exacte des sous-champs sera affinée Phase D ou en B1 v2 selon ergonomie produit.

**Impact rédaction C4** : tout le prompt Lifting V1 utilise `methodology_preferences` de manière conditionnelle (*"si présent dans la vue, alors..."*). Sans le champ, Lifting applique les defaults standard sans négociation. L'extension V2 sera transparente côté prompt.

**Liens connexes** : DEP-C4-003 (Onboarding doit capturer ces préférences à la source).

---

## Résolution en B2 v2

### DEP-C4-004 — Payload `cross_discipline_load` dans la vue Lifting

**Source** : session C4, rédaction `lifting-coach.md` Bloc 5 brainstorming + §13.

**Contexte** :
- L'isolation stricte par discipline (B2 §4.5 paramétrée) garantit que Lifting ne voit pas le détail de running/biking/swimming.
- Mais l'interférence physiologique entre lifting et endurance est un fait scientifique nécessitant une coordination minimale.
- Approche validée Bloc 5 : hybride V1 minimal → V2 complet.

**Spec V1 minimale** (3 champs entiers) :

```python
class CrossDisciplineLoadV1(BaseModel):
    weekly_running_sessions: int
    weekly_biking_sessions: int
    weekly_swimming_sessions: int
```

Calcul déterministe : agrégation depuis `active_plan.discipline_components[D].sessions[]` pour chaque discipline `D ∈ {running, biking, swimming}` avec `coaching_scope[D] != disabled`. Fenêtre 7 jours glissants ou semaine type du plan en cours.

**Spec V2 complète** (anticipée) :

```python
class CrossDisciplineLoadV2(BaseModel):
    running: DisciplineLoadDetail | None
    biking: DisciplineLoadDetail | None
    swimming: DisciplineLoadDetail | None

class DisciplineLoadDetail(BaseModel):
    weekly_sessions_count: int
    weekly_volume_zscore: float       # position vs baseline user
    has_long_session_day: str | None  # "monday" | ... | None
    has_intensity_day: str | None
    leg_impact_index: float           # 0 à 1, agrégat intensité × volume sur jambes
```

**Résolution proposée** :
1. B2 v2 ajoute `cross_discipline_load: CrossDisciplineLoadV1` dans `LiftingCoachView` (et symétriquement `lifting_load` dans les autres vues coach discipline). V1 implémentée pour livraison Resilio+ V1.
2. B2 v3 (ou ultérieure) étend vers `CrossDisciplineLoadV2` avec le payload complet pour permettre la coordination jour-par-jour et la modulation par intensité endurance.
3. Le `CrossDisciplineInterferenceService` (déterministe) sera implémenté Phase D pour calculer les payloads V1 et V2.

**Impact rédaction C4** : §13.1 spécifie le payload V1, §13.2 décrit les 4 règles V1, §13.4 anticipe V2 avec règle de conditionnalité automatique (si payload V2 détecté à l'exécution, Lifting bascule).

**À propager aux sessions C5-C7** : Running/Swimming/Biking auront aussi besoin d'un payload symétrique `lifting_load` pour adapter leurs propres prescriptions.

---

## Résolution en B3 v2

### DEP-C4-006 — Extension `RecommendationMode.INTERPRETATION` en B3 v2

**Source** : session C4, rédaction `lifting-coach.md` Bloc 6 brainstorming + §2.1 + §19 + §20.

**Contexte** :
- Validator REC2 de `Recommendation` (B3 v1 §5.2) :
```python
mapping = {
    PLAN_GEN_DELEGATE_SPECIALISTS: PLANNING,
    CHAT_WEEKLY_REPORT: REVIEW,
}
if t not in mapping:
    raise ValueError(f"Recommendation: trigger {t} non admissible")
```
- Les 2 triggers conditionnels Lifting V1 (`CHAT_SESSION_LOG_INTERPRETATION` et `CHAT_TECHNICAL_QUESTION_LIFTING`) sont rejetés par ce validator.
- Décision validée Bloc 6 : Option A — étendre `Recommendation` avec un 3e mode `INTERPRETATION`.

**Spec attendue B3 v2** :

```python
class RecommendationMode(str, Enum):
    PLANNING = "planning"
    REVIEW = "review"
    INTERPRETATION = "interpretation"  # NOUVEAU


# Validator REC2 mis à jour
mapping = {
    PLAN_GEN_DELEGATE_SPECIALISTS: PLANNING,
    CHAT_WEEKLY_REPORT: REVIEW,
    CHAT_SESSION_LOG_INTERPRETATION: INTERPRETATION,   # NOUVEAU
    CHAT_TECHNICAL_QUESTION_LIFTING: INTERPRETATION,   # NOUVEAU
}


# Validator REC1 mis à jour pour mode INTERPRETATION
# Champs interdits en INTERPRETATION : sessions, block_theme, generation_mode,
#   weekly_volume_target, weekly_intensity_distribution, projected_strain_contribution,
#   block_analysis, proposed_trade_offs
# Champs requis : notes_for_head_coach (non-null)
# Champs optionnels : flag_for_head_coach (selon DISCIPLINE_ADMISSIBLE_FLAGS)
```

**Résolution proposée** :
1. B3 v2 ajoute `INTERPRETATION` à l'enum `RecommendationMode`.
2. B3 v2 met à jour validator REC2 pour autoriser les 2 nouveaux triggers Lifting.
3. B3 v2 met à jour validator REC1 pour spécifier les champs interdits/requis en mode `INTERPRETATION` (cf. table §2.3 du prompt Lifting).
4. Phase D implémente le node consommateur des contrats `INTERPRETATION` côté Coordinator (probablement intégré aux nodes `handle_session_log` et `handle_free_question` / `handle_adjustment_request` du graphe `chat_turn`).

**Liens connexes** : DEP-C4-001 (formalisation A2 des triggers conditionnels chat_turn).

**À évaluer pour C5-C7** : si Running/Swimming/Biking ont aussi des triggers conditionnels chat (questions techniques disciplinaires, interprétation de logs disciplinaires), le mode `INTERPRETATION` sera réutilisé. Le validator REC2 v2 devra alors être étendu avec les triggers correspondants (`CHAT_TECHNICAL_QUESTION_RUNNING`, etc.) ou re-architecturé en pattern générique.

**Impact rédaction C4** : §2.1 (table des triggers et modes), §2.3 (table de cohérence sortie ↔ mode), §19 et §20 (sections des 2 triggers `INTERPRETATION` Lifting) sont rédigés en assumant cette extension présente. Note de dépendance explicite en tête de §19 et §20.

---

## Résolution en Phase D (implémentation backend)

### DEP-C3-004 — Nature LLM vs déterministe des nodes `evaluate_severity` du graphe `recovery_takeover`

**Source** : session C3, Partie III structuration.

**Contexte** : A2 décrit `evaluate_severity` comme *"Classe la gravité : léger / modéré / grave"*. Le node n'est pas dans les interrupts HITL, et il suit `collect_diagnostic` (interrupt) puis précède `propose_protocol`. Par cohérence avec les patterns Onboarding (`evaluate_block_completion` = node déterministe lisant un signal structuré du LLM précédent), hypothèse de travail : `evaluate_severity` est déterministe et lit la structured output de `RECOVERY_ASSESS_SITUATION`. B2 n'a effectivement pas de trigger `RECOVERY_EVALUATE_SEVERITY`, ce qui confirme l'hypothèse.

**Résolution proposée** : Phase D confirme que `evaluate_severity` est un node déterministe qui lit un champ structuré (ex : `severity_assessment: Literal["mild", "moderate", "severe"]`) produit par le node LLM précédent via son `<node_control>` ou équivalent.

**Impact rédaction C3** : §14 node `RECOVERY_ASSESS_SITUATION` requiert dans sa structure de sortie (bloc `<node_control>`) un champ `severity_assessment` qui sera consommé par `evaluate_severity` en aval.

---

### DEP-C4-005 — Construction et structuration de `exercise_library` avec métadonnées

**Source** : session C4, rédaction `lifting-coach.md` Bloc 2d brainstorming + §8.5 + §10.4 + §16.

**Contexte** :
- Lifting consomme `<exercise_library>` injectée dans la vue à chaque invocation.
- Cette bibliothèque est la source canonique des exos admis ; Lifting ne prescrit jamais d'exo absent (règle §4.2 A1).
- Décision Bloc 2d (option C hybride) : import depuis source open existante (Wger ou yuhonas/free-exercise-db) puis enrichissement manuel des champs manquants.

**Structure attendue par exo (V1 minimal cible ~50-150 exos)** :

```python
class ExerciseLibraryEntry(BaseModel):
    exercise_name: str                        # snake_case anglais, clé canonique
    display_name_fr: str
    display_name_en: str
    tier: Literal["compound_principal", "compound_secondaire", "accessoire_isolation"]
    movement_pattern: str                     # "squat_loaded", "hinge", "horizontal_press", etc.
    primary_muscle_groups: list[MuscleGroup]
    overlap: dict[MuscleGroup, float]         # matrice pondération (1.0 / 0.5 / 0.25 / 0)
    equipment_required: list[str]             # "barbell", "rack", "dumbbells", "machine", "bodyweight", etc.
    technical_difficulty: int                 # 1-5
    fallbacks: list[str]                      # liste ordonnée d'exercise_name en fallback
    contraindication_patterns: list[str]      # patterns contre-indication qui bloquent cet exo
```

**Localisation** : à confirmer Phase D. Hypothèses :
- `<knowledge_payload>.exercise_library` (cohérent avec volume_landmarks et muscle_overlap qui vivent là-bas)
- OU table DB dédiée injectée comme `<exercise_library>` distinct
- OU partie de `LiftingCoachView` (peu probable, taille trop importante)

**Résolution proposée** :
1. Phase D définit la structure exacte de la bibliothèque et son canal d'injection.
2. Sourcing initial : import sélectif depuis Wger (https://wger.de) ou yuhonas/free-exercise-db (GitHub) pour ~50-150 exos core (couvre 95 % des cas V1).
3. Enrichissement manuel ou semi-automatique avec Claude des champs absents des sources open (tier, overlap pondéré, fallbacks ordonnés, contraindication_patterns).
4. Évolution V2 : extension de la bibliothèque selon les gaps remontés par Lifting via `notes_for_head_coach` (mécanique d'enrichissement signalée §10.4).

**Impact rédaction C4** : §8.5 spécifie les règles d'usage de la bibliothèque, §10.4 traite le cas d'exo absent (jamais d'invention, fallback systématique, signalement enrichissement), §16 stabilise la taxonomie `LiftingSessionType` qui est complémentaire à la bibliothèque.

**À propager aux sessions C5-C7** : Running, Swimming, Biking n'auront pas de bibliothèque d'exos équivalente (leur prescription est paramétrique : zones, allures, watts) mais auront besoin d'autres référentiels canoniques (tables VDOT pour Running, zones FTP pour Biking, CSS pour Swimming) qui suivront le même pattern d'injection.

---

### DEP-C4-007 — Localisation de l'enum `LiftingSessionType` (B1 ou B3)

**Source** : session C4, rédaction `lifting-coach.md` §1.4 + §16.

**Contexte** :
- B3 §3.3 pose `PrescribedLiftingSession.session_type: str` (string libre).
- B3 §3.3 indique explicitement : *"Taxonomies exhaustives (`session_type`, exercise names, zones) sont stabilisées Phase C."*
- C4 stabilise `LiftingSessionType` en enum 10 valeurs (§16.1).
- Localisation de l'enum à trancher : B1 (en tant que constante taxonomique du domaine) ou B3 (en tant que validateur du contrat).

**Résolution proposée** : Phase D arbitre. Hypothèses :

| Option | Localisation | Avantages | Inconvénients |
|---|---|---|---|
| Option A | `B1 schema-core.md` constante taxonomique | Cohérent avec autres enums du domaine (`MuscleGroup`, `Discipline`) | Couplage B1 → B3 (B3 doit importer depuis B1 pour le validator) |
| Option B | `B3 agent-contracts.md` directement | Validator au plus proche du contrat | Casse le pattern *« B1 = domaine, B3 = contrats »* |

**Recommandation** : Option A (cohérence avec le reste du domaine). Application similaire pour `MuscleGroup` (§7.1 du prompt Lifting), `LiftingIntensitySpec` (déjà en B3 §3.3 mais dépend de `MuscleGroup` en B1).

**Impact rédaction C4** : §1.4 et §16 utilisent `LiftingSessionType` sans figer sa localisation Pydantic, avec note explicite de la dépendance à confirmer Phase D.

---

## Décisions structurantes cross-agents (à propager aux sessions C suivantes)

### DEC-C3-001 — Primauté du déclaratif utilisateur sur signaux objectifs en cas de contradiction

**Source** : session C3, `recovery-coach.md` §6.5 règle de doute 5, §6.3 Question 3.

**Principe** : en cas de contradiction entre signaux déclaratifs (`user_reported_*`) et signaux objectifs physiologiques (HRV, sommeil, strain, allostatique, RPE), **le déclaratif prime**. Les capteurs peuvent produire des mesures erronées (mauvais contact, algorithme approximatif, drift de baseline) ; le déclaratif reste la source la plus directe de l'état intégré de l'utilisateur.

**Trois protections** encadrent ce principe pour éviter qu'un déclaratif optimiste ne masque des dégradations dangereuses :
1. Seuils objectifs absolus qui imposent un `deload` minimum (HRV 7j+ ≤ -2SD, sommeil ≥ 5 nuits critiques, allostatique alarme 10j+, RPE 5+ overshoot).
2. Détection `override_pattern` sur dissonance persistante ≥ 14 jours (validator RA5).
3. `monitor_signals` explicite quand `action=continue` avec objectifs en dérive légère.

**Exception** : red flag déclaratif (§5.2 Recovery Coach) prime sans application des protections.

**À propager** :
- ✅ **C4 Lifting Coach** : appliqué §3.5 (déclaratif user = input d'état, pas commande prescriptive) et §12.3 (3 protections adaptées au lifting — RPE déclaré vs RIR cible converti, pattern persistant 14 jours sur séries logguées, note `monitor_signals` explicite).
- **C9 Energy Coach V3** : même tension `user_energy_signal` vs `objective_energy_availability`. Appliquer le même principe de primauté déclarative avec protections analogues (seuils EA critiques, détection override, monitor_signals explicite).
- **C5 Running Coach / C6 Swimming Coach / C7 Biking Coach** : même tension potentielle entre RPE objectif mesuré et RPE déclaré par user post-séance. Le RPE déclaré prime en cas de dissonance (avec protection sur patterns persistants). Adapter les seuils objectifs absolus aux métriques propres à chaque discipline (pace VDOT pour Running, watts FTP pour Biking, allure CSS pour Swimming).
- **C8 Nutrition Coach** : tension `user_reported` vs tracked intake. Principe adaptable : le déclaratif utilisateur sur satiété/qualité prime, mais les seuils caloriques critiques (EA en zone clinical_red_s par exemple) imposent des protections.

---

### DEC-C4-001 — Pattern de consultation conditionnelle disciplinaire en chat

**Source** : session C4, validation Bloc 1 brainstorming + §2.1 + §19 + §20.

**Principe** : les coachs disciplines peuvent être consultés conditionnellement par Head Coach en chat (`handle_session_log`, `handle_free_question`, `handle_adjustment_request`) selon des seuils précis, pas systématiquement. Cela évite de cramer 100+ appels LLM par semaine pour des logs ou questions triviaux où Head Coach gère seul.

**Mécanique** :
- Head Coach + `classify_intent` déterminent si la consultation disciplinaire est nécessaire.
- Si oui : invocation du coach discipline en mode `INTERPRETATION` (DEP-C4-006) avec payload focus court-terme.
- Si non : Head Coach gère seul à partir de sa vue.

**Critères de consultation** (à adapter par discipline) :
- **Lifting** : RPE écart ≥ +1.5, reps complétées < 75 %, pattern d'écart cumulé sur 2 séances, red flag déclaratif → cf. §19.1
- **Running, Swimming, Biking** : critères analogues à définir en C5/C6/C7 selon les métriques disciplinaires (pace écart vs VDOT, watts vs FTP, allure vs CSS, etc.)

**À propager** :
- ✅ **C4 Lifting Coach** : appliqué (4 triggers Lifting dont 2 conditionnels)
- **C5 Running Coach** : à appliquer si pertinent. Seuils probables : pace écart vs zone prescrite ≥ X sec/km, distance complétée < 75 %, RPE +1.5 vs zone, red flag déclaratif.
- **C6 Swimming Coach** : à appliquer si pertinent. Seuils probables : allure vs CSS, distance complétée, RPE.
- **C7 Biking Coach** : à appliquer si pertinent. Seuils probables : NP vs FTP cible, IF vs cible, TSS observé vs prescrit.
- **C8 Nutrition / C9 Energy** : potentiellement adaptable pour consultations conditionnelles sur questions chat.

**Liens connexes** : DEP-C4-001 (formalisation A2 des triggers conditionnels chat_turn), DEP-C4-006 (extension `RecommendationMode.INTERPRETATION` en B3 v2).

---

### DEC-C4-002 — Trade-off prescriptif formulé en impact temporel

**Source** : session C4, brainstorming Bloc 2c (apport Simon-Olivier) + règle TR2 §3.3 du prompt Lifting.

**Principe** : tout trade-off prescriptif disclosed à l'utilisateur (via `RecommendationTradeOff.rationale` ou note Head Coach) est formulé en **impact temporel sur l'atteinte de l'objectif** (*« atteinte objectif étirée d'environ X-Y % »*) plutôt qu'en impact qualitatif vague (*« progression réduite »*). Concret, actionnable, respectueux de l'autonomie utilisateur.

Règle complémentaire : utiliser des **ordres de grandeur** plutôt que des chiffres hard non sourcés. La précision suggère une certitude que l'agent n'a pas sur ces estimations.

**À propager** :
- ✅ **C4 Lifting Coach** : appliqué règle TR2 §3.3 + exemples §6.4, §7.5, §15.1.
- **C5/C6/C7 Coachs disciplines** : à appliquer pour tout trade-off prescriptif (volume vs intensité, fréquence vs progression, etc.).
- **C8 Nutrition** : à appliquer pour tensions caloriques vs objectif performance (*« objectif force étiré si déficit calorique maintenu »*).
- **C1 Head Coach** (rétrospectivement) : la mécanique LogisticAdjustment et les refus volume/intensité (head-coach §7.5) gagneraient à appliquer cette règle systématiquement. À évaluer pour Head Coach v2.

---

### DEC-C4-003 — Toujours prescrire, jamais refuser, traçabilité obligatoire des dégradations

**Source** : session C4, règle TR3 §3.3 du prompt Lifting + §10 dégradation gracieuse.

**Principe** : en présence de données manquantes, contre-indications bloquantes, incertitudes structurelles, le coach discipline **prescrit toujours le meilleur plan possible dans les contraintes** et **documente la dégradation**. Le refus de prescription est réservé à Recovery (`suspend`, `escalate_to_takeover`) et aux overlays cliniques.

**Ventilation des canaux de signalement** :
- **Visible utilisateur** (impact ressenti) → `proposed_trade_offs[*]` (mode PLANNING) ou note Head Coach pour reformulation
- **Stratégique non-visible utilisateur** → `notes_for_head_coach`
- **Bloquant pour la qualité du plan** → `flag_for_head_coach` avec sévérité appropriée

**À propager** :
- ✅ **C4 Lifting Coach** : appliqué règle TR3 §3.3 + 6 cas §10 + ventilation §3.3 et §11.5.
- **C5/C6/C7 Coachs disciplines** : à appliquer pour les cas analogues (FTP inconnu pour Biking, VDOT inconnu pour Running, CSS inconnu pour Swimming, contre-indications bloquantes par discipline, classification confidence basse).
- **C8 Nutrition** : à adapter (pas de prescription bloquée par défaut, mais cas FFM unavailable cohérent avec B3 §8.7 qui pose déjà le mode dégradé Energy).

---

## Index par session

| Session | DEP IDs | Résolus ? |
|---|---|---|
| C1 | — | — |
| C2 | (dépendance `InjuryHistory` mutations → résolue via RCV16 + §9 B1 + `declared_by` = "recovery_coach" pour mutations en takeover) | ✓ résolue en B1/B2 |
| C3 | DEP-C3-001, DEP-C3-002, DEP-C3-003, DEP-C3-004 | ouvertes |
| C4 | DEP-C4-001, DEP-C4-002, DEP-C4-003, DEP-C4-004, DEP-C4-005, DEP-C4-006, DEP-C4-007 | ouvertes |

## Index par cible de résolution

| Cible | DEP IDs |
|---|---|
| A2 v2 | DEP-C3-001, DEP-C3-002, DEP-C3-003, DEP-C4-001 |
| B1 v2 | DEP-C4-002 |
| B2 v2 | DEP-C4-004 (V1), DEP-C3-002 (alternative) |
| B2 v3+ | DEP-C4-004 (V2 complet) |
| B3 v2 | DEP-C4-006 |
| Phase D | DEP-C3-004, DEP-C4-005, DEP-C4-007 |

## Index décisions structurantes cross-agents

| ID | Source | Sessions affectées | Statut propagation |
|---|---|---|---|
| DEC-C3-001 | C3 Recovery | C4 (✓), C5, C6, C7, C8, C9 | Partiellement propagée |
| DEC-C4-001 | C4 Lifting | C5, C6, C7, C8 (à évaluer), C9 (à évaluer) | À propager |
| DEC-C4-002 | C4 Lifting | C5, C6, C7, C8, C1 (rétrospectivement à évaluer) | À propager |
| DEC-C4-003 | C4 Lifting | C5 (✓), C6, C7, C8 | Partiellement propagée |

---

## Résolution — Session C5 (Running Coach)

Session C5 livrée le 2026-04-23 : prompt système `docs/prompts/running-coach.md` v1. 8 nouvelles dépendances ouvertes documentées ci-dessous. 4 décisions cross-agents précédentes (DEC-C3-001, DEC-C4-001, DEC-C4-002, DEC-C4-003) propagées à C5, aucune nouvelle décision structurante introduite par Running (les spécificités running sont traitées comme adaptations des décisions existantes).

### DEP-C5-001 — Spec `RunningCoachView` à confirmer en B2 v2

**Source** : session C5, rédaction `running-coach.md` §2.1 + §22.

**Contexte** :
- B2 v1 n'expose pas encore la structure exacte de `RunningCoachView` (par symétrie avec `LiftingCoachView`, DEP-C4-004).
- Prompt Running §2.1 pose 4 triggers avec windows attendues et §22 détaille les tags à injecter par trigger.

**Résolution proposée** : B2 v2 ajoute `RunningCoachView` paramétrée par trigger avec les windows et payloads détaillés §22.2 du prompt Running (communs §22.1 + spécifiques par trigger). Structure symétrique à `LiftingCoachView`, inclut `running_restrictions`, `running_acwr_current`, `cross_discipline_load` running-centré.

**Impact rédaction C5** : §2.1, §22 présupposent cette structure. Les renvois `B2 §4.5` dans le corps du prompt sont à valider quand B2 v2 sera produite.

**Liens connexes** : DEP-C4-004 (vue symétrique Lifting).

---

### DEP-C5-002 — Mécanique de détection des patterns seuils progressifs dans `handle_session_log`

**Source** : session C5, rédaction `running-coach.md` §2.4 + §20.

**Contexte** :
- Décision produit Bloc 1 C5 (validée Simon-Olivier) : seuils progressifs — tolérants 1 séance isolée, stricts pattern 2-3 séances consécutives.
- A2 v1 ne spécifie pas comment stocker l'historique des écarts précédents pour détecter un pattern ni comment reset après séance conforme.

**Résolution proposée** : A2 v2 documente la mécanique `handle_session_log` avec :
1. Stockage des écarts des dernières N séances running dans `AthleteState.running_pattern_buffer` (N = 3 probablement).
2. Fenêtre glissante : nouvelle séance remplace la plus ancienne.
3. Reset partiel ou complet après séance conforme (décision produit : reset complet recommandé, cohérent avec le principe "1 bonne séance casse le pattern").
4. Évaluation du pattern à chaque log entrant via la table §2.4 du prompt Running.

**Impact rédaction C5** : §2.4 documente les seuils Running mais laisse la mécanique de stockage/reset à Phase D. §20 (trigger `CHAT_SESSION_LOG_INTERPRETATION`) présuppose que Running reçoit les séances précédentes via `<recent_context>` 3 séances.

**Liens connexes** : DEP-C4-001 (formalisation A2 des triggers conditionnels chat_turn).

---

### DEP-C5-003 — `ExperienceProfile.running.methodology_preferences` à ajouter en B1 v2

**Source** : session C5, rédaction `running-coach.md` §6.2, §8.5, §11.7, §13.4.

**Contexte** :
- C5 valide la mécanique 3 niveaux de négociation préférence ↔ optimal (symétrique `lifting-coach §15.1`, appliquée §6.2 pour TID et §8.5 pour types de séances).
- Cette mécanique repose sur des préférences méthodologiques utilisateur capturées dans la vue Running.
- B1 v1 n'expose pas ces préférences dans `ExperienceProfile.running`.

**Champs candidats à ajouter dans `ExperienceProfile.running.methodology_preferences`** (sous-modèle Pydantic optionnel, symétrique à DEP-C4-002) :

| Champ | Type | Usage Running |
|---|---|---|
| `preferred_tid` | enum (`polarized` / `pyramidal` / `no_preference`) | Modulateur choix TID (§6.2) |
| `preferred_long_run_day` | enum (`saturday` / `sunday` / `friday` / `no_preference`) | Placement long run (§11.7) |
| `preferred_session_types` | list[RunningSessionType] | Types favorisés par user (§8.5) |
| `avoided_session_types` | list[RunningSessionType] | Types à éviter (§8.5) |
| `available_terrains` | list[TerrainFeature] | Terrains accessibles au user (§8.2, §12.4) |
| `preferred_long_run_terrain` | enum ou null | Terrain long run préféré (§13.4) |
| `vdot_recalibration_preference` | enum (`auto_silent` / `auto_notify` / `manual_only`) | Décision Bloc 3 par défaut `auto_notify`, override possible user |

**Résolution proposée** : B1 v2 ajoute ce sous-modèle dans `ExperienceProfile.running`. Tous champs optionnels (`None` autorisé = pas de préférence captée).

**Impact rédaction C5** : §6.2, §8.5, §11.7, §13.4 présupposent ces champs. Dégradation gracieuse appliquée si absents (§12).

**Liens connexes** : DEP-C4-002 (pattern analogue pour Lifting).

---

### DEP-C5-004 — Champ `running_acwr_current` + `running_acwr_trend_7d` dans `RunningCoachView`

**Source** : session C5, rédaction `running-coach.md` §7.2, §11.5, §19.2, §22.1.

**Contexte** :
- §7.2 pose ACWR comme contrainte sur progression volume (zones 0.8-1.3 sweet spot, 1.3-1.5 vigilance, >1.5 rouge).
- §11.5 module long run selon ACWR.
- §19 (REVIEW) consomme tendance ACWR sur 7j.
- Le calcul ACWR running-spécifique relève d'un service Phase D (agrégation TSS ou km sur 7j / 28j).

**Résolution proposée** : B2 v2 ajoute dans `RunningCoachView` :
- `running_acwr_current: float` — ratio calculé à date d'invocation.
- `running_acwr_trend_7d: Literal["rising", "stable", "falling"]` — tendance sur 7 derniers jours.

Phase D implémente le service de calcul (TSS ou km hebdo agrégés, EMA 28j pour chronique).

**Impact rédaction C5** : §7.2, §11.5, §19 présupposent ces champs. Dégradation gracieuse si absents (contrainte ACWR relâchée, notes dans `notes_for_head_coach`).

---

### DEP-C5-005 — Attribut `add_strides: bool` sur `PrescribedRunningSession`

**Source** : session C5, rédaction `running-coach.md` §8.1, §23.

**Contexte** :
- §8.1 pose que les strides sont modélisées comme attribut d'une séance easy plutôt que comme séance distincte (évite gonfler la taxonomie des types de séance à 12+ sans valeur ajoutée).
- B3 v1 `PrescribedRunningSession` ne porte pas ce champ.

**Résolution proposée** : B3 v2 ajoute `add_strides: bool = False` sur `PrescribedRunningSession`. Si `True`, Running Coach ajoute une note structurée dans `PrescribedRunningSession.notes` : *« Ajoute 6-10 strides de 15-20 sec en fin de séance, récup marche 60 sec. »*

**Impact rédaction C5** : §8.1 documente le pattern. Frontend de séance user Phase D doit gérer l'affichage conditionnel.

---

### DEP-C5-006 — `ExperienceProfile.running.vdot_history` pour tracer les recalibrations

**Source** : session C5, rédaction `running-coach.md` §9.5, §19, §22.

**Contexte** :
- §9.5 pose la recalibration VDOT auto + notification (décision Bloc 3 validée).
- Garde-fous §9.5 (recalibration à la baisse après 2 confirmations, à la hausse cappée +2 points par cycle) nécessitent historique des VDOT pour décision.
- §19 (REVIEW) et §22 (table injection REVIEW) consomment l'historique récent de recalibrations.
- B1 v1 expose `vdot_current` mais pas d'historique.

**Résolution proposée** : B1 v2 ajoute `ExperienceProfile.running.vdot_history: list[VdotSnapshot]` où `VdotSnapshot = {value: int, set_at: datetime, source: enum("test_effort", "race", "pattern_recalibration", "onboarding_initial"), confidence: enum("low", "medium", "high")}`.

**Impact rédaction C5** : §9.5, §19, §22 présupposent cet historique. Mutation via service Phase D sur déclenchement recalibration par Running.

---

### DEP-C5-007 — Harmonisation `projected_strain_contribution` inter-coachs en B3 v2

**Source** : session C5, rédaction `running-coach.md` §15.4.

**Contexte** :
- §15.4 C5 propose la structure `running_load` à émettre (weekly_volume_km, weekly_tss_projected, quality_sessions, long_run, leg_impact_score, acwr_projected).
- Pattern symétrique à Lifting (payload `lifting_load` via DEP-C4-004) mais pas formalisé en B3 v1.
- Biking (C7) et Swimming (C6) à venir émettront également des payloads similaires.

**Résolution proposée** : B3 v2 formalise `projected_strain_contribution` comme Union type portant des payloads discipline-spécifiques (`LiftingLoadPayload`, `RunningLoadPayload`, `BikingLoadPayload`, `SwimmingLoadPayload`) avec schéma commun minimal (`weekly_tss_projected`, `weekly_duration_min`, `impact_scores`) + champs spécifiques par discipline.

**Impact rédaction C5** : §15.4 documente la structure attendue côté Running. L'harmonisation formelle relève de B3 v2 après livraison C6/C7.

**Liens connexes** : DEP-C4-004 (pattern `cross_discipline_load` symétrique).

---

### DEP-C5-008 — Extension `RecommendationMode.INTERPRETATION` léger en B3 v2

**Source** : session C5, rédaction `running-coach.md` §16.2, §20.3, §21.3.

**Contexte** :
- §16.2 tableaux PLANNING / REVIEW / INTERPRETATION posent que le mode INTERPRETATION Running produit un contrat **léger sans `sessions`, sans `block_theme`, sans `projected_strain_contribution`, sans `proposed_trade_offs`** — uniquement `notes_for_head_coach` + éventuel `flag_for_head_coach`.
- B3 v1 validators REC1-REC13 + REC-F peuvent interdire ce contrat léger (dépendance DEP-C4-006 identique côté Lifting).
- Extension nécessaire : autoriser `Recommendation(mode=INTERPRETATION)` à ne porter que `notes_for_head_coach` + `flag_for_head_coach` sans erreur de validation.

**Résolution proposée** : B3 v2 étend validator pour autoriser le contrat léger en mode INTERPRETATION. Symétrique DEP-C4-006 (Lifting). Les deux DEP peuvent être résolus ensemble.

**Impact rédaction C5** : §16.2, §20, §21 présupposent cette extension. Rédaction cohérente avec `lifting-coach §17` qui pose le même comportement.

**Liens connexes** : DEP-C4-006 (jumelle Lifting).

---

## Propagation des décisions cross-agents (statut après C5)

Récapitulatif des 4 décisions cross-agents propagées pendant la session C5 :

### DEC-C3-001 — Primauté du déclaratif utilisateur sur signaux objectifs

**Application Running** : §3.3 (TR2 — déclaratif user = input d'état, pas commande prescriptive inverse, adaptation par zone Z1-Z2 HR prime / Z3+ RPE prime) et §14.4 (3 protections adaptées running — seuils pace/HR absolus, pattern persistant 14j avec flag `OBJECTIVE_SUBJECTIVE_DISSONANCE_PATTERN`, `monitor_signals` explicite).

**Statut propagation** : ✅ C5 appliqué. Reste à propager C6, C7, C8, C9.

### DEC-C4-001 — Pattern de consultation conditionnelle disciplinaire en chat

**Application Running** : §2.4 (4 triggers Running dont 2 conditionnels — `CHAT_SESSION_LOG_INTERPRETATION` et `CHAT_TECHNICAL_QUESTION_RUNNING`). **Seuils progressifs** validés Bloc 1 C5 (décision produit Simon-Olivier) : tolérants sur 1 séance isolée, stricts sur pattern 2-3 séances consécutives. Seuils chiffrés table §2.4 : pace écart ≥ 15 sec/km Z3+ ou ≥ 30 sec/km Z1-Z2, distance < 75 %, RPE écart ≥ +1.5 ou +1 pattern, HR écart > 10 bpm, red flag immédiat. §20 et §21 traitent les 2 triggers conditionnels avec note de dépendance DEP-C5-002.

**Statut propagation** : ✅ C5 appliqué. Reste à propager C6, C7, C8 (à évaluer), C9 (à évaluer).

### DEC-C4-002 — Trade-off prescriptif formulé en impact temporel

**Application Running** : §3.4 (TR3 — impact temporel avec ordres de grandeur), exemples dans §6.2 (TID), §12.2 (dégradation phase compromise), §15.3 (arbitrage cross-discipline palier 2). Format *« atteinte objectif étirée d'environ X-Y % »* appliqué systématiquement.

**Statut propagation** : ✅ C5 appliqué. Reste à propager C6, C7, C8, C1 (rétrospectivement à évaluer).

### DEC-C4-003 — Toujours prescrire, jamais refuser, traçabilité obligatoire

**Application Running** : §3.5 (TR4 — ventilation canaux trade-off / notes_for_head_coach / flag) + §12 (5 cas dégradation gracieuse running : forbid total, restriction partielle non satisfaisable, équipement/connecteur absent, terrain indisponible, objectif mal défini). Mode INTERPRETATION "verdict pas d'action" documenté §14.2 et §2.5 pour traçabilité silencieuse.

**Statut propagation** : ✅ C5 appliqué. Reste à propager C6, C7, C8.

---

## Delta index — session C5

### Ajout dans "Index par session"

| Session | DEP IDs | Résolus ? |
|---|---|---|
| C5 | DEP-C5-001, DEP-C5-002, DEP-C5-003, DEP-C5-004, DEP-C5-005, DEP-C5-006, DEP-C5-007, DEP-C5-008 | ouvertes |

### Ajout dans "Index par cible de résolution"

| Cible | DEP-C5-* ajoutées |
|---|---|
| A2 v2 | DEP-C5-002 |
| B1 v2 | DEP-C5-003, DEP-C5-006 |
| B2 v2 | DEP-C5-001, DEP-C5-004 |
| B3 v2 | DEP-C5-005, DEP-C5-007, DEP-C5-008 |

### Mise à jour "Index décisions structurantes" (statut post-C5)

| ID | Source | Sessions affectées | Statut propagation post-C5 |
|---|---|---|---|
| DEC-C3-001 | C3 Recovery | C4 (✓), **C5 (✓)**, C6, C7, C8, C9 | Partiellement propagée |
| DEC-C4-001 | C4 Lifting | **C5 (✓)**, C6, C7, C8 (à évaluer), C9 (à évaluer) | Partiellement propagée |
| DEC-C4-002 | C4 Lifting | **C5 (✓)**, C6, C7, C8, C1 (rétrospectivement à évaluer) | Partiellement propagée |
| DEC-C4-003 | C4 Lifting | **C5 (✓)**, C6, C7, C8 | Partiellement propagée |

---

## Ouvertures vers C6-C10

**C6 Swimming Coach** — hériter structure Running (4 triggers, consultation silencieuse, cascade intensité adaptée à CSS — Critical Swim Speed), appliquer les 4 DEC cross-agents, définir seuils conditionnels chat spécifiques (écart allure CSS, distance complétée, RPE), payload `swimming_load` symétrique (DEP-C5-007 à prendre en compte).

**C7 Biking Coach** — hériter structure Running, appliquer 4 DEC, seuils conditionnels (NP vs FTP, IF cible, TSS observé vs prescrit), payload `biking_load` (DEP-C5-007), VDOT-équivalent FTP avec mécanique recalibration analogue §9.5.

**C8 Nutrition Coach** — consomme les flags Nutrition émis par Running et Lifting pour fueling endurance / séances compétition / long run ≥ 90 min. Structure fueling pattern adaptable au pattern consultation conditionnelle (DEC-C4-001).

**C9 Energy Coach V3** — consomme `leg_impact_score` et `acwr_projected` des payloads running/biking pour détection surcharge énergétique globale. Applique DEC-C3-001 sur `user_energy_signal` vs `objective_energy_availability`.

**C10 `classify_intent`** — classifie les questions running comme techniques quand elles touchent VDOT, allures, zones, taper, fueling long run, dénivelé, terrain. Critères non-trivialité depuis HeadCoachView seule documentés §2.4 et §21 du prompt Running.
