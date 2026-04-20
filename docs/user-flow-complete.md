# Flow utilisateur complet — Resilio+

> **Version 4 (finale A2).** Intègre les trois enrichissements d'architecture validés en session A2 : taxonomie des modes d'intervention des spécialistes (consultation / délégation / takeover), état macro `journey_phase` comme source de vérité du parcours, et distinction formelle entre événements initiés utilisateur et événements détectés système. Document stable, référence pour A3 (roster des agents consolidé), Phase B (spécification des schémas), Phase C (par agent) et Phase D (implémentation backend).

## Objet

Document de référence décrivant le parcours utilisateur complet, de la création de compte à la vie steady-state, incluant les modes d'échec, les transitions conditionnelles et les règles systémiques associées.

Ne décrit pas l'implémentation technique ni les interfaces visuelles. Ne contient plus de points ouverts de conception.

---

## Principes directeurs

**Consentement éclairé guidé.** L'agent propose une recommandation justifiée, ouvre la validation, accueille le désaccord sans friction. Jamais de demande de préférence non informée.

**Gating par qualité de données.** Aucune prescription personnalisée sans signal suffisant. Le mode assessment est une porte de qualité, pas un détour administratif.

**Réversibilité.** Tout choix utilisateur structurant (coaching scope, objectifs, plan, bloc onboarding) est révisable.

**Opacité de l'architecture multi-agents.** L'utilisateur interagit avec un coach unifié. L'architecture multi-agents est invisible par défaut. Seules exceptions : transitions cliniques explicites (Recovery Coach sur blessure), à concevoir en session UX dédiée.

**Prescription plutôt que suggestion.** Chaque interaction produit une décision claire ou explicite son absence motivée.

---

## État macro du parcours (`journey_phase`)

Le parcours utilisateur est piloté par un champ d'état macro `journey_phase` porté par l'`AthleteState`. Ce champ est la source de vérité pour déterminer dans quelle section du flow l'utilisateur se trouve et conditionne le routage de l'orchestrateur à chaque interaction.

### Sept états principaux (mutuellement exclusifs)

| État | Correspond à | Durée typique |
|---|---|---|
| `signup` | Phase 0 | Minutes |
| `scope_selection` | Phase 1 | Minutes |
| `onboarding` | Phase 2 | 15–20 min (split possible) |
| `baseline_pending_confirmation` | Phase 3 | Minutes à 30 j max |
| `baseline_active` | Phase 4 | 7–21 jours |
| `followup_transition` | Phase 5 | Une conversation |
| `steady_state` | Phase 6 post-confirmation + Phase 7 | Ouvert |

### Deux états overlay (peuvent coexister avec un état principal)

| État overlay | Déclenché par | Effet |
|---|---|---|
| `recovery_takeover_active` | Rapport de blessure ou pause clinique | Recovery Coach prend la main, cadre UX change, plan suspendu |
| `onboarding_reentry_active` | Changement d'objectif ou de contraintes | Re-entrée partielle dans Phase 2 sur les blocs concernés, état principal maintenu en arrière-plan |

### Règles de mutation

- Un seul état principal à la fois. Les transitions sont explicites (validées par sortie de phase).
- Les overlays se superposent. À leur résolution, l'état principal reprend son activité.
- Chaque graphe LangGraph qui se termine est responsable de muter `journey_phase` vers l'état suivant avant son `END`. Le service d'orchestration lit l'état post-graphe pour décider du routage suivant.

---

## Phase 0 — Création de compte

### État de données
`AthleteProfile` créé avec 4 champs : `date_of_birth`, `biological_sex`, `height`, `weight`. `coaching_scope` non défini. `assessment_mode` non défini. `journey_phase = signup`.

### Règles
- Saisie au choix en unités métriques ou impériales. Pré-sélection basée sur la locale. **Stockage interne toujours métrique.**
- Date de naissance stockée, âge dérivé.
- `biological_sex` sans cas particulier pour parcours hormonal atypique (non-priorité V1).

