# Plan — faire de Resilio un vrai coach conversationnel

**Date :** 2026-08-21
**Déclencheur :** premier test réel sur Telegram (20 août, 20:50–21:04). Trace complète dans `telegram_history/result.json`.
**Verdict de l'athlète :** « l'objectif d'avoir un coach ai n'est pas du tout atteint ».

---

## 1. Diagnostic — cinq symptômes, quatre causes

### La cause racine, partagée par les symptômes 1, 2 et 3

`_block_question()` dans `backend/app/graphs/onboarding.py` construit chaque appel LLM ainsi :

```python
instruction = _BLOCK_INSTRUCTIONS[block]          # texte figé
context = f"Athlete context:\n{view.model_dump_json()}"
return _call_head_coach(instruction, context)
```

C'est **tout ce que le modèle reçoit**. Pas l'historique de la conversation. Pas `collected_data`. Pas la date du jour.

Chacune des six questions est donc générée dans un isolement total. Le modèle n'exécute pas une conversation : il remplit un formulaire dont on lui dicte la case courante.

| Symptôme | Conséquence directe |
|---|---|
| « on dirait des réponses pré-enregistrées » | Le modèle applique une instruction figée par bloc. Il ne converse pas, il récite une case de formulaire. |
| « il repose des questions déjà répondues » | Le modèle **ne peut pas voir** les réponses précédentes. À 20:55 il redemande l'objectif donné à 20:54 ; à 20:56 il redemande l'historique de course ; à 21:01 il redemande la distance cible. |
| « il pense que septembre 2026 est dans 60 semaines » | La date du jour n'est jamais dans le prompt. Le modèle raisonne depuis son propre a priori temporel : « septembre 2026 représente environ 60+ semaines, pas 4 ». |

**Preuve supplémentaire :** `chat_messages` contient **0 ligne**. Aucune mémoire de conversation n'existe nulle part.

### Fuite d'échafaudage interne vers l'athlète

Le modèle a renvoyé, verbatim dans Telegram :

```
Profil reçu depuis l'onboarding :
...
Ces données sont déjà enregistrées. Rien à collecter ici.
---
Message à l'athlète :
```

et

```
Athlete #1a2d73d5 — Profil initial
```

Il produit sa structure de travail interne et l'envoie telle quelle. Aucune séparation entre le raisonnement et le message.

### L'extraction perd ou déforme les données (symptômes 4 et 5)

Écrit dans la ligne athlète après les six blocs :

| Champ | Valeur | Ce que l'athlète a dit |
|---|---|---|
| `sports_json` | `["running"]` | « Course à pied **et lifting** » |
| `hours_per_week` | `3.0` | « je vise **3 sorties** », 8 h disponibles |
| `vdot` | `None` | « 5 km : 26:47, 10 km : 1:04:43 » |
| `goals_json` | `["compléter en 2h ou moins"]` | semi-marathon 21,1 km, Usti nad Labem |

Trois défauts distincts :

1. **`_BLOCK_INSTRUCTIONS` et `_BLOCK_TARGETS` ont été écrits séparément et ne correspondent pas.** Le bloc 2 demande à l'athlète un chrono de référence ; l'extracteur du bloc 2 ne cherche que âge/sexe/poids/taille. Les deux chronos donnés sont partis à la poubelle.
2. **Séances ≠ heures.** « 3 sorties » est devenu `hours_per_week = 3.0`, ce qui a plafonné la semaine à 1 h 30.
3. **Le scope se rétrécit silencieusement.** « Prioriser la course » a effacé le lifting de `sports_json`. `build_agents()` (`routes/_agent_factory.py:22`) n'instancie le `LiftingCoach` que si `Sport.LIFTING in athlete.sports` — d'où **zéro séance de musculation** dans le plan.

### Ce que le plan a produit, et pourquoi

```
Semaine du 20 août — 2 séances · 1h30 · phase compétition
```

- 2 séances au lieu de 6–8 → `hours_per_week = 3.0`
- 0 musculation → `sports_json = ["running"]`
- Un pavé de macros brutes (`carbs=3.5g/kg protein=1.8g/kg kcal≈2467…`) → `plan_renderer` recopie les notes d'agent verbatim
- `Readiness good` alors qu'aucune donnée HRV n'existe → corrigé depuis (`readiness_source`)
- `ACWR 1.24` alors que la mesure réelle est 1.54 → corrigé depuis (fenêtre en heure locale)
- `VDOT 30` → provenance non tracée ; à instrumenter

### Le silence qui trahit le plus l'absence de coach

Ses chronos donnent :

| Performance | VDOT |
|---|---|
| 5 km 26:47 | 35 |
| 10 km 1:04:43 | 31 |

Un semi sous 2 h demande environ **VDOT 36–37**. Il est à ~33, à quatre semaines de la course, et n'a jamais couru un semi.

Un vrai coach le dit. Celui-ci a accepté l'objectif sans commentaire et a sorti une semaine de 1 h 30. **C'est ça, le fond du reproche « ce n'est pas un vrai coach » — pas le ton.**

---

## 2. Décision d'architecture

