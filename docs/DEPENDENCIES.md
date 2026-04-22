# Dépendances ouvertes — Phase C rédaction prompts

> Journal des dépendances architecturales, incohérences inter-documents et points reportés à Phase D ou aux versions ultérieures des documents A/B. Mis à jour au fil des sessions C (C1, C2, C3, …).
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

## Résolution en B2 v2

*(vide pour l'instant — DEP-C3-002 peut alternativement être résolu ici)*

---

## Résolution en B3 v2

*(vide pour l'instant)*

---

## Résolution en Phase D (implémentation backend)

### DEP-C3-004 — Nature LLM vs déterministe des nodes `evaluate_severity` du graphe `recovery_takeover`

**Source** : session C3, Partie III structuration.

**Contexte** : A2 décrit `evaluate_severity` comme *"Classe la gravité : léger / modéré / grave"*. Le node n'est pas dans les interrupts HITL, et il suit `collect_diagnostic` (interrupt) puis précède `propose_protocol`. Par cohérence avec les patterns Onboarding (`evaluate_block_completion` = node déterministe lisant un signal structuré du LLM précédent), hypothèse de travail : `evaluate_severity` est déterministe et lit la structured output de `RECOVERY_ASSESS_SITUATION`. B2 n'a effectivement pas de trigger `RECOVERY_EVALUATE_SEVERITY`, ce qui confirme l'hypothèse.

**Résolution proposée** : Phase D confirme que `evaluate_severity` est un node déterministe qui lit un champ structuré (ex : `severity_assessment: Literal["mild", "moderate", "severe"]`) produit par le node LLM précédent via son `<node_control>` ou équivalent.

**Impact rédaction C3** : §14 node `RECOVERY_ASSESS_SITUATION` requiert dans sa structure de sortie (bloc `<node_control>`) un champ `severity_assessment` qui sera consommé par `evaluate_severity` en aval.

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
- **C9 Energy Coach V3** : même tension `user_energy_signal` vs `objective_energy_availability`. Appliquer le même principe de primauté déclarative avec protections analogues (seuils EA critiques, détection override, monitor_signals explicite).
- **C4-C6 Coachs disciplines** : même tension potentielle entre RPE objectif mesuré et RPE déclaré par user post-session. Le RPE déclaré prime en cas de dissonance (avec protection sur patterns persistants).
- **C7 Nutrition Coach** : tension `user_reported` vs tracked intake. Principe adaptable : le déclaratif utilisateur sur satiété/qualité prime, mais les seuils caloriques critiques (EA en zone clinical_red_s par exemple) imposent des protections.

---

## Index par session

| Session | DEP IDs | Résolus ? |
|---|---|---|
| C1 | — | — |
| C2 | (dépendance `InjuryHistory` mutations → résolue via RCV16 + §9 B1 + `declared_by` = "recovery_coach" pour mutations en takeover) | ✓ résolue en B1/B2 |
| C3 | DEP-C3-001, DEP-C3-002, DEP-C3-003, DEP-C3-004 | ouvertes |