### Entrée / sortie
Entrée : signup complété. Sortie : 4 champs valides → mutation `journey_phase = scope_selection` → Phase 1.

### Modes d'échec
- Abandon : acceptable.
- Données incohérentes : validation client + serveur, retour à la saisie.

---

## Phase 1 — Activation du coaching

### État de données
`coaching_scope` défini comme un dict par domaine fonctionnel. `journey_phase = scope_selection`.

### Structure
```
coaching_scope: {
  lifting:   "full" | "tracking" | "disabled",
  running:   "full" | "tracking" | "disabled",
  swimming:  "full" | "tracking" | "disabled",
  biking:    "full" | "tracking" | "disabled",
  nutrition: "full" | "tracking" | "disabled",
  recovery:  "full" | "tracking" | "disabled",
}
```

### Règles
- Présentation des modes au **premier lancement du chat coach** (pas au signup).
- Mention explicite : le choix est réversible à tout moment.
- Trois raccourcis exposés :
  1. **`full`** : tous les domaines en `"full"`.
  2. **`tracking_only`** : tous les domaines en `"tracking"`.
  3. **`custom`** : choix par domaine.
- `tracking_only` reste visible pour capter les utilisateurs ayant déjà un coach privé.

### Sémantique du mode `tracking` par domaine

| Domaine | Comportement en tracking |
|---|---|
| Disciplines sport (lifting, running, swimming, biking) | Agrégation des données connecteur + saisie manuelle. Pas de prescription. |
| Nutrition | Calories ingérées saisies par l'user. TDEE estimé automatiquement si l'user ne sait pas. Permet de mesurer le delta avant/après un éventuel passage en `full`. Pas de recommandations. |
| Recovery | Agrégation HRV + sommeil via connecteurs. Affichage brut. Pas d'interprétation ni de recommandation. |

### Entrée / sortie
Entrée : premier lancement chat coach. Sortie :
- Si ≥ 1 domaine en `"full"` → mutation `journey_phase = onboarding` → Phase 2 (onboarding limité aux blocs pertinents).
- Si aucun domaine en `"full"` → flow tracking pur, hors périmètre de ce document.

### Modes d'échec
- Indécision : pas de choix par défaut, ré-interrogation à la session suivante.
- Changement post-choix : autorisé. `tracking → full` sur un domaine déclenche une Phase 2 partielle (blocs onboarding du domaine concerné + blocs transversaux si pas déjà complétés).

---

## Phase 2 — Onboarding

### État de données
`ExperienceProfile`, `ObjectiveProfile`, `InjuryHistory`, `PracticalConstraints` enrichis. Classement 4 niveaux × 3 dimensions produit, accompagné d'un **niveau de confiance** par dimension. `journey_phase = onboarding`.

### Règles
- Durée cible **15–20 minutes maximum**.
- Option **« je ne sais pas »** disponible sur toutes les questions factuelles, **sauf** les blocs **Objectifs** et **Blessures** (tous deux obligatoires).
  - Bloc Blessures : la réponse « aucune blessure » est valide et prévue.
- Pilotage par l'**Onboarding Coach** en mode **délégation** : l'agent détient le tour conversationnel pendant toute la phase, tout en restant invisible à l'utilisateur (identité façade maintenue). Questions factuelles indirectes, jamais d'auto-évaluation subjective.
- Classement 4×3 **non exposé** à l'utilisateur. Exposition sous forme de **graphique radar** des compétences par discipline.
- Radar mis à jour **après la baseline** puis **à chaque fin de bloc mesocycle**.
- Connecteurs (Hevy, Strava, Apple Health) **proposés dès le début de Phase 2**, optionnels mais fortement recommandés.

### Scope des blocs selon `coaching_scope`

**Blocs transversaux (toujours présents si ≥ 1 domaine en `full`)**
- Objectifs.
- Historique de blessures.
- Contraintes pratiques.

**Blocs conditionnels (présents uniquement pour les domaines en `full`)**
- Historique d'entraînement par discipline.
- Compétence technique par discipline.
- Capacité de charge par discipline.