Le design actuel est **un formulaire scripté qui appelle un LLM pour formuler ses cases**, doublé d'un extracteur qui tente de reconstituer les données après coup.

Il faut l'inverser : **donner au modèle la conversation et les faits, pas un script.**

Concrètement, l'onboarding cesse d'être six blocs figés. Il devient une conversation dirigée par un objectif : le modèle voit l'historique complet, voit quels champs du profil manquent encore, et demande ce qui manque avec ses propres mots. Il s'arrête quand le profil est suffisant.

Ce n'est pas un remplacement du moteur déterministe. Les allures, les zones, l'ACWR, la périodisation restent du Python testé — c'est ce qui empêche le coach d'halluciner une prescription. Ce qui change, c'est **la couche conversationnelle**, qui aujourd'hui n'a ni mémoire, ni date, ni agentivité.

---

## 3. Plan d'exécution

### Phase A — La conversation se souvient *(cause racine des symptômes 1, 2, 3)*

**A1. Persister chaque tour.** `chat_messages` existe et n'est jamais écrit sur le chemin Telegram. L'écrire pour tous les chemins, onboarding compris.

**A2. Passer l'historique à chaque appel LLM.** `_call_head_coach` et `_call_agent` prennent aujourd'hui un `messages=[{"role":"user"}]` unique. Passer la vraie liste de tours.

**A3. Mettre la date du jour dans le contexte.** `HeadCoachView` gagne `today` et `days_to_race`. Sans ça, aucun raisonnement temporel n'est fiable.

**A4. Séparer le raisonnement du message.** Contrat de sortie explicite ; ne transmettre à l'athlète que la partie destinée à l'athlète. Test : aucun `Athlete #`, aucun `Message à l'athlète :`, aucun identifiant interne dans un message sortant.

*Vérification :* rejouer la vraie conversation depuis `result.json` et vérifier qu'aucune question déjà répondue n'est reposée.

### Phase B — L'onboarding devient une conversation *(symptômes 1, 2)*

**B1. Remplacer les six blocs figés par un objectif de complétude.** Le prompt reçoit : l'historique, le profil actuel, et la liste des champs encore manquants. Le modèle choisit quoi demander et comment.

**B2. Extraire depuis toute la conversation, pas par bloc.** Supprime par construction le décalage `_BLOCK_INSTRUCTIONS` / `_BLOCK_TARGETS`.

**B3. Un chrono devient un VDOT.** Le mécanisme existe déjà (`_derive_vdot`) — il n'était simplement jamais atteint depuis le bloc où l'athlète donne ses temps.

**B4. Ne jamais rétrécir le scope en silence.** Un sport déclaré ne disparaît que si l'athlète le retire explicitement. Test dédié : « prioriser la course » ne supprime pas le lifting.

**B5. Séances ≠ heures.** Champs distincts `sessions_per_week` par sport, et `hours_per_week` séparé.

*Vérification :* rejouer la conversation réelle et vérifier que la ligne athlète finale contient running **et** lifting, 3–4 séances de chaque, VDOT ~33, objectif nommé.

### Phase C — Le plan reflète l'athlète *(symptôme 4)*

**C1. Tracer la provenance du VDOT 30.**

**C2. Le budget vient des séances déclarées**, pas d'un nombre d'heures mal extrait.

**C3. Le renderer arrête de vider les tables de macros brutes** dans le message. Un coach dit « glucides autour des séances de qualité », pas `carbs=5.5g/kg`.

**C4. Contrôle de faisabilité de l'objectif.** Quand le VDOT actuel et l'horizon rendent la cible improbable, le coach le dit et propose une cible réaliste. C'est le cœur du « vrai coach ».

*Vérification :* le plan généré contient 3–4 courses **et** 3–4 séances de musculation, et le coach commente explicitement la faisabilité du sous-2h.

### Phase D — Les données sont visiblement utilisées *(symptôme 5)*

**D1. Le coach cite ses sources.** « Tes 8 sorties des 30 derniers jours à 5:48/km de médiane », « ta séance Hevy de mardi », pas un `VDOT 30` sorti de nulle part.

**D2. Apple Health** pour HRV et sommeil, puisque Terra est hors de portée.

**D3. Instrumenter le chemin des données** pour qu'un connecteur muet se voie dans les logs au lieu de dégrader silencieusement.

---

## 4. Ordre et raison

A avant tout : sans mémoire ni date, tout le reste se construit sur du sable.
B ensuite : c'est là que la donnée entre dans le système. Une extraction fausse contamine chaque plan ultérieur.
C puis D : le plan et sa justification, une fois que le système sait enfin qui est l'athlète.

Phase A est la plus courte et débloque la plus grande part du ressenti « pas un vrai coach ».

---

## 5. Ce que je ne propose pas de changer

- **Le moteur déterministe.** VDOT, zones Daniels, DUP, ACWR, strain restent du Python testé. C'est ce qui garantit qu'une allure prescrite est juste. Le problème n'a jamais été là.
- **Le ton clinique.** L'athlète n'a pas reproché la sécheresse mais le vide. Un coach direct qui a lu tes messages est exactement la cible.
- **Le découpage en agents spécialistes.** Il fonctionne ; il n'a simplement jamais reçu les bonnes entrées.
