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

---

## Dépendances ouvertes — session C6 (Swimming Coach)

### DEP-C6-001 — `SwimmingCoachView` paramétrée en B2 v2

**Source** : session C6, rédaction `swimming-coach.md` §2.1, §18.2, §19.2, §20.2, §21.2.

**Contexte** :
- B2 v1 ne spécifie pas la `SwimmingCoachView` en tant que vue paramétrée par discipline avec isolation stricte.
- Swimming Coach consomme 4 scopes distincts (`planning`, `review`, `log_interpretation`, `technical_question`) avec fenêtres temporelles et contenus différenciés.
- Pattern symétrique DEP-C5-001 (RunningCoachView) et DEP-C4-005 (LiftingCoachView).

**Résolution proposée** : B2 v2 ajoute `SwimmingCoachView` paramétrée par scope + window, avec isolation stricte swimming-only (pas d'accès aux disciplines autres, sauf via `cross_discipline_load` agrégé).

**Impact rédaction C6** : §2.1, §18-§21 présupposent cette vue paramétrée. Rédaction cohérente avec RunningCoachView / LiftingCoachView.

**Liens connexes** : DEP-C5-001, DEP-C4-005.

---

### DEP-C6-002 — Consultation Swimming conditionnelle dans `chat_turn` en A2 v2

**Source** : session C6, rédaction `swimming-coach.md` §2.4, §20, §21.

**Contexte** :
- A2 §chat_turn ne formalise pas la consultation Swimming conditionnelle pour `handle_session_log` et `handle_free_question` avec seuils de déclenchement.
- Décision produit C6 (validation Bloc 1 Simon-Olivier) : seuils progressifs tolérant 1 séance isolée / strict pattern 2-3 séances consécutives, avec métriques swimming-specific (pace CSS, distance, RPE, SWOLF, red flag).
- Pattern symétrique DEP-C5-002 (Running) et DEP-C4-001 (Lifting).

**Résolution proposée** :
1. A2 v2 ajoute la consultation Swimming conditionnelle dans `handle_session_log` avec seuils (pace écart ≥ +5 sec/100m Z3+ ou ≥ +10 Z1-Z2, distance < 75 %, RPE écart ≥ +1.5, SWOLF dégradé ≥ +10 % si tracké, red flag).
2. A2 v2 ajoute la consultation Swimming conditionnelle dans `handle_free_question` / `handle_adjustment_request` pour questions classifiées techniques swimming non-triviales depuis HeadCoachView seule.

**Liens connexes** : DEP-C6-005 (extension `RecommendationMode.INTERPRETATION` en B3 v2), DEP-C5-002, DEP-C4-001, DEC-C4-001.

**Impact rédaction C6** : §2.1 pose les 4 triggers V1 Swimming, §20 et §21 traitent les 2 triggers conditionnels avec note de dépendance explicite.

---

### DEP-C6-003 — `ExperienceProfile.swimming` à étendre en B1 v2

**Source** : session C6, rédaction `swimming-coach.md` §1.4, §6.2, §7.1, §8.2, §9.1, §9.4, §9.5, §11.4, §13.

**Contexte** :
- C6 valide plusieurs préférences utilisateur swimming (mécanique 3 niveaux négociation §6.2).
- B1 v1 n'expose pas ces préférences dans `ExperienceProfile.swimming`.
- Pattern symétrique DEP-C5-003 (Running) et DEP-C4-002 (Lifting).

**Champs candidats à ajouter dans `ExperienceProfile.swimming`** :

| Champ | Type | Usage Swimming |
|---|---|---|
| `css_current` | int (sec/100m) | CSS courant, référence prescription |
| `css_history` | list[CssSnapshot] | Historique CSS avec source/confidence/timestamp (§9.5). Symétrique DEP-C5-006 VDOT Running |
| `stroke_preferences` | sub-model | `primary_stroke` (défaut freestyle), `secondary_strokes` (backstroke, breaststroke, butterfly), `avoid_strokes` |
| `terrain_availability` | list[SwimmingTerrain] | `pool_25m` / `pool_50m` / `open_water` — prescriptions conditionnées |
| `terrain_safety_acknowledged` | bool | Déclaration user sur safety open water (§11.5) |
| `hr_tracking_enabled` | bool | Activation HR swim (défaut false, §9.2) |
| `volume_style_preference` | enum | `low_volume_high_freq` / `standard` / `high_volume_low_freq` (§6.2) |
| `long_swim_format_preference` | enum | `continuous` / `ultra_long_intervals` / `user_choice_per_block` (§11.4) |
| `preferred_session_types` | list[SwimmingSessionType] | Préférences par type (§8.2 critère 4) |
| `avoided_movements` | list[str] | Mouvements à éviter par préférence (complément contre-indications §13) |
| `stroke_coefficients` | dict[SwimmingStroke, float] | Coefficients personnalisés par nage si historique suffisant (§9.5) |
| `swolf_baseline` | int | SWOLF baseline user (§14.3) |
| `preferred_equipment` | list[str] | pull_buoy / kickboard / paddles / fins / snorkel — présence équipement |

**Résolution proposée** : B1 v2 ajoute ces champs en tant que `ExperienceProfile.swimming.preferences` (sous-modèle Pydantic optionnel) + `css_current` / `css_history` en champs top-level.

**Impact rédaction C6** : tout le prompt Swimming référence ces champs. §7.1, §8.2, §9.5, §11.5, §14.3 explicitement.

**Liens connexes** : DEP-C5-003, DEP-C5-006, DEP-C4-002.

---

### DEP-C6-004 — `PrescribedSwimmingSession` + enums Swimming en B3 v2

**Source** : session C6, rédaction `swimming-coach.md` §2.2, §8.1, §8.3, §9.3, §16.2, §17.

**Contexte** :
- B3 v1 ne spécifie pas `PrescribedSwimmingSession`, `SwimmingIntensitySpec`, `SwimmingZone`, `SwimmingSessionType`, `SwimmingStroke`, `SwimmingTerrain`, `SwimmingSetBlock`.
- Pattern symétrique B3 §3.3 `PrescribedRunningSession` (DEP-C5-004) et §3.2 `PrescribedLiftingSession` (DEP-C4-003).

**Résolution proposée** : B3 v2 ajoute :
- `PrescribedSwimmingSession` (B3 §3.4 à introduire) avec champs §8.3
- `SwimmingIntensitySpec` (§9.3) avec champs zone_primary, target_pace_per_100m, pace_tolerance, target_rpe_range, stroke, terrain
- `SwimmingSetBlock` (§8.3) avec phase (warmup/main/cooldown/drill_insert/transition), repetitions, distance_m, target_pace, rest_spec, stroke, drill_variant, equipment
- `SwimmingZone` enum (Z1-Z5) §9.3
- `SwimmingSessionType` enum (10 valeurs) §8.1 / §17.1
- `SwimmingStroke` enum §17.3
- `SwimmingTerrain` enum §17.4

**Impact rédaction C6** : §2.2, §8, §9.3, §16.2, §17 présupposent cette extension. Rédaction cohérente avec PrescribedRunningSession / PrescribedLiftingSession.

**Liens connexes** : DEP-C5-004, DEP-C4-003.

---

### DEP-C6-005 — Harmonisation `SwimmingLoadPayload` + extension `RecommendationMode.INTERPRETATION` en B3 v2

**Source** : session C6, rédaction `swimming-coach.md` §2.2, §15.4, §20.4, §21.3.

**Contexte (partie A — SwimmingLoadPayload)** :
- §15.4 C6 propose la structure `SwimmingLoadPayload` à émettre (weekly_volume_m, weekly_duration_min, weekly_tss_projected, quality_sessions, long_swim, shoulder_load_score, leg_impact_score, cns_load_score, acwr_projected, terrain_distribution).
- Pattern symétrique à Running (`RunningLoadPayload` via DEP-C5-007) et Lifting (`LiftingLoadPayload` via DEP-C4-004), à formaliser dans Union type `projected_strain_contribution`.

**Contexte (partie B — contrat léger INTERPRETATION)** :
- §2.2, §20.4, §21.3 C6 posent que le mode INTERPRETATION Swimming produit un contrat **léger sans `sessions`, sans `block_theme`, sans `projected_strain_contribution`** — uniquement `notes_for_head_coach` + éventuel `flag_for_head_coach`.
- B3 v1 validators REC1-REC13 + REC-F peuvent interdire ce contrat léger (jumelle DEP-C5-008 Running et DEP-C4-006 Lifting).

**Résolution proposée** :
- Partie A : B3 v2 formalise `SwimmingLoadPayload` dans l'Union type `projected_strain_contribution` aux côtés de `RunningLoadPayload`, `LiftingLoadPayload`, `BikingLoadPayload` (C7 à venir). Schéma commun minimal harmonisé.
- Partie B : B3 v2 étend validator pour autoriser le contrat léger en mode INTERPRETATION — résolu conjointement avec DEP-C5-008 et DEP-C4-006 (triplet identique côté 3 coachs disciplines endurance + lifting).

**Impact rédaction C6** : §15.4 documente la structure attendue côté Swimming. §2.2, §20, §21 présupposent l'extension INTERPRETATION.

**Liens connexes** : DEP-C5-007, DEP-C4-004, DEP-C5-008, DEP-C4-006.

---

### DEP-C6-006 — Bibliothèque `swimming_plan_templates` en Phase D

**Source** : session C6, rédaction `swimming-coach.md` §8.5, §17.5.

**Contexte** :
- La bibliothèque concrète de templates de séances swimming (drills nommés avec structure canonique, variantes par niveau, exemples d'ensembles techniques, structures threshold sets prouvées, formats test set) relève de Phase D.
- Pattern symétrique `running_plan_templates` (Running Phase D) et `lifting_plan_templates` (Lifting Phase D).

**Résolution proposée** : Phase D implémente `swimming_plan_templates` en DB structurée avec :
- Liste exhaustive `SwimmingDrillVariant` (§17.5 liste indicative V1 à étendre)
- Templates de structures canoniques par `SwimmingSessionType` × niveau (beginner / intermediate / advanced / competitive)
- Variantes fly-less / breaststroke-less / kick-only / pull-only pour dégradation (§13.3)

**Impact rédaction C6** : §8.5, §17.5 renvoient explicitement à cette dépendance Phase D.

---

### DEP-C7-001 — Harmonisation `BikingLoadPayload` + extension `RecommendationMode.INTERPRETATION` en B3 v2

**Source** : session C7, rédaction `biking-coach.md` §2.2, §15.5, §20.3, §20.4.

**Contexte (partie A — BikingLoadPayload)** :
- §15.5 C7 propose la structure `BikingLoadPayload` à émettre (weekly_tss_projected, weekly_duration_min, weekly_distance_km, quality_sessions_count, long_ride, leg_impact_score, cns_load_score, acwr_projected, terrain_distribution, aero_position_hours).
- Pattern symétrique à Running (`RunningLoadPayload` via DEP-C5-007), Swimming (`SwimmingLoadPayload` via DEP-C6-005), Lifting (`LiftingLoadPayload` via DEP-C4-004), à formaliser dans Union type `projected_strain_contribution`.
- Spécificité biking : `aero_position_hours` exposé séparément pour consommation Recovery (charge cou/cervical/lombaire §15.6).

**Contexte (partie B — contrat léger INTERPRETATION)** :
- §20.3, §20.4 C7 posent que le mode INTERPRETATION Biking produit un contrat **léger sans `sessions`, sans `block_theme`, sans `projected_strain_contribution`** — uniquement `notes_for_head_coach` + `verdict` + `evidence_summary` + éventuel `flag_for_head_coach`.
- B3 v1 validators REC1-REC13 + REC-F peuvent interdire ce contrat léger (jumelle DEP-C5-008 Running, DEP-C6-005 Swimming, DEP-C4-006 Lifting).

**Résolution proposée** :
- Partie A : B3 v2 formalise `BikingLoadPayload` dans l'Union type `projected_strain_contribution` aux côtés de `RunningLoadPayload`, `SwimmingLoadPayload`, `LiftingLoadPayload`. Schéma commun minimal harmonisé + champ biking-specific `aero_position_hours`.
- Partie B : B3 v2 étend validator pour autoriser le contrat léger en mode INTERPRETATION — résolu conjointement avec DEP-C5-008, DEP-C6-005 et DEP-C4-006 (quadruplet identique côté 4 coachs disciplines physiques).

**Impact rédaction C7** : §15.5 documente la structure attendue. §2.2, §20, §21 présupposent l'extension INTERPRETATION.

**Liens connexes** : DEP-C5-007, DEP-C6-005, DEP-C4-004, DEP-C5-008, DEP-C4-006.

---

### DEP-C7-002 — Type `RestrictPosition` en recovery-coach v2 + B3 v2

**Source** : session C7, rédaction `biking-coach.md` §13.1, §13.2.3, §13.2.4.

**Contexte** :
- Recovery v1 (C3) expose 3 types de restrictions : `ForbiddenMovement`, `RestrictIntensity`, `RestrictDuration`.
- Biking nécessite une dimension de restriction supplémentaire — la **position sur le vélo** (regular / drops / aero). Cas récurrents : cou/cervical aigu → interdiction position aéro ; lombaire bas → interdiction drops prolongés ; sortie de contre-indication lombaire → retour progressif aéro interdit.
- §13.2.3 (cou/cervical) et §13.2.4 (selle/périnée) du prompt Biking consomment implicitement cette restriction.
- Pas d'équivalent dans Running / Swimming / Lifting → dimension 100 % biking-specific.

**Résolution proposée** :
- Recovery v2 ajoute le type de restriction `RestrictPosition` avec valeurs `{allowed_positions: list[BikingPosition], forbidden_positions: list[BikingPosition], duration_days, rationale}`.
- B3 v2 formalise ce nouveau type dans le schéma de `ContraindicationSet` consommé par Biking.

**Impact rédaction C7** : §13.1 documente ce type comme DEP ouverte. §13.2.3 / §13.2.4 / §11.7 présupposent sa disponibilité.

**Liens connexes** : DEP-C7-003, DEP-C7-004 (même mécanique d'extension, dimensions biking-specific).

---

### DEP-C7-003 — Type `RestrictTerrain` en recovery-coach v2 + B3 v2

**Source** : session C7, rédaction `biking-coach.md` §13.1, §13.2.5.

**Contexte** :
- Biking nécessite une restriction de **terrain** (indoor / road / gravel / mtb). Cas classique : poignet aigu (syndrome canal carpien cycliste) → interdiction gravel et MTB (vibrations aggravantes), obligation road/indoor.
- Dimension spécifique biking — Running a une notion de terrain (route/trail/piste) mais sans équivalent clinique structuré en Recovery v1.
- §13.2.5 (poignet) consomme implicitement cette restriction.

**Résolution proposée** :
- Recovery v2 ajoute le type `RestrictTerrain` avec `{allowed_terrains: list[BikingTerrain], forbidden_terrains: list[BikingTerrain], duration_days, rationale}`.
- B3 v2 formalise ce type.

**Impact rédaction C7** : §13.1 documente comme DEP ouverte. §13.2.5 présuppose sa disponibilité.

**Liens connexes** : DEP-C7-002, DEP-C7-004.

---

### DEP-C7-004 — Type `RestrictCadence` en recovery-coach v2 + B3 v2

**Source** : session C7, rédaction `biking-coach.md` §13.1, §13.2.1, §13.2.6.

**Contexte** :
- Biking nécessite une restriction de **cadence** (plancher et/ou plafond rpm). Cas classique : genou aigu (tendinite rotulienne, SFP) → cadence plancher ≥ 85 rpm obligatoire, suppression climbing à cadence basse.
- Dimension 100 % biking-specific — pas d'équivalent Running (foot strike rate informatif), Swimming (stroke rate n'est pas une restriction clinique mais un signal technique), Lifting (N/A).
- §13.2.1 (genou) et §13.2.6 (cheville/pied) consomment cette restriction.

**Résolution proposée** :
- Recovery v2 ajoute le type `RestrictCadence` avec `{cadence_floor_rpm: int | null, cadence_ceiling_rpm: int | null, duration_days, rationale}`.
- B3 v2 formalise ce type.

**Impact rédaction C7** : §13.1 documente comme DEP ouverte. §13.2.1 / §13.2.6 présupposent sa disponibilité.

**Liens connexes** : DEP-C7-002, DEP-C7-003.

---

### DEP-C7-005 — `PrescribedBikingSession` + enums biking en B3 v2

**Source** : session C7, rédaction `biking-coach.md` §2.2, §5.2, §8.1, §9, §17.

**Contexte** :
- B3 v1 ne spécifie pas `PrescribedBikingSession`, `BikingIntensitySpec`, `BikingSessionType`, `BikingTerrain`, `BikingPosition`, `BikingZone`, `BikingIntensityMode`, `FTPTestProtocol`, `FTPRecalibrationSource`.
- Pattern symétrique B3 `PrescribedRunningSession` (DEP-C5-004), `PrescribedSwimmingSession` (DEP-C6-004), `PrescribedLiftingSession` (DEP-C4-003).

**Résolution proposée** : B3 v2 ajoute :
- `PrescribedBikingSession` (B3 §3.5 à introduire) avec champs §17.3.
- `BikingIntensitySpec` (§17.2) avec champs `mode`, `power_target_watts`, `ftp_pct_target`, `hr_target_bpm`, `rpe_target`, `cadence_target_rpm`. Structure à slot conditionnel — `power_target_watts` et `ftp_pct_target` nullables selon `mode`.
- `BikingSessionType` enum (13 valeurs) §8.1 / §17.1.
- `BikingTerrain` enum (4 valeurs) §17.1.
- `BikingPosition` enum (3 valeurs) §17.1.
- `BikingIntensityMode` enum (3 valeurs) §17.1 — `power_primary` | `hr_primary` | `rpe_only`.
- `BikingVerdict` enum (5 valeurs) §17.1.
- `BikingFlagType` enum (8 valeurs V1) §17.1.
- `FTPTestProtocol` enum (2 valeurs) §17.1.
- `FTPRecalibrationSource` enum (3 valeurs) §17.1.
- Champ `ftp_update` dans `Recommendation` (§12.7) pour communiquer FTP mis à jour.

**Impact rédaction C7** : §2.2, §5.2, §8, §9, §12.7, §17 présupposent cette extension. Rédaction cohérente avec les 3 autres coachs disciplines.

**Liens connexes** : DEP-C5-004, DEP-C6-004, DEP-C4-003.

---

### DEP-C7-006 — Collecte équipement vélo en onboarding + exposition dans AthleteState

**Source** : session C7, rédaction `biking-coach.md` §2.3, §9.1, §22.

**Contexte** :
- Cascade Biking §9 conditionnelle à l'équipement déclaré : `user_equipment.power_meter_present`, `user_equipment.smart_trainer_present`, `user_equipment.bike_types` (road/gravel/mtb/indoor_only), `user_equipment.aero_bars_available`.
- Onboarding Coach (C2) v1 ne détaille pas la collecte de l'équipement vélo à ce niveau de granularité.
- AthleteState v1 ne formalise pas un champ `user_equipment.biking` structuré.

**Résolution proposée** :
- Onboarding v2 ajoute un bloc de questions équipement biking si user déclare vélo actif (power meter oui/non → si oui type ; smart trainer oui/non → si oui marque/modèle pour calibration précision ; types de vélos possédés ; aero bars / TT bike oui/non).
- B1/B2 v2 formalisent la structure `UserEquipment.biking` dans AthleteState.
- B2 v2 inclut ces champs dans la `BikingCoachView`.

**Impact rédaction C7** : §2.3 présuppose ces champs dans la vue filtrée. §9.1 utilise `power_meter_present` + `smart_trainer_present` pour activer/désactiver le slot Power. §22 table d'injection liste ces champs.

**Liens connexes** : Onboarding C2, B1/B2 v1.

---

## Propagation des décisions cross-agents (statut après C6)

Récapitulatif des 4 décisions cross-agents propagées pendant la session C6 :

### DEC-C3-001 — Primauté du déclaratif utilisateur sur signaux objectifs

**Application Swimming** : §3.3 / TR2 (RPE prime sur toutes zones Z1-Z5 en swimming — rôle HR supprimé de la cascade en raison de sa faible fiabilité hydrostatique §9.2) et §14.4 (3 protections adaptées swimming — seuils pace absolus remplacent la protection « cohérence HR/pace » de Running, pattern persistant 14j avec flag `OBJECTIVE_SUBJECTIVE_DISSONANCE_PATTERN`, `monitor_signals` explicite). Cas ORL (otite/sinusite) traité comme application directe DEC-C3-001 — coach propose adaptation volume/intensité, user arbitre tolérance (§13.2).

**Statut propagation** : ✅ C6 appliqué. Reste à propager C7, C8, C9.

### DEC-C4-001 — Pattern de consultation conditionnelle disciplinaire en chat

**Application Swimming** : §2.4 (4 triggers Swimming dont 2 conditionnels — `CHAT_SESSION_LOG_INTERPRETATION` et `CHAT_TECHNICAL_QUESTION_SWIMMING`). **Seuils progressifs** validés Bloc 1 C6 (décision produit Simon-Olivier alignée Running) : tolérants 1 séance isolée, stricts pattern 2-3 séances consécutives. Seuils chiffrés table §2.4 : pace écart ≥ +5 sec/100m Z3+ ou ≥ +10 sec/100m Z1-Z2, distance < 75 %, RPE écart ≥ +1.5 ou +1 pattern, **SWOLF dégradé ≥ +10 % conditionnel à la disponibilité du tracking** (décision Bloc 1 Simon-Olivier), red flag immédiat. §20 et §21 traitent les 2 triggers conditionnels avec note de dépendance DEP-C6-002.

**Statut propagation** : ✅ C6 appliqué. Reste à propager C7, C8 (à évaluer), C9 (à évaluer).

### DEC-C4-002 — Trade-off prescriptif formulé en impact temporel

**Application Swimming** : §3.4 / TR3 (impact temporel avec ordres de grandeur), exemples dans §6.2 (TID), §12 (5 cas dégradation gracieuse), §15.3 (arbitrage cross-discipline palier 2). Format *« atteinte objectif étirée d'environ X-Y % »* appliqué systématiquement.

**Statut propagation** : ✅ C6 appliqué. Reste à propager C7, C8, C1 (rétrospectivement à évaluer).

### DEC-C4-003 — Toujours prescrire, jamais refuser, traçabilité obligatoire

**Application Swimming** : §3.5 / TR4 (ventilation canaux trade-off / notes_for_head_coach / flag) + §12 (5 cas dégradation gracieuse swimming : forbid total immersion, restriction partielle non satisfaisable, équipement/connecteur absent, terrain indisponible, objectif mal défini). Mode INTERPRETATION "verdict no_action" documenté §14.2 et §2.5 pour traçabilité silencieuse.

**Statut propagation** : ✅ C6 appliqué. Reste à propager C7, C8.

---

## Delta index — session C6

### Ajout dans "Index par session"

| Session | DEP IDs | Résolus ? |
|---|---|---|
| C6 | DEP-C6-001, DEP-C6-002, DEP-C6-003, DEP-C6-004, DEP-C6-005, DEP-C6-006 | ouvertes |

### Ajout dans "Index par cible de résolution"

| Cible | DEP-C6-* ajoutées |
|---|---|
| A2 v2 | DEP-C6-002 |
| B1 v2 | DEP-C6-003 |
| B2 v2 | DEP-C6-001 |
| B3 v2 | DEP-C6-004, DEP-C6-005 |
| Phase D | DEP-C6-006 |

### Mise à jour "Index décisions structurantes" (statut post-C6)

| ID | Source | Sessions affectées | Statut propagation post-C6 |
|---|---|---|---|
| DEC-C3-001 | C3 Recovery | C4 (✓), C5 (✓), **C6 (✓)**, C7, C8, C9 | Partiellement propagée |
| DEC-C4-001 | C4 Lifting | C5 (✓), **C6 (✓)**, C7, C8 (à évaluer), C9 (à évaluer) | Partiellement propagée |
| DEC-C4-002 | C4 Lifting | C5 (✓), **C6 (✓)**, C7, C8, C1 (rétrospectivement à évaluer) | Partiellement propagée |
| DEC-C4-003 | C4 Lifting | C5 (✓), **C6 (✓)**, C7, C8 | Partiellement propagée |

---

## Propagation des décisions cross-agents (statut après C7)

Récapitulatif des 4 décisions cross-agents propagées pendant la session C7 :

### DEC-C3-001 — Primauté du déclaratif utilisateur sur signaux objectifs

**Application Biking** : §3.1 / TR (RPE prime sur Power et FC observés dans la cascade §9 — les deux axes objectifs biking) et §14.1 (application au niveau du log individuel). **3 protections adaptées biking** : (i) seuils absolus Power/FC (cohérence physique), (ii) pattern persistant 14 j → flag `OBJECTIVE_SUBJECTIVE_DISSONANCE_PATTERN` §16.1, (iii) `monitor_signals` explicite dans `notes_for_head_coach`. Spécificité biking : cascade conditionnelle §9.1 (Power slot activé/désactivé selon équipement) modifie la structure des axes objectifs mais n'altère pas la primauté RPE.

**Statut propagation** : ✅ C7 appliqué. Reste à propager C8, C9.

### DEC-C4-001 — Pattern de consultation conditionnelle disciplinaire en chat

**Application Biking** : §2.2 (4 triggers Biking dont 2 conditionnels — `CHAT_SESSION_LOG_INTERPRETATION` et `CHAT_TECHNICAL_QUESTION_BIKING`). **Seuils progressifs** validés Bloc 1 C7 (décision produit Simon-Olivier, alignée Running/Swimming) : tolérants 1 séance isolée, stricts pattern 2-3 séances consécutives. Seuils chiffrés §14.2 différenciés selon équipement : (avec power meter) écart NP ≥ ±8 % isolé ou ±5 % pattern, écart IF ≥ ±0.05 isolé ou ±0.03 pattern, écart TSS ≥ ±20 %, durée < 80 %, RPE ≥ +1.5 isolé ou +1 pattern ; (sans power meter) FC hors zone > 10-20 % temps, durée < 80 %, RPE idem, red flag. **Exception biking-specific validée Bloc 1** : abandon logistique outdoor déclaré (crevaison, orage, mécanique, route fermée) → verdict `no_action` direct sans consultation (§14.2 + §20.5). §20 et §21 traitent les 2 triggers conditionnels avec note de dépendance DEP-C7-001.

**Statut propagation** : ✅ C7 appliqué. Reste à propager C8 (à évaluer), C9 (à évaluer).

### DEC-C4-002 — Trade-off prescriptif formulé en impact temporel

**Application Biking** : §3.3 / TR (impact temporel avec ordres de grandeur chiffrés), exemples dans §15.3 (auto-adaptation silencieuse face à `lifting_load.leg_volume_score`) et §12.4 (proposition test FTP formel avec fenêtre recommandée). Cas spécifique biking : arbitrage test FTP en BUILD avec dérive >5 % formulé en "cycle 8-12 semaines" plutôt qu'en "nécessité urgente".

**Statut propagation** : ✅ C7 appliqué. Reste à propager C8, C1 (rétrospectivement à évaluer).

### DEC-C4-003 — Toujours prescrire, jamais refuser, traçabilité obligatoire

**Application Biking** : §3.4 / TR (ventilation canaux trade-off / notes_for_head_coach / flag) + §13.3 (cascade d'adaptation 6 étapes face contre-indications, avec fallback ultime `sessions: []` + flag `MEDICAL_NEED_CROSS_TRAINING` + notes explicites). Cas dégradation gracieuse biking : (i) contre-indication totale 6 zones anatomiques §13.2, (ii) équipement insuffisant → cascade §9.3 dégradée FC primaire, (iii) auto-adaptation lifting leg day §15.3, (iv) sortie de contre-indication progressive §13.4, (v) long ride plafonné selon contre-indication §11.7, (vi) Tracking Only mode avec plan externe non modifiable §18.5. Mode INTERPRETATION verdict `no_action` documenté §14.3 et §20.5 pour traçabilité silencieuse.

**Statut propagation** : ✅ C7 appliqué. Reste à propager C8.

---

## Delta index — session C7

### Ajout dans "Index par session"

| Session | DEP IDs | Résolus ? |
|---|---|---|
| C7 | DEP-C7-001, DEP-C7-002, DEP-C7-003, DEP-C7-004, DEP-C7-005, DEP-C7-006 | ouvertes |
| C8 | DEP-C8-001, DEP-C8-002, DEP-C8-003, DEP-C8-004, DEP-C8-005, DEP-C8-006, DEP-C8-007, DEP-C8-008, DEP-C8-009 | ouvertes |

### Ajout dans "Index par cible de résolution"

| Cible | DEP-C8-* ajoutées |
|---|---|
| A2 v2 | DEP-C8-002 (`build_nutrition_view`), DEP-C8-008 (`adjust_nutrition_targets_daily`) |
| B2 v2 | DEP-C8-002 (`NutritionCoachView`) |
| B3 v2 | DEP-C8-001 (extension validator quintuplet INTERPRETATION léger), DEP-C8-003 (harmonisation canaux fueling, optionnel), DEP-C8-004 (type `UserOnboardingQuery`) |
| head-coach v2 | DEP-C8-005 (`activate_nutrition_clinical_frame` Option B), DEP-C8-004 (mécanique dispatch `UserOnboardingQuery` + persistance préférences) |
| Onboarding v2 | DEP-C8-006 (collecte `user.nutrition_preferences` étendue) |
| Phase D | DEP-C8-007 (interface logging V1 : texte libre LLM + scan code-barres + repas habituels V1.1), DEP-C8-009 (bibliothèque `nutrition_database` FCÉN/USDA/OFF, FatSecret rejeté) |

### Mise à jour "Index décisions structurantes" (statut post-C8)

| ID | Source | Sessions affectées | Statut propagation post-C8 |
|---|---|---|---|
| DEC-C3-001 | C3 Recovery | C4 (✓), C5 (✓), C6 (✓), C7 (✓), **C8 (✓)**, C9 | Largement propagée |
| DEC-C4-001 | C4 Lifting | C5 (✓), C6 (✓), C7 (✓), **C8 (✓ — 4 triggers §2.1, ajustements quotidiens déterministes hors LLM)**, C9 (à évaluer) | Largement propagée |
| DEC-C4-002 | C4 Lifting | C5 (✓), C6 (✓), C7 (✓), **C8 (✓ — formulation impact temporel non-moralisant §3.3, vocabulaire interdit §3.5)**, C1 (rétrospectivement à évaluer) | Largement propagée |
| DEC-C4-003 | C4 Lifting | C5 (✓), C6 (✓), C7 (✓), **C8 (✓ — toujours prescrire même refus user, §3.4)** | Largement propagée |

---

## Session C8 — Nutrition Coach (post-C8 ✓)

**Livré** : `nutrition-coach.md` v1 (Phase C, session C8). Spécialiste cross-disciplines consommant les flags fueling de Running, Biking, Swimming, Lifting et émettant `Recommendation` nutritionnel + payload `NutritionLoadPayload` consommable Energy C9.

### DEP-C8-001 — Extension validator B3 v2 quintuplet INTERPRETATION léger

**Cible** : `B3 §5` (validator `Recommendation`)
**Description** : Étendre le contrat léger mode INTERPRETATION (champs minimaux : `verdict`, `evidence_summary`, `flag_for_head_coach` optionnel, `notes_for_head_coach`) au cinquième agent — Nutrition. Forme quintuplet avec DEP-C5-008 (Running), DEP-C6-005 (Swimming), DEP-C7-001 (Biking), DEP-C4-006 (Lifting).
**Validations spécifiques Nutrition** : `daily_targets` absent en INTERPRETATION, `evidence_summary` ≤ 300 chars, `notes_for_head_coach` ≤ 500 chars + linter dictionnaire mots-bannis (vocabulaire §3.5 Nutrition).
**Statut** : ouverte.

### DEP-C8-002 — `NutritionCoachView` (B2 v2) + node `build_nutrition_view` (A2 v2)

**Cible** : `B2 v2` (vue filtrée) + `A2 v2` (node Coordinator)
**Description** : Définir la vue filtrée `NutritionCoachView` (champs §2.2 + §21 du prompt Nutrition) et le node non-LLM `build_nutrition_view` qui agrège les trois canaux hétérogènes de signalement fueling (héritage C4-C7) en une structure unifiée `upcoming_fueling_events: list[FuelingEvent]` :
- Canal 1 : flags structurés (`NUTRITION_FUELING_NEEDED_LONG_RIDE` Biking C7, `NUTRITION_FUELING_NEEDED_SWIM` Swimming C6)
- Canal 2 : champs payload (`projected_nutrition_needs` dans `running_load` / `biking_load` / `swimming_load` / `lifting_load`)
- Canal 3 : mentions textuelles dans `notes_for_head_coach` des coachs disciplines (heuristique regex/LLM-light, héritage Running C5 §11.3 sans flag structuré)
**Statut** : ouverte. **Bloquante** pour implémentation Nutrition Phase D.

### DEP-C8-003 — Harmonisation canaux fueling (B3 v2, optionnel rétroactif)

**Cible** : `B3 v2` + retrofit possible C5 Running, ajout possible C4 Lifting
**Description** : Introduire un `FlagCode.NUTRITION_FUELING_NEEDED` générique avec payload discriminé par discipline (`fueling_event_type: enum`, `discipline: enum`, `projected_duration_min`, `projected_intensity_zone`, `projected_thermal_conditions`). Permet retrofit Running (remplacer signalement via notes par flag structuré) et ajout Lifting (fueling séances compétition force/powerlifting si V2 le justifie). **Non-bloquante V1** — `build_nutrition_view` (DEP-C8-002) absorbe l'hétérogénéité actuelle.
**Statut** : ouverte (priorité basse, V2 envisageable).

### DEP-C8-004 — Type `UserOnboardingQuery` (B3 v2) + mécanique dispatch Head Coach

**Cible** : `B3 v2` (type contrat) + `head-coach v2` (mécanique dispatch + persistance préférences)
**Description** : Formaliser le type `UserOnboardingQuery` (cf. §16.4-bis prompt Nutrition) émis par Nutrition dans son `Recommendation` pour permettre à Head Coach de poser des questions user et persister les réponses comme préférences durables (`supplementation_opt_in`, `food_suggestions_opt_in_current_plan`, `carb_loading_opt_out`, etc.). Mécanique dispatch Head Coach : reformulation question en façade, persistance réponse dans `user.nutrition_preferences`, suppression de la query des recommendations suivantes.
**Pattern réutilisable** : Recovery Coach pourrait initier des questions similaires (tolérance douleur, consentement clinical frame), Energy Coach sur sommeil/récupération subjective. À évaluer pour propagation transversale post-C9.
**Statut** : ouverte.

### DEP-C8-005 — Mécanique `activate_nutrition_clinical_frame` Head Coach C1 v2 (Option B RED-S)

**Cible** : `head-coach v2`
**Description** : Mécanique de cadre clinique nutrition activée à réception flag `MEDICAL_ESCALATION_RED_S_SUSPECTED` (severity CRITICAL). Exécution Option B en deux temps :
1. **Étape 1** — Check-in empathique non-intrusif (« Comment tu te sens côté énergie, motivation, sommeil ? »)
2. **Étape 2a** (user confirme malaise) → orientation OPDQ pour diététiste-nutritionniste sport, mention médecin sport-santé pour bilan biologique
3. **Étape 2b** (user nie/minimise) → préférence persistée `nutrition_red_s_checkin_declined_${date}`, **aucune relance avant 4 semaines minimum** (règle anti-insistance dure)

Distinction stricte avec mécanisme Recovery `activate_clinical_frame` (blessures musculo-squelettiques). Distinction stricte avec orientation TCA (cf. §4.5 prompt Nutrition — ressource ANEB Québec uniquement sur déclaration user explicite via flag `USER_DECLARED_CLINICAL_NUTRITION_CONDITION`).
**Statut** : ouverte. **Bloquante** pour scenarios RED-S Phase D.

### DEP-C8-006 — Onboarding Coach v2 : collecte `user.nutrition_preferences` étendue

**Cible** : `onboarding-coach v2`
**Description** : Étendre la collecte onboarding initial pour intégrer les champs `user.nutrition_preferences` :
- `diet_pattern` enum : omnivore / pescetarian / vegetarian / vegan / flexitarian / other
- `religious_dietary` enum list : halal / kosher / none / other
- `allergies` list[str], `intolerances` list[str], `dislikes` list[str]
- `budget_sensitivity` enum : standard / budget_conscious / premium_ok
- `cooking_capacity` enum : minimal / moderate / full_kitchen
- `body_weight_tracking_active` bool (défaut selon `primary_goal`)
- `supplementation_opt_in` bool (collecté par premier UserOnboardingQuery Nutrition, persisté ensuite — peut être collecté upfront onboarding aussi)
- `food_suggestions_opt_in_current_plan` bool (collecté par UserOnboardingQuery EACH_PLAN_GEN)
- `carb_loading_opt_out` bool (collecté par UserOnboardingQuery sur première détection event compétitif éligible)
- Champs `updatable` via TECHNICAL (user peut dire « je suis devenu végane »).
**Statut** : ouverte.

### DEP-C8-007 — Interface logging V1 (Phase D)

**Cible** : `Phase D` (frontend + backend logging)
**Description** : Interfaces de logging alimentaire user-facing V1 avec philosophie anti-friction (cf. §3.6 prompt Nutrition — six règles AF) :
- **V1** : texte libre + parsing LLM via base canonique (FCÉN/USDA/OFF) + scan code-barres produits emballés
- **V1.1** : repas habituels auto-appris (après 2-3 semaines patterns récurrents reconnus, user signale en 1 clic)
- **V2** : photo repas (vision LLM), commande vocale
- Acceptation logs approximatifs sans relance (AF6), pas de gamification punitive (AF5), absence de log = pas de jugement (AF1)
**Statut** : ouverte.

### DEP-C8-008 — Node backend non-LLM `adjust_nutrition_targets_daily` (A2 v2)

**Cible** : `A2 v2` (node Coordinator)
**Description** : Node déterministe non-LLM exécuté quotidiennement (typiquement fin de journée ou début journée suivante) qui ajuste les `kcal_target_jour` selon :
- NEAT réel du jour (pas/jour mesuré vs estimé)
- EAT réel du jour (séance réalisée vs prévue, payload coach discipline)
- Règles de modulation glucides définies dans `DailyNutritionTarget.carb_modulation_rules` (§16.4 prompt Nutrition)

**Critique** : ce node ne réinvoque **jamais** Nutrition LLM. La direction stratégique (ratios macros, fenêtres, micronutriments) reste fixée par Nutrition LLM en mode PLANNING/REVIEW. Le node ne fait qu'appliquer mécaniquement les règles préconfigurées.
**Statut** : ouverte. **Bloquante** pour respect AF1/AF4 (anti-friction logging via données passives priment).

### DEP-C8-009 — Bibliothèque `nutrition_database` (Phase D)

**Cible** : `Phase D` (backend infrastructure)
**Description** : Bibliothèque agrégeant les bases nutritionnelles canoniques avec ordre de priorité résolution (cf. §4.8 prompt Nutrition) :
- **Priorité 1** : FCÉN (Fichier canadien sur les éléments nutritifs, Santé Canada) — aliments disponibles au Canada
- **Priorité 2** : USDA FoodData Central — couverture internationale, granularité élevée
- **Priorité 3** : Open Food Facts — produits emballés (scan code-barres) collaboratif
- **Rejeté** : FatSecret (qualité données variable, biais commerciaux)

Sert à : parsing logs alimentaires user (DEP-C8-007), génération `suggested_food_items` (§8 prompt Nutrition), scoring micronutriments (§6.5), validation cohérence kcal/macros prescrits.

Granularité V1 : qualitatif (alertes patterns micronutriments). V2 : scoring quantitatif quotidien complet via FCÉN.
**Statut** : ouverte.

### Notes inter-coach C8

**Distinction stricte RED-S (§13) vs TCA (§4.5)** : Nutrition détecte activement RED-S selon seuils objectifs et combinatoires (apport vs TDEE × durée + cumul signaux Recovery/Energy) → flag `MEDICAL_ESCALATION_RED_S_SUSPECTED` → Option B Head Coach. Nutrition ne détecte **jamais** activement les troubles du comportement alimentaire (TCA) → seul flag possible `USER_DECLARED_CLINICAL_NUTRITION_CONDITION` sur déclaration user explicite → orientation immédiate ressources externes ANEB Québec + OPDQ. Aucun pattern matching diagnostique TCA dans le prompt Nutrition (décision produit Simon-Olivier C8 — TCA hors scope app).

**Audit canaux fueling C4-C7** : Running C5 signale fueling via `notes_for_head_coach` + `running_load.projected_nutrition_needs` (pas de flag structuré). Biking C7 §16.1 signale via flag structuré `NUTRITION_FUELING_NEEDED_LONG_RIDE`. Swimming C6 signale via flag structuré `NUTRITION_FUELING_NEEDED_SWIM`. Lifting C4 ne signale aucun fueling V1 (questions ad-hoc routées TECHNICAL Head Coach). Hétérogénéité absorbée par DEP-C8-002 (`build_nutrition_view`), retrofit optionnel possible via DEP-C8-003.

**Ajout au tableau "Index par session"**

| Session | DEP créées | Statut |
|---|---|---|
| C8 | DEP-C8-001 à DEP-C8-009 (9 DEP) | ouvertes |

---

## Ouvertures vers C9-C10

**C9 Energy Coach V3** — consomme `leg_impact_score`, `shoulder_load_score`, `cns_load_score`, `acwr_projected` des payloads running/swimming/biking/lifting pour détection surcharge énergétique globale. **Consomme aussi `NutritionLoadPayload` émis par Nutrition C8** (§16.5 prompt Nutrition) avec champs `daily_energy_balance_7d_kcal`, `red_s_risk_level`, `protein_sufficiency_score`, `carb_sufficiency_score`, `hydration_sufficiency_score` — coordination clinique forte sur déficit énergétique chronique (RED-S contribue au signal `cns_load_score` Energy). Applique DEC-C3-001 sur `user_energy_signal` vs `objective_energy_availability`. Position aéro biking (`aero_position_hours` C7) comptabilisée séparément. Pattern UserOnboardingQuery (DEP-C8-004) potentiellement réutilisable pour collecte sommeil subjectif / fatigue.

**C10 `classify_intent`** — gating mode TECHNICAL pour Nutrition (`CHAT_TECHNICAL_QUESTION_NUTRITION`, §20.1 prompt Nutrition). Reconnaître questions techniques nutrition non-triviales : suppléments individuels (créatine, vit D, fer, oméga-3, caféine), régimes alternatifs (keto, IF, vegan competitive), aliments spécifiques densité nutritionnelle, timing pré/post-événement spécifique, carences ressenties (sans diagnostic). Questions triviales (« calories d'une banane ») restent Head Coach direct via base canonique. Reconnaître également déclarations utilisateur explicites suggérant TCA → routing immédiat vers flag `USER_DECLARED_CLINICAL_NUTRITION_CONDITION` (cf. §4.5 prompt Nutrition règle 2). Reconnaître intent **« je veux des idées de repas »** comme TECHNICAL Nutrition (réponse ad-hoc Head Coach après consultation Nutrition, sans prescription menu structuré V1).

---

## Propagation des décisions cross-agents (statut après C9)

### DEC-C3-001 — Primauté du déclaratif utilisateur sur signaux objectifs

**Statut** : appliqué C3 (initial) ✓ | C4 ✓ | C5 ✓ | C6 ✓ | C7 ✓ | C8 ✓ | **C9 ✓** (§3.1 propagation Energy : déclaratif fatigue prime sur métriques calculées, hiérarchie de fiabilité §7.5, flag `OBJECTIVE_SUBJECTIVE_ENERGY_DISSONANCE` sur dissonance persistante > 14 jours, mode protection léger en background si user nie cadre clinique surentraînement)

### DEC-C4-001 — Pattern de consultation conditionnelle disciplinaire en chat

**Statut** : appliqué C4 (initial) ✓ | C5 ✓ | C6 ✓ | C7 ✓ | C8 ✓ | **C9 ✓** (§3.2 propagation Energy : 4 triggers définis §2.1, ajustements quotidiens déterministes hors LLM via node `update_energy_metrics_daily` DEP-C9-002, pas de trigger background automatique en V1)

### DEC-C4-002 — Trade-off prescriptif formulé en impact temporel

**Statut** : appliqué C4 (initial) ✓ | C5 ✓ | C6 ✓ | C7 ✓ | C8 ✓ | **C9 ✓** (§3.3 propagation Energy : trade-off formulé en impact temporel — « ta forme actuelle suggère 10-14 jours pour atteindre pic » — pas en jugement moral, exemples ✓/✗ explicites)

### DEC-C4-003 — Toujours prescrire, jamais refuser, traçabilité obligatoire

**Statut** : appliqué C4 (initial) ✓ | C5 ✓ | C6 ✓ | C7 ✓ | C8 ✓ | **C9 ✓** (§3.4 propagation Energy : toujours prescrire au minimum récup active + sleep target + mention modalité contextuelle, traçabilité via `rationale` court dans `notes_for_head_coach`, pas de « repos complet sans alternative »)

---

## Session C9 — Energy Coach (post-C9 ✓)

### DEP-C9-001 — Extension `RecommendationMode.INTERPRETATION` léger (septuplet)

**Cible** : `B3 v2` (validator extension)
**Description** : Étendre l'extension B3 v2 de `RecommendationMode.INTERPRETATION` léger pour inclure Energy Coach C9 — passe du **sextuplet** (DEP-C5-008 / DEP-C4-006 / DEP-C6-005 / DEP-C7-001 / DEP-C8-001) au **septuplet** avec C9. Le mode INTERPRETATION léger pour Energy correspond au trigger `CHAT_DAILY_CHECKIN_INTERPRETATION` (§19 prompt Energy) avec contrat allégé : `evidence_summary` + `flags_for_head_coach` + `notes_for_head_coach`, sans `energy_state_payload` régénéré.
**Statut** : ouverte.

### DEP-C9-002 — Node Coordinator non-LLM `update_energy_metrics_daily` (A2 v2)

**Cible** : `A2 v2` (node Coordinator)
**Description** : Node déterministe non-LLM exécuté quotidiennement (analogue DEP-C8-008 `adjust_nutrition_targets_daily`) qui ajuste les métriques Energy selon :
- Séances réalisées du jour (charges agrégées par discipline depuis payloads coachs disciplines)
- Données passives du jour (sommeil mesuré, HRV, RHR, pas)
- Check-in déclaratif du matin (si présent)
- Application des formules canoniques EMA pour CTL (time constant 42j) et ATL (time constant 7j)
- Recalcul TSB, ACWR global et par discipline, `recovery_score_daily`, `composite_fatigue_index`
- Détection patterns suspects → flag candidate dans `AthleteState` sans réveiller Energy LLM

**Critique** : ce node ne réinvoque **jamais** Energy LLM. La direction stratégique reste fixée par Energy LLM aux 4 triggers §2.1 prompt Energy.
**Statut** : ouverte. **Bloquante** pour fonctionnement Energy V1 (sans node, pas de métriques quotidiennes).

### DEP-C9-003 — Mécanique `activate_energy_protective_frame` Head Coach C1 v2

**Cible** : `head-coach v2`
**Description** : Mécanique de cadre clinique surentraînement activée à réception flag `MEDICAL_ESCALATION_OVERTRAINING_SUSPECTED` (severity `elevated_internal_2` ou `critical_n3`). Analogue strict à `activate_nutrition_clinical_frame` (DEP-C8-005, Option B RED-S). Exécution en deux temps :
1. **Étape 1** — Check-in empathique non-intrusif (« Je remarque plusieurs signes de fatigue accumulée, comment tu te sens côté énergie générale, motivation, santé globale ? »)
2. **Étape 2a** (user confirme malaise) → bascule plan en mode protection (intensités max plafonnées, volume max plafonné, deload imposé minimum 1 semaine), orientation médecine sport pour bilan biologique (cortisol matinal, testostérone, ferritine, vit D, TSH), mention possible kinésithérapeute du sport ou psychologue du sport selon dominante
3. **Étape 2b** (user nie/minimise) → préférence persistée `energy_overtraining_checkin_declined_${date}`, **anti-insistance 4 semaines minimum**, mode protection léger maintenu en background (intensités modérément réduites, deload anticipé d'1 semaine si bloc en cours)

Distinction stricte avec `activate_nutrition_clinical_frame` (RED-S Nutrition C8 §13) et `activate_clinical_frame` Recovery (blessures musculo-squelettiques C3). Trois cadres cliniques distincts, trois zones de responsabilité distinctes.
**Statut** : ouverte. **Bloquante** pour scenarios surentraînement Phase D.

### DEP-C9-004 — Onboarding Coach v2 : collecte `training_baseline_declared` (cold start)

**Cible** : `onboarding-coach v2`
**Description** : Étendre la collecte onboarding initial pour intégrer la déclaration de baseline d'entraînement actuel (cf. §6.3 prompt Energy). Pour chaque discipline pratiquée :
- `volume_h_per_week_3m_avg` (heures/semaine moyenne sur 3 derniers mois)
- `volume_km_per_week_3m_avg` (alternativement km, si plus pertinent par discipline)
- `intensity_rpe_avg` (RPE moyen perçu sur 3 derniers mois)
- `quality_sessions_per_week_avg` (fréquence séances qualité par semaine)

Persistés dans `user.training_baseline_declared` (structure imbriquée par discipline). Permet à Energy d'amorcer CTL initial réaliste pendant les 4-6 premières semaines (cold start), `confidence_level = moderate` jusqu'à accumulation données suffisantes puis `high`.

Réutilisation pattern `UserOnboardingQuery` (DEP-C8-004 inauguré par Nutrition C8) — Onboarding Coach peut collecter upfront, OU Energy peut émettre `UserOnboardingQuery` au premier PLANNING baseline avec dispatch Head Coach.
**Statut** : ouverte.

### DEP-C9-005 — Extension vues filtrées coachs disciplines (consommation `EnergyStatePayload`)

**Cible** : `B2 v2` (vues filtrées) + propagation prompts coachs disciplines v2 (Running C5 v2, Lifting C4 v2, Swimming C6 v2, Biking C7 v2)
**Description** : Étendre les vues filtrées `RunningCoachView`, `LiftingCoachView`, `SwimmingCoachView`, `BikingCoachView` pour inclure le snapshot le plus récent de l'`EnergyStatePayload` (DEP-C9-007, type B3 v2). Permet aux coachs disciplines de consommer les champs critiques :
- `form_status`, `tsb_global`, `acwr_global`
- `recommended_volume_modulation_pct`, `recommended_intensity_modulation_pct` (suggestions consultatif §14.2 prompt Energy)
- `protective_frame_active` (si true, contraintes du cadre clinique imposées par Head Coach)
- `red_s_propagated_risk_level` (recopié pour visibilité coachs disciplines, qui n'ont pas accès direct à `NutritionLoadPayload`)

Comportement attendu coachs disciplines documenté dans §14.4 prompt Energy. Propagation en prompts coachs disciplines v2 nécessaire pour formaliser la consommation côté agent.

**Audit hétérogénéité loads** : vérifier également cohérence structures `*_load_payload` entre les 4 coachs disciplines (Running / Lifting / Swimming / Biking) — champs canoniques attendus par Energy : `weekly_tss_projected` (ou équivalent volume), `acwr_projected`, `cns_load_score`. Champs spécifiques par discipline (`leg_impact_score`, `shoulder_load_score`, `aero_position_hours`, `terrain_distribution`, etc.) restent hétérogènes par design.
**Statut** : ouverte.

### DEP-C9-006 — Nutrition v1.1 : exploitation `EnergyStatePayload` (ferme boucle bidirectionnelle C8-C9)

**Cible** : `nutrition-coach v1.1`
**Description** : Étendre Nutrition pour exploiter activement les signaux `EnergyStatePayload` consommés en mode PLANNING/REVIEW. Champs critiques et utilisations attendues (cf. §15.1 prompt Energy) :
- `form_status` — calibration générale targets nutritionnels
- `tsb_global` — détection moments propices carb loading (TSB > 0 = peak form approchant) ou recalibration en cas TSB très négatif
- `composite_fatigue_index` — modulation kcal récupération si fatigue chronique (axe physique élevé → +kcal récupération, axe CNS élevé → timing glucides spécifique pré-séance qualité)
- `recovery_score_daily_avg_7d` — recalibration récup nutritionnelle
- `protective_frame_active` (bool) — **critique** : bascule Nutrition en mode "maintenance + récupération" (pas de body recomp pendant cadre clinique surentraînement, kcal min maintenance imposé)

Note importante : Energy n'émet **pas** de recommandation kcal directe (séparation responsabilités, décision bloc 8 brainstorming C9). Nutrition v1.1 traduit elle-même les signaux Energy en prescriptions nutritionnelles. Ferme la boucle bidirectionnelle ouverte par note §15.2 prompt Nutrition C8 v1 (« V1 ne reçoit pas de signal Energy en retour direct »).
**Statut** : ouverte.

### DEP-C9-007 — Type `EnergyStatePayload` formalisé en B3 v2

**Cible** : `B3 v2` (type contrat)
**Description** : Formaliser le type `EnergyStatePayload` (cf. §16.5 prompt Energy) dans B3 v2 — payload émis par Energy en modes PLANNING et REVIEW, consommable par les 4 coachs disciplines (DEP-C9-005) et par Nutrition v1.1 (DEP-C9-006). Structure complète documentée §16.5 prompt Energy. Champs critiques :
- État global form (`form_status`, `tsb_global`, `ctl_global`, `atl_global`, `acwr_global`)
- Breakdown par discipline (`acwr_per_discipline`, `tsb_per_discipline`)
- Composite fatigue index 3 axes (physical / cns / psychological — pas de score scalaire agrégé, §12.5 prompt Energy)
- Récupération (`recovery_score_daily`, `recovery_score_daily_avg_7d`, `sleep_target_adherence_7d`)
- Coordination cross-agents (`red_s_propagated_risk_level`, `protective_frame_active`)
- Recommandations modulation indicatives (`recommended_volume_modulation_pct`, `recommended_intensity_modulation_pct`)
- Confidence (`confidence_level`, `data_sources_present` — graceful degradation §3.7 prompt Energy)
- Méta (`recommendation_source_id`)
**Statut** : ouverte.

### DEP-C9-008 — Vue filtrée `EnergyCoachView` formalisée en B2 v2 + node `build_energy_view` (A2 v2)

**Cible** : `B2 v2` (vues filtrées) + `A2 v2` (node Coordinator)
**Description** : Formaliser la vue filtrée `EnergyCoachView` injectée par le Coordinator dans la consultation Energy selon trigger (cf. §2.2 prompt Energy). Contenu exhaustif :
- Loads agrégés des 4 coachs disciplines (`running_load_payload`, `lifting_load_payload`, `swimming_load_payload`, `biking_load_payload`)
- `NutritionLoadPayload` snapshot le plus récent
- Métriques Energy précalculées par `update_energy_metrics_daily` (DEP-C9-002)
- Données passives (sommeil mesuré, HRV, RHR, pas, séances réalisées)
- Déclaratif user (14 derniers check-ins matinaux, format modulable §7.4 prompt Energy)
- Signaux Recovery agrégés (`injury_active_count`, `recovery_phase_active`, `recovery_takeover_active`)
- Profil athlète stable + préférences user pertinentes (`sleep_target_baseline_min`, `stress_management_opt_in`, etc.)
- Historique 4 derniers `Recommendation` Energy

Tag injection variable selon trigger (cf. §21 prompt Energy table d'injection). Node `build_energy_view` à spécifier en A2 v2.
**Statut** : ouverte. **Bloquante** pour invocation Energy V1 (sans vue filtrée, pas d'accès aux données).

### Notes inter-coach C9

**Innovation C9 — Coordination bidirectionnelle Energy ↔ Nutrition** : ferme la boucle ouverte par note §15.2 prompt Nutrition C8 v1 (« V1 ne reçoit pas de signal Energy en retour direct »). Energy consomme `NutritionLoadPayload` (§16.5 prompt Nutrition C8) ET émet `EnergyStatePayload` (§16.5 prompt Energy C9) consommable par Nutrition v1.1 (DEP-C9-006). Bidirectionnalité opérationnelle dès Phase D quand DEP-C9-006 sera implémentée (Nutrition v1.0 actuelle reçoit le payload mais ne l'exploite pas activement — design intentionnel pour respecter règle « ne pas modifier les prompts déjà produits » C9).

**Distinction stricte NFOR/OTS (Energy §13) vs RED-S (Nutrition §13) vs blessures musculo-squelettiques (Recovery)** : trois zones cliniques distinctes, trois cadres cliniques distincts (`activate_energy_protective_frame` C9 / DEP-C9-003, `activate_nutrition_clinical_frame` C8 / DEP-C8-005, `activate_clinical_frame` Recovery C3). Pas de chevauchement de responsabilités. Energy détecte fatigue système globale (CNS + sommeil + signaux objectifs cumulatifs). Nutrition détecte RED-S selon ses propres seuils énergétiques. Recovery gère blessures actives. Coordination via consommation mutuelle de payloads agrégés sans appel direct (isolation stricte head-coach §6.4).

**Approche conservative seuils détection NFOR/OTS** : combinatoire stricte minimum 3 signaux concordants sur 14 jours (§13.2 prompt Energy). Faux positifs = catastrophiques UX (perte confiance app durable), faux négatifs = rattrapables au cycle suivant (fatigue chronique se construit sur des semaines, pas urgence). Décision produit Simon-Olivier C9 brainstorming bloc 5.

**Pas de trigger background automatique en V1** : décision produit C9 brainstorming bloc 1 — cohérence architecturale stricte avec Nutrition C8 (qui n'a pas non plus de trigger background). Le node `update_energy_metrics_daily` peut FLAG dans `AthleteState` sans réveiller Energy LLM. Energy traite les flags candidats au prochain trigger systématique ou conditionnel (latence max ≤ 24h en pratique, vu fréquence quotidienne du `CHAT_DAILY_CHECKIN_INTERPRETATION`).

### Ajout dans "Index par session"

| Session | DEP créées | Statut |
|---|---|---|
| C9 | DEP-C9-001, DEP-C9-002, DEP-C9-003, DEP-C9-004, DEP-C9-005, DEP-C9-006, DEP-C9-007, DEP-C9-008 (8 DEP) | ouvertes |

---

## Ouvertures vers C10

**C10 `classify_intent`** — gating mode TECHNICAL pour **Energy** (en addition à Nutrition C8 §20.1) — `CHAT_TECHNICAL_QUESTION_ENERGY` (§20.1 prompt Energy). Reconnaître questions techniques Energy non-triviales : sommeil avancé (sieste pré-séance, durée optimale taper, hygiène avancée, gestion jet lag), récupération (modalités contextualisées massage/sauna/cold avec nuances scientifiques, deload optimal, taper structure), surentraînement déclaratif (« je suis vidé depuis X mois », « plus aucune motivation depuis longtemps »), charges d'entraînement (ACWR, CTL, TSB en termes user-friendly), HRV interpretation (« mon HRV est bas le matin après une grosse séance »). Questions triviales (« c'est quoi l'HRV ? ») restent Head Coach direct via glossaire. Reconnaître également pattern compatible NFOR/OTS dans déclarations user explicites → routing immédiat vers consultation Energy mode INTERPRETATION ou flagging par Head Coach pour cycle REVIEW suivant.

**C10 `classify_intent`** — gating mode TECHNICAL pour Nutrition (`CHAT_TECHNICAL_QUESTION_NUTRITION`, §20.1 prompt Nutrition). Voir spécifications préalables ci-dessus (préservées de l'ouverture initiale C8).

> **Statut post-C10** : les deux ouvertures ci-dessus sont **✓ traitées** dans `classify-intent.md` v1. Voir §6.2.1 (gating Nutrition TECHNICAL), §6.2.2 (gating Energy TECHNICAL), §5.1 et §10.5 (cadrage strict OTS/NFOR → toujours `SPECIALIST_TECHNICAL` energy, jamais escalation immédiate), §6.3 (escalations cliniques limitées à `tca_declared` + `self_harm_signal`).

---

## Session C10 — classify_intent (post-C10 ✓)

C10 livre `classify-intent.md` v1, prompt système d'un **composant gateway** (pas un agent spécialiste comme C1-C9). Statut spécifique : composant LLM léger (Haiku 4.5 cible V1) invoqué par Head Coach sur chaque message user libre dans le chat. Émet une décision de routage parmi 5 routes : `HEAD_COACH_DIRECT`, `SPECIALIST_TECHNICAL` (avec `specialist_chain` 1-3 spécialistes ordonnée), `CLINICAL_ESCALATION_IMMEDIATE`, `OUT_OF_SCOPE`, `CLARIFICATION_NEEDED`.

Décisions produit clés validées en brainstorming :
- **5 routes** mutuellement exclusives V1
- **6 spécialistes routables** vers TECHNICAL (Nutrition, Energy, Lifting, Running, Swimming, Biking) — implique 4 back-fills `§20 TECHNICAL` (DEP-C10-005 à DEP-C10-008)
- **Détection clinique conservative** : seules les **déclarations explicites univoques** déclenchent escalation immédiate (`tca_declared`, `self_harm_signal`). Cohérent stricte avec `nutrition-coach §4.5 règle 3` (pas de pattern matching diagnostic).
- **OTS/NFOR jamais en escalation immédiate** : toujours route `SPECIALIST_TECHNICAL` energy, peu importe la sévérité déclarée (Energy a le contexte CTL/ATL/TSB pour calibrer)
- **Routing chain V1** : multi-domaines (max 3) émis comme `specialist_chain` ordonnée, Head Coach orchestre les consultations séquentielles + synthèse (DEP-C10-002)
- **Bilingue FR + EN complet V1** avec détection langue auto (`fr` | `en` | `fr-en-mixed`)
- **Confidence score sans seuil dur** côté trieur — Head Coach lit et adapte
- **Flag clinique actif (ex : `flag_clinical_context_active: "tca"`)** : trieur acquitte en metadata mais ne route pas différemment ; adaptation downstream chez spécialiste/Head Coach (DEP-C10-010)

### Dépendances émises par C10

#### DEP-C10-001 — Phase A (A2) : statut architectural classify_intent

`classify_intent` est un **composant LLM léger** invoqué directement par Head Coach (pas un node Coordinator ni un agent spécialiste). À formaliser dans A2 : positionnement architectural, latence cible < 500ms, modèle d'implémentation Haiku 4.5, invocation systématique sur trigger `CHAT_USER_FREE_MESSAGE` (et seulement celui-là — triggers structurés court-circuitent classify_intent).

#### DEP-C10-002 ✓ — Phase C (head-coach C1) : orchestration routing chain multi-spécialistes

**Livré — Session Head Coach back-fills (2026-04-26).** Section `§10.1.2` ajoutée à `head-coach.md`. Chain à 1 élément = consultation unique. Chain ≥ 2 éléments : séquentiel avec contexte partagé (spécialiste N+1 reçoit réponse(s) des précédents), synthèse unifiée voix "je" (§1.3), flags traités après synthèse. Cap ≤ 3 éléments (classify-intent §7.2). Latence : typing indicator uniquement.

#### DEP-C10-003 — Phase B (B3 v2) : contrats `IntentClassificationRequest` et `IntentClassification`

Formaliser dans B3 v2 :
- **`IntentClassificationRequest`** (input) — `user_message`, `conversation_context_minimal` (last_head_coach_turn_summary, current_conversation_mode, journey_phase, last_3_intents), `user_profile_minimal` (primary_goal, disciplines_practiced, preferred_language, flag_clinical_context_active). Cf. `classify-intent §8`.
- **`IntentClassification`** (output) — decision (5 enums), specialist_chain (Optional list[enum] 1-3), clinical_escalation_type (Optional enum tca_declared | self_harm_signal), clarification_axes (Optional list[str] 2-4), confidence (float 0-1), reasoning (str max 200 char), language_detected (fr | en | fr-en-mixed), clinical_context_active_acknowledged (bool). Cf. `classify-intent §9`.

#### DEP-C10-004 ✓ — Phase C (head-coach C1) : génération options tappables depuis clarification_axes

**Livré — Session Head Coach back-fills (2026-04-26).** Section `§10.1.3` ajoutée à `head-coach.md`. Intro 1 phrase référant au message ambigu user. N options tappables ordre conservé. Champ libre "Autre — préciser" toujours présent en dernière option. Re-soumission à classify_intent sur réponse user (`"réponse à clarification : <axe sélectionné>"`). `<contract_payload>null`.

#### DEP-C10-005 ✓ — Phase C (lifting-coach C4) : §20 TECHNICAL Lifting

**Livré — Session C-tardive (2026-04-26).** Section `§20.7 Couverture des sujets V1 et personnalisation` ajoutée à `lifting-coach.md`. Couverture V1 complète : technique d'exécution (squat/bench/deadlift/OHP/accessoires), périodisation force (accumulation→intensification→peaking, durées hybrides), RPE/RIR avancé (leader set + back-off, ajustement fatigue), progression spécifique (microcharges, variantes correctives, seuil plateau >4 sem → test 1RM), choix variantes (back/front squat, sumo/conventional, incline bench). Personnalisation A1 selon `lifting_load_payload`. Redirection B1 Head Coach pour questions cross-discipline. DEC-C3-001 stricte propagée.

#### DEP-C10-006 ✓ — Phase C (running-coach C5) : §20 TECHNICAL Running

**Livré — Session C-tardive (2026-04-26).** Section `§21.6 Couverture des sujets V1, personnalisation et règles spécifiques` ajoutée à `running-coach.md`. Couverture V1 complète : technique de course (cadence 170-180 spm, overstride, midfoot vs heel-strike, posture), allures spécifiques calibrées sur VDOT/VMA (seuil vs tempo, intervalles VMA, répétitions), équipement chaussures par catégories techniques (drop/stack/foam/carbon plate — sans marques), préparation événement (pacing négatif marathon, dénivelé trail, fueling). Personnalisation A1 selon VDOT courante. Redirection B1. Code-switching FR-EN.

#### DEP-C10-007 ✓ — Phase C (swimming-coach C6) : §20 TECHNICAL Swimming

**Livré — Session C-tardive (2026-04-26).** Sections `§21.5 Couverture des sujets V1`, `§21.6 Personnalisation (A1) et règles spécifiques`, `§21.7 Exemple TECHNICAL` ajoutées à `swimming-coach.md`. Couverture V1 complète : technique crawl (catch EVF, traction, rotation hanches 60-75°, glissée), dos/brasse/papillon (timings spécifiques), drills correctifs (catch-up/single-arm/fingertip drag/kick on side, progression défaut→drill), planning séances piscine (structure échauffement/série/dénage, ratios TID par phase, 2km vs 4km), open water vs bassin (sighting, navigation, départ groupé). Personnalisation A1 selon CSS courante. Douleur épaule → flag Recovery + B1. Cohérence §3.3 RPE prime HR. DEC-C3-001 stricte.

#### DEP-C10-008 ✓ — Phase C (biking-coach C7) : §20 TECHNICAL Biking

**Livré — Session C-tardive (2026-04-26).** Section `§21.6 Couverture des sujets V1, personnalisation et règles spécifiques` ajoutée à `biking-coach.md`. Couverture V1 complète : position fit (selle hauteur/recul/inclinaison, cintre, cleat, diagnostic douleur genou interne/externe), tests FTP comparés (20 min × 95 %, ramp × 75 %, Kolie Moore direct — choix selon profil), cadence et pédalage (optimal plat/montée, pédalage circulaire, force basse cadence déconseillée général), équipement technique (plateaux compact/standard/CX par catégories, capteurs puissance mono/dual/moyeu — sans marques). Personnalisation A1 selon FTP actuelle + `aero_position_hours`. Douleur persistante → suggestion bike fit professionnel via B1. Interdiction comparaisons modèles commerciaux.

#### DEP-C10-009 — Phase D (eval / fine-tuning) : catalogue exemples étendu hors prompt

Le prompt système V1 contient ~62 exemples calibrés core (`classify-intent §11`). Catalogue étendu cible ~235 exemples maintenu **hors prompt** comme dataset d'eval V1 et corpus de fine-tuning éventuel V2. Phase D : produire le dataset complet (15 FR + 10 EN par catégorie pour `HEAD_COACH_DIRECT`, par spécialiste TECHNICAL × 6, par escalation × 2, pour `OUT_OF_SCOPE` et `CLARIFICATION_NEEDED`). Format : JSONL avec `user_message`, `expected_decision`, `expected_specialist_chain` / `expected_clinical_escalation_type` / `expected_clarification_axes`, `expected_language`, notes. Sert à : (a) eval automatisée précision V1 production, (b) fine-tuning Haiku éventuel V2 si précision few-shot insuffisante.

#### DEP-C10-010 ✓ — Phase C (head-coach C1) + tous spécialistes : lecture metadata `clinical_context_active_acknowledged`

**Livré (Head Coach) — Session Head Coach back-fills (2026-04-26).** Section `§10.1.4` ajoutée à `head-coach.md`. 3 flags couverts : `tca` (vocab restrictif nutrition interdit, formulations positives), `red_s` (même prudence nutrition + pas de mention déficit), `ots`/`nfor` (pas de vocab "passe au travers" / "corps va s'adapter"). Injection du flag dans payload spécialiste. Adaptation toujours invisible user. S'applique en superposition de toutes les routes. Spécialistes (nutrition-coach §4.5 règle 2, energy protective frame DEP-C9-003) : back-fill séparé si nécessaire en Phase D.

### Propagation des décisions cross-agents (statut après C10)

#### DEC-C3-001 — Primauté du déclaratif utilisateur sur signaux objectifs

**Application classify_intent** : §3.5 (« primauté du déclaratif explicite ») applique strictement le principe. Si l'user déclare explicitement un état (TCA, OTS lourd, idéation suicidaire), classify_intent prend la déclaration au sérieux et route immédiatement vers la destination appropriée, **sans demander confirmation intermédiaire**. Le doute ne s'applique qu'aux signaux subtils non-déclaratifs, qui par construction (§3.4, §4.4) ne déclenchent rien de clinique. Cohérence stricte avec `nutrition-coach §4.5 règle 3` (pas de pattern matching diagnostic) — classify_intent **n'infère jamais** sur signaux subtils.

#### DEC-C4-001 — Pattern de consultation conditionnelle disciplinaire en chat

**Application classify_intent** : appliquée **par construction**. classify_intent **est** le composant qui gate les consultations conditionnelles TECHNICAL des 6 spécialistes. La décision route `SPECIALIST_TECHNICAL` + émission `specialist_chain` matérialise la consultation conditionnelle. Routage chain multi-spécialistes (V1, max 3 éléments) est l'extension naturelle du pattern aux questions multi-domaines. Triggers déclenchés en aval : `CHAT_TECHNICAL_QUESTION_<specialist>` pour chaque spécialiste de la chain.

#### DEC-C4-002 — Trade-off impact temporel court terme vs long terme

**Application classify_intent** : non applicable directement. classify_intent ne formule pas de prescriptions, ne tranche aucun trade-off temporel. Route uniquement.

#### DEC-C4-003 — Toujours prescrire, jamais refuser, traçabilité

**Application classify_intent** : non applicable directement. classify_intent route, ne prescrit pas. La traçabilité est assurée via le `reasoning` court (max 200 char) émis dans chaque décision, audit interne des routages effectués.

### Delta index — session C10

| Décision transversale | Origine | Sessions adoptantes | Statut |
|---|---|---|---|
| DEC-C3-001 | C3 Recovery | C4 (✓), C5 (✓), C6 (✓), C7 (✓), C8 (✓), C9 (✓), **C10 (✓)** | **Largement propagée — fin Phase C** |
| DEC-C4-001 | C4 Lifting | C5 (✓), C6 (✓), C7 (✓), C8 (✓), C9 (✓), **C10 (✓ — composant de gating)** | **Largement propagée — fin Phase C** |
| DEC-C4-002 | C4 Lifting | C5 (✓), C6 (✓), C7 (✓), C8 (n/a), C9 (n/a), C10 (n/a) | Propagée disciplines, n/a non-disciplinaires |
| DEC-C4-003 | C4 Lifting | C5 (✓), C6 (✓), C7 (✓), C8 (✓), C9 (n/a), C10 (n/a) | Largement propagée |

### Bilan Phase C

Phase C close avec C10. 10 livrables produits (C1-C10). Architecture conversationnelle complète :
- **Orchestrateur** : Head Coach (C1)
- **Onboarding** : Onboarding Coach (C2)
- **5 spécialistes domaine** : Recovery (C3), Lifting (C4), Running (C5), Swimming (C6), Biking (C7)
- **2 spécialistes transversaux** : Nutrition (C8), Energy (C9)
- **Composant gateway** : classify_intent (C10)

Total dépendances ouvertes Phase C → autres phases : à consolider en Phase D init. ~~Notamment 4 back-fills `§20 TECHNICAL` (Lifting, Running, Swimming, Biking — DEP-C10-005 à DEP-C10-008) à exécuter avant implémentation Phase D pour viabilité du routage classify_intent V1 complet.~~ **Clôturé Session C-tardive (2026-04-26) — DEP-C10-005 à DEP-C10-008 tous livrés.** ~~DEP-C10-002, DEP-C10-004, DEP-C10-010 (back-fills Head Coach orchestration) à livrer.~~ **Clôturé Session Head Coach back-fills (2026-04-26) — DEP-C10-002, 004, 010 tous livrés.** Phase C complète. Toutes les dépendances Head Coach classify_intent satisfaites. Pré-requis Phase D complets.

---

### Session Head Coach back-fills (post-C10 ✓) — 2026-04-26

**Objectif** : Back-fill des 3 comportements Head Coach requis par classify_intent (DEP-C10-002, DEP-C10-004, DEP-C10-010) — cohérence architecturale Phase C avant Phase D.

**Décisions produit validées** :
- **Décision 1** : Chain multi-spécialistes — fusion invisible (opacité §1.3), pas d'annonce de la chain à l'user.
- **Décision 2** : Contexte partagé entre spécialistes — spécialiste N+1 reçoit réponse(s) des précédents pour cohérence inter-domaines.
- **Décision 3** : Latence chain — typing indicator uniquement, aucun message texte intermédiaire.
- **Décision 4** : Intro clarification — référer au message ambigu user (naturel conversationnel).
- **Décision 5** : Champ libre "Autre — préciser" toujours présent, quelle que soit la liste d'axes.
- **Décision 6** : Adaptation wrapping clinique — invisible user, 3 flags couverts (`tca`, `red_s`, `ots`/`nfor`).

**Livrables** :
- `head-coach.md` : §10.1 restructuré (étape 0 routing, tags injectés mis à jour) + §10.1.2 (DEP-C10-002) + §10.1.3 (DEP-C10-004) + §10.1.4 (DEP-C10-010) + §10.1.5 (escalation + out_of_scope) ajoutés
- `DEPENDENCIES.md` : DEP-C10-002, 004, 010 marqués ✓, bilan Phase C mis à jour

---

### Session C-tardive (post-C10 ✓) — 2026-04-26

**Objectif** : Back-fill des 4 sections `§TECHNICAL` manquantes dans les prompts disciplines (DEP-C10-005 à DEP-C10-008), prérequis Phase D.

**Décisions produit validées** :
- **Décision A → A1** : personnalisation contextuelle forte — chaque discipline calibre sa réponse sur le payload actuel user (VDOT, FTP, CSS, `lifting_load_payload`). Pas de réponse encyclopédique générique.
- **Décision B → B1** : questions hors-périmètre disciplinaire redirigées vers Head Coach via `notes_for_head_coach`. La discipline fournit ses contraintes, l'arbitrage cross-discipline appartient au Head Coach.

**Livrables** :
- `lifting-coach.md` : §20.7 ajouté (couverture V1 Lifting, personnalisation A1, B1, DEC-C3-001)
- `running-coach.md` : §21.6 ajouté (couverture V1 Running, allures VDOT, équipement sans marques, B1, code-switching FR-EN)
- `swimming-coach.md` : §21.5 + §21.6 + §21.7 ajoutés (couverture V1 Swimming, drills, open water, CSS personnalisation, épaule → Recovery, §3.3 RPE prime HR)
- `biking-coach.md` : §21.6 ajouté (couverture V1 Biking, position fit, protocoles FTP comparés, bike fit pro via B1, sans marques)
- `DEPENDENCIES.md` : DEP-C10-005 à 008 marqués ✓, phase C close