### Contenu des blocs

1. **Historique d'entraînement.** Années de pratique structurée, fréquence typique sur 12 mois, dernière interruption > 4 semaines.
2. **Compétence technique.** PR référencés, distances couvertes, mouvements maîtrisés, charges relatives au poids de corps.
3. **Capacité de charge.** Volume hebdo des 8 dernières semaines, session la plus longue, session la plus intense.
4. **Objectifs.** Un objectif principal, objectifs secondaires acceptés si non-contradictoires avec le principal. Horizon + date cible si applicable.
5. **Historique de blessures.** Actives, chroniques, passées significatives < 24 mois.
6. **Contraintes pratiques.** Jours disponibles, budget temps par session, équipement, lieu, sommeil, travail.

### Mécanique « je ne sais pas »
- La dimension correspondante hérite d'un score `unknown` + niveau de confiance réduit.
- Le plan baseline prend des hypothèses conservatrices sur cette dimension (intensité plus basse, progression plus prudente).
- La re-calibration Phase 6 a plus de poids sur cette dimension.
- Seuil de rupture : si > 50 % des questions d'un bloc sont skippées, le bloc est marqué « insuffisant » → baseline étendue pour compenser.

### Checkpoint par bloc
- L'état d'avancement est persisté **à la fin de chaque bloc complété**, pas à chaque question.
- Reprise après abandon : l'utilisateur recommence le bloc en cours à sa première question. Les blocs déjà validés sont conservés tels quels.
- Conséquence : un abandon en milieu de bloc fait perdre la progression du bloc courant uniquement.

### Graphique radar
Présentation **descriptive, pas évaluative**. Axes : dimensions × disciplines pratiquées. Pas de formulations type « à améliorer » ou « point fort ». Cohérent avec la charte clinique / zero-encouragement.

### Entrée / sortie
Entrée : `coaching_scope` avec ≥ 1 domaine en `"full"`. Sortie : blocs pertinents traités (remplis ou skippés) + synthèse validée → mutation `journey_phase = baseline_pending_confirmation` → Phase 3.

### Modes d'échec
- **Abandon partiel.** État sauvegardé bloc par bloc, reprise au bloc en cours. Délai > 14 j → revalidation des blocs remplis.
- **Refus d'un bloc gaté (objectifs / blessures).** Non-skippable. Expliciter le contrat.
- **Contradictions internes.** Surface, pas de résolution silencieuse.
- **Objectifs incompatibles.** Push back Onboarding Coach, demande de priorisation.

---

## Phase 3 — Plan baseline : génération et confirmation

### État de données
`assessment_mode = true`. `baseline_plan` généré à partir du **déclaratif onboarding uniquement**. `journey_phase = baseline_pending_confirmation`.

### Règles

**Durée de la baseline**

| Profil | Durée |
|---|---|
| Hommes | 7 jours |
| Femmes avec cycle actif | 14 jours |
| Femmes sans cycle actif (aménorrhée, ménopause, contraception stable) | 7 jours |

**Extension multi-disciplines**
- Base : 7 jours.
- + 2 jours par discipline active au-delà de 2 disciplines.
- Plafond : **21 jours**.

Exemples : 1–2 disciplines → durée de base. 3 disciplines → base + 2j. 4 disciplines → base + 4j. 5 disciplines → base + 6j (ou plafond selon le cas).

Combiné avec le modificateur femmes avec cycle : la plus longue des deux durées s'applique.

### Interaction
Head Coach présente (en **consultation** silencieuse des coachs disciplines pour la génération) :
- Nature diagnostique de la baseline (pas performant).
- Structure du plan : modalités exposées, intensité sous-max.
- Conditions de sortie (voir Phase 5).
- Ajustements logistiques acceptés (jours, ordre). Ajustements de contenu refusés avec explication.

### Entrée / sortie
Entrée : onboarding validé. Sortie : confirmation baseline → mutation `journey_phase = baseline_active` → Phase 4.

### Modes d'échec
- **Refus de la baseline.** Gate dur par défaut. Exception : utilisateurs classés `intermédiaire` ou `avancé` avec historique connecteur riche → baseline raccourcie ou remplacée par observation passive.
- **Modifications massives demandées.** Refusées avec explication.
- **Délai avant exécution > 30 jours.** Re-validation de la baseline (les données peuvent avoir changé).

### Définition « historique connecteur riche »
Strava, Hevy ou Apple Health avec **≥ 3 mois d'activité régulière** (peu importe la source). Ce seuil définit aussi opérationnellement le niveau `intermédiaire` minimum en Phase 2.

---

## Phase 4 — Exécution de la baseline

### État de données
`assessment_mode = true`. Logs session, HRV, sommeil, RPE, sensations, données de charge. `baseline_metrics` accumule. `journey_phase = baseline_active`.

### Règles
- **Tolérance aux écarts d'exécution.** Le système accepte que le user sur-estime ou sous-estime. Tant que les séances sont complétées, le système combine données session + données connecteurs pour ajuster.
- **Connecteurs en priorité.** La baseline couvre **seulement les signaux manquants** non déjà fournis par les connecteurs.
- **Quantité minimale de données indexée sur l'objectif principal.** Modalités directement liées à l'objectif principal → signal complet requis. Modalités secondaires → signal minimal acceptable.

### Principe opérationnel « quantité minimale dépend de l'objectif »

Exemples (à formaliser discipline par discipline en Phase C) :
- Objectif marathon → course doit être exposée à volume + intensité. Lifting accepté en signal minimal.
- Objectif force max → lifting doit exposer les patterns principaux à intensité ≥ 80 %. Cardio accepté en signal minimal.
- Objectif hybride (recomposition + endurance) → signal complet sur les deux modalités.

### Interventions des agents en baseline

Mode observation par défaut. Exceptions :
- **Sécurité** : blessure rapportée ou douleur persistante → Recovery Coach prend la main en **takeover** explicite, overlay `recovery_takeover_active = true`.
- **Anomalie critique** : HRV en chute libre, RPE systématique ≥ 9 sur sessions sous-max → Head Coach surface (déclenchement via monitoring système, pas via message utilisateur).

### Modes d'échec / interruption
- **Sessions manquées.** Seuil : ≥ 70 % des séances complétées **ET** ≥ 1 séance représentative par modalité au plan.
- **Pause courte (1–5 j).** Extension de la baseline de la durée de la pause.
- **Pause longue (> 7 j).** Re-déclenchement baseline.
- **Blessure.** Recovery Coach prend la main, baseline suspendue, reprise conditionnée.
- **Données incohérentes.** Surface par Head Coach, conversation pour identifier la cause.
- **Ghosting.** Relance à 7 j, message Head Coach à 14 j, mode inactif au-delà de 21 j.

### Définitions opérationnelles (par défaut, à affiner par discipline en Phase C)
- **Séance représentative** : ≥ 70 % du volume prescrit **ET** ≥ 80 % de l'intensité prescrite.
- **Tolérance aux écarts** : écart < 30 % silencieux, ≥ 30 % surface sans moralisation.

---

## Phase 5 — Transition baseline → plan personnalisé

### État de données
Transition `assessment_mode: true → false`. Premier plan personnalisé généré. Transition `journey_phase = baseline_active → followup_transition → steady_state`.

### Règles
- **Conversation de suivi obligatoire avant Phase 6.** Head Coach demande « comment c'est passé la baseline ». Cette conversation est une **ré-entrée déguisée dans l'onboarding** : les réponses corrigent les éventuelles mauvaises interprétations du déclaratif initial.
- **Raccourci baseline selon classement** :
  - **Intermédiaire / avancé** + historique connecteur riche (≥ 3 mois activité régulière) → baseline raccourcie ou remplacée par observation passive.
  - **Novice / débutant avancé** → pas de raccourci, baseline complète même si connecteurs présents (le déclaratif est moins fiable).

### Conditions conjointes de sortie de baseline

1. Durée minimale écoulée selon profil (Phase 3).
2. Compliance ≥ 70 % des séances prévues.
3. Couverture des modalités cibles (fonction de l'objectif, voir Phase 4).
4. Données physiologiques minimales (HRV baseline établie si connecteur présent, sommeil loggé, RPE loggé sur ≥ 70 % des séances).
5. Absence d'événement perturbateur ouvert (blessure non résolue, pause en cours).
6. Conversation de suivi complétée.

### Conversation de suivi — mécanique

Head Coach en façade, Onboarding Coach **consulté en backend** (mode consultation silencieuse, non délégation). L'Onboarding Coach produit un set de questions ciblées à partir des écarts observés entre le déclaratif initial et les observations de baseline ; Head Coach les formule et les pose lui-même. Zones ciblées :
- Écart entre difficulté ressentie et difficulté prévue → recalibrer capacité de charge.
- Écart entre RPE déclaré en séance et sensations globales → recalibrer compétence technique.
- Émergence de contraintes non déclarées → mettre à jour `PracticalConstraints`.
- Réaffirmation ou révision de l'objectif principal.

Pas de question directe du type « es-tu sûr de ton niveau ». Questions factuelles indirectes, cohérent avec la posture Onboarding Coach.

### Entrée / sortie
Entrée : baseline exécutée. Sortie : conditions + conversation validées → mutation `journey_phase = steady_state` puis génération du premier plan personnalisé (Phase 6, en continuité).

### Modes d'échec
- Conditions non atteintes à la durée nominale → extension justifiée.
- **Sous-compliance persistante > 45 jours en `assessment_mode`** → révision obligatoire : soit re-onboarding partiel (objectifs ou contraintes irréalistes), soit rebasculement en `tracking`.
- Contradictions entre déclaratif et observations → résolution via conversation de suivi, re-entrée Onboarding Coach si nécessaire.

---

## Phase 6 — Plan personnalisé

### État de données
`assessment_mode = false`. `active_plan` créé. `journey_phase = steady_state`.

### Règles
- **Horizon du plan** : formats **4 semaines, 12 semaines, ou « jusqu'à l'objectif » (date précise)**.
- **Structure en blocs** : tous les blocs jusqu'à l'objectif sont **énumérés et titrés** à la présentation. Seul le bloc courant est **détaillé**. Les suivants apparaissent en **titre + thème**. La fin d'un bloc déclenche le détail du suivant.
- **Un seul `active_plan`** orchestrant toutes les disciplines actives. Composantes par discipline, cohérence arbitrée par Head Coach.
- **Transparence explicite sur les trade-offs.** Tout sacrifice d'un objectif secondaire pour protéger le principal est explicité à la présentation du plan.

### Structure de données
```
active_plan: {
  objective: ObjectiveProfile,
  horizon: "4w" | "12w" | "until_date",
  end_date: date | null,
  blocks: [
    { id, title, theme, start_date, end_date,
      status: "current" | "upcoming" | "completed",
      detail_level: "full" | "summary" },
    ...
  ],
  discipline_components: {
    running: PlanComponent,
    lifting: PlanComponent,
    swimming: PlanComponent,
    biking: PlanComponent,
  },
  trade_offs_disclosed: [TradeOff, ...],
}
```

### Interaction
Head Coach présente macrocycle complet + bloc 1 détaillé. Niveaux d'ajustement utilisateur :
1. **Logistique** (jours, ordre des séances) : accepté si ne casse pas la logique de récupération.
2. **Volume / intensité** : refusé sans justification médicale ou contrainte.
3. **Objectif / direction** : déclenche une re-conversation avec l'Onboarding Coach (changement d'objectif = re-classement partiel possible).

### Entrée / sortie
Entrée : sortie validée de Phase 5. Sortie : confirmation du plan → Phase 7.

### Modes d'échec
- **Refus complet du plan.** Dialogue structuré, retour sur le bloc onboarding concerné (objectif mal capté, contraintes ignorées, sous/sur-calibration).
- **Confirmation sans intention d'exécution.** Détectée post-hoc en Phase 7 via non-exécution.

---

## Phase 7 — Vie steady-state

### État de données
`active_plan` en cours. Logs continus. `AthleteState` mis à jour à chaque événement. `journey_phase = steady_state`. Overlays `recovery_takeover_active` ou `onboarding_reentry_active` possibles.

### Rythme structurel

**Check-ins quotidiens**
- **Matin** : sommeil, stress, énergie.
- **Nutrition** : calories consommées.
- **Séance** : exécutée via connecteur OU saisie manuelle. Les deux voies marquent la/les session(s) prévue(s) du jour comme complétées.

**Rapport hebdomadaire**
- Synthèse de la semaine.
- Ajustements marginaux pour la suivante.
- Conditions posées pour la semaine à venir.

**Fin de bloc mesocycle**
- Régénération du bloc suivant à partir de la progression observée.
- Le nouveau bloc passe en `detail_level: "full"`, les suivants restent en `"summary"`.
- Radar onboarding mis à jour.

**Par objectif**
- Évaluation périodique d'alignement avec l'objectif principal.

### Événements déclencheurs non rythmiques

**Initiés par l'utilisateur** (entrée par le chat)
- Rapport de blessure → Recovery Coach prend la main en takeover, overlay activé.
- Changement d'objectif → Onboarding Coach, bloc objectifs (re-entrée partielle).
- Changement de contraintes → Onboarding Coach, bloc contraintes (re-entrée partielle).
- Voyage ou perturbation planifiée → ajustement temporaire.
- Demande de pause volontaire → plan suspendu.
- Question libre → routing Head Coach.

**Détectés par le système** (entrée par le service de monitoring, pas par le chat)
- **Déviation HRV ou autre métrique quotidienne : 2 jours consécutifs** de variation > 1 écart-type par rapport à la moyenne de base → alerte Recovery, possible ajustement de charge. (Une journée isolée n'est pas une tendance.)
- RPE systématiquement au-dessus du prescrit → charge sous-calibrée ou stress exogène, Head Coach ouvre conversation.
- Non-exécution répétée (> 2 séances manquées sur 7) → Head Coach ouvre conversation.
- Sommeil dégradé persistant → Recovery Coach.
- Déviation nutritionnelle persistante (V3, energy availability) → Nutrition / Energy Coach.
- Approche d'échéance → repriorisation, peaking.

### Plafond de pro-activité
**Maximum 2 messages Head Coach non sollicités par semaine**, hors rapport hebdomadaire. Le plafond s'applique aux événements système qui déclenchent une conversation proactive. Les mutations silencieuses de l'`AthleteState` (ajustements marginaux sans message utilisateur) ne comptent pas.

### Seuils d'interruption longue déclenchant retour `assessment_mode`

| Domaine | Seuil |
|---|---|
| Disciplines sport hors lifting | 14 jours |
| Lifting | 28 jours |
| Fonctions (nutrition, recovery) | 14 jours |

La règle des 28 jours pour le lifting s'applique uniquement si le lifting est au `coaching_scope` en `"full"`. Si lifting absent ou en `tracking`/`disabled`, règle 14 jours partout.

### Modes d'échec
- **Ghosting progressif.** Relance passive à 7 j, message Head Coach à 14 j, basculement en `assessment_mode` à la reprise au-delà de 21 j sans logs.
- **Exécution sans adhésion aux recommandations.** Surface le décalage sans moralisation. Si persiste, proposer passage en `tracking`.
- **Blessure grave.** Suspension complète, Recovery Coach pilote, retour baseline partielle ou totale conditionné au feu vert.
- **Interruption longue.** Retour `assessment_mode` selon seuils ci-dessus. Baseline peut être accélérée si données récentes disponibles, pas contournée.
- **Objectif invalidé en cours.** Onboarding Coach, redéfinition.

---

## Préoccupations transversales

### Unification des coaches côté utilisateur
Coach unifié en façade par défaut. Transition Recovery Coach lors de blessure à concevoir en session UX dédiée. Objectif : transition fluide, pas d'effet « on te passe à quelqu'un d'autre ». Possibilité : changement de cadre visuel (encart clinique) sans changement d'identité nommée.

### Modes d'intervention des spécialistes

Les agents spécialistes interviennent selon trois modes distincts. Le choix du mode conditionne la visibilité façade, le propriétaire du tour conversationnel et la structure de l'orchestration.

**Consultation silencieuse.** Le spécialiste produit une sortie structurée (plan, questions, diagnostic) que le Head Coach reformule en façade. L'utilisateur ne voit que le Head Coach. Cas : coachs disciplines en génération de plan (Phases 3, 6, régénération de bloc) ; Onboarding Coach en Phase 5 ; Nutrition Coach sur check-in calories.

**Délégation sous-graphe.** Le spécialiste détient le tour conversationnel pendant une phase déterminée, mais le nommage et le cadre visuel restent ceux du coach unifié. Le Head Coach a passé la main, pas le micro. À la sortie, contrôle rendu au Head Coach avec un payload de transition. Cas : Onboarding Coach en Phase 2 ; re-entrée onboarding partielle sur changement d'objectif ou de contraintes (overlay `onboarding_reentry_active`).

**Takeover explicite UX.** Le spécialiste devient visible, le cadre visuel change (encart clinique), l'utilisateur comprend qu'il change de registre. La règle d'opacité est volontairement brisée parce que la situation clinique l'exige. Cas unique V1 : Recovery Coach sur blessure ou pause clinique (overlay `recovery_takeover_active`).

### Deux points d'entrée au système

Les interactions avec le parcours utilisateur entrent au système par deux voies distinctes qui convergent toutes deux sur le Head Coach mais ont des contraintes de sortie différentes.

**Entrée utilisateur.** Message de l'utilisateur dans le chat. Aucun plafond, réponse attendue à chaque message. Route principale de toutes les Phases 0–6 et des événements initiés utilisateur en Phase 7.

**Entrée système.** Service de monitoring qui évalue les seuils Phase 7 sur l'`AthleteState` (HRV sur 2 jours, RPE, compliance, interruption longue, sommeil, nutrition). Sortie de deux types : mutation silencieuse de l'`AthleteState` (ajustement marginal de charge, pas de message utilisateur) ou ouverture d'une conversation proactive Head Coach soumise au plafond 2/semaine. Cette entrée n'est pas accessible à l'utilisateur et n'est pas déclenchée par un message.

### Réversibilité du `coaching_scope`
Autorisé à tout moment.
- `full → tracking` sur un domaine : arrête la prescription, conserve les données.
- `tracking → full` sur un domaine : déclenche Phase 2 partielle (blocs du domaine + transversaux si absents).
- `disabled → full` ou `tracking` : activation normale.

### Données historiques à l'arrivée
Import rétroactif des données connecteurs. Impact :
- **Phase 2** : radar peut être pré-rempli partiellement.
- **Phase 3–5** : baseline raccourcie uniquement pour intermédiaire/avancé avec ≥ 3 mois activité régulière.
- **Phase 6** : calibration initiale plus précise.

### V3 — cycles hormonaux
Placeholders respectés :
- Champ `cycle_active: bool` sur AthleteProfile.
- Modulation de la durée baseline (14 j F avec cycle actif).
- Future modulation du plan par phase du cycle (Phase C / V3).

### Révision vs abandon d'objectif
- **Révision** (date cible, niveau visé) : traitée en Head Coach.
- **Abandon / nouvel objectif principal** : Onboarding Coach complet sur bloc objectifs (mode délégation, overlay `onboarding_reentry_active`).

---

## Résumé des règles structurantes

### Règles de schéma (Phase B)
1. Stockage interne métrique, unités user en affichage.
2. Date de naissance stockée, âge dérivé.
3. `coaching_scope` dict par domaine : lifting, running, swimming, biking, nutrition, recovery × `full`/`tracking`/`disabled`.
4. Sous-modèles : `ExperienceProfile`, `ObjectiveProfile`, `InjuryHistory`, `PracticalConstraints`.
5. Classement 4×3 avec niveau de confiance par dimension.
6. `assessment_mode: bool` sur `AthleteState`.
7. `active_plan` en blocs énumérés + titrés, un seul bloc `detail_level: "full"` à la fois.
8. Champ V3 `cycle_active: bool`.
9. `journey_phase: enum` sur `AthleteState` avec 7 valeurs principales + 2 booléens overlay (`recovery_takeover_active`, `onboarding_reentry_active`).

### Règles de durée
- Baseline H : 7 j. F cycle actif : 14 j. F sans cycle : 7 j.
- Extension multi-disciplines : +2 j par discipline au-delà de 2, plafond 21 j.
- Délai max avant réexécution baseline confirmée : 30 j.
- Délai max en `assessment_mode` avant révision : 45 j.
- Seuil ghosting : 7/14/21 j.
- Seuil interruption longue : 14 j toutes disciplines, 28 j lifting.

### Règles de seuils
- Compliance minimale baseline : 70 % séances + 1 représentative par modalité.
- Séance représentative : ≥ 70 % volume + ≥ 80 % intensité (défaut, à affiner par discipline Phase C).
- Tolérance écarts : < 30 % silencieux, ≥ 30 % surface.
- Seuil skip onboarding : > 50 % questions d'un bloc skippées → bloc insuffisant.
- Déviation HRV : > 1 écart-type sur 2 jours consécutifs.
- Pro-activité Head Coach : ≤ 2 messages/semaine hors hebdo.
- Historique connecteur riche : ≥ 3 mois activité régulière.

### Règles d'agents
- **Head Coach** : façade constante, orchestrateur, route vers les spécialistes selon `journey_phase` et l'intent du message. Décide du mode d'intervention (consultation / délégation / takeover).
- **Onboarding Coach** : pilote Phase 2 en mode **délégation** ; alimente Head Coach en Phase 5 en mode **consultation** ; re-entrées partielles sur changement d'objectif ou de contraintes en mode **délégation** (overlay).
- **Recovery Coach** : prend la main en mode **takeover** explicite sur blessure ou pause activité baseline. Cadre UX distinct de la façade coach unifié.
- **Coachs disciplines** (Lifting, Running, Swimming, Biking) : travaillent en mode **consultation** silencieuse sauf exceptions cliniques. Invoqués pour génération de plan, régénération de bloc, et diagnostic sur anomalies spécifiques à leur discipline.
- **Nutrition Coach** : mode **consultation** silencieuse pour check-ins et ajustements nutritionnels, intégrés dans les réponses Head Coach.
- **Energy Coach** (V3) : mode **consultation** silencieuse pour calcul d'énergie disponible et détection RED-S.

### Règles d'entrée système
- Deux points d'entrée : chat utilisateur (aucun plafond), monitoring système (plafond 2 messages proactifs Head Coach par semaine).
- Monitoring système produit soit une mutation silencieuse d'`AthleteState`, soit un événement consommé par l'orchestrateur qui déclenche une conversation Head Coach.

---

## Suites

**A3 — Roster des agents consolidé.** Liste définitive des agents, responsabilités, scopes `_AGENT_VIEWS`, delta vs existant. À partir de ce document + `agent-flow-langgraph.md`.

**Phase B.** Spécification exhaustive des sous-modèles de `AthleteProfile` et des ajustements `_AGENT_VIEWS`. Inclut la formalisation du champ `journey_phase` et des overlays.

**Phase C.** Par agent, dans l'ordre : Onboarding → Lifting → Running → Nutrition → Recovery → Energy → Head Coach. C'est dans cette phase que sont formalisées les définitions opérationnelles par discipline (séance représentative, seuils, quantité minimale de signal) et les prompts système par agent.

**Phase D.** Implémentation backend. Création du service d'orchestration (Coordinator), des cinq graphes LangGraph identifiés en A2, et du service de monitoring.
