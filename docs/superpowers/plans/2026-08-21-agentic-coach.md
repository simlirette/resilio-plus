# Plan — le coach conduit, le graphe exécute

**Date :** 2026-08-21
**Déclencheur :** second test réel (`telegram_history/ChatExport_2026-08-21/`), après les phases A/B/C.
**Vision de l'athlète :** « une conversation entre Coach AI et l'athlète comme on converse en ce moment » — c'est-à-dire une boucle agentique à outils, comme `QueryEngine` dans Claude Code.

---

## 1. Ce que le second test a montré

Trois échanges, verbatim :

```
[10:23] Simon   : Hello
[10:23] Coach   : Tu m'as indiqué 8 heures par semaine — est-ce uniquement de
                  la course, ou d'autres sports ? Et côté objectif : … ?
[10:24] Simon   : Quand est-ce que je t'ai indiqué que j'ai 8h à consacré ?
[10:24] Coach   : Pour calibrer correctement ton programme : tu pratiques
                  uniquement la course, ou d'autres sports ? Et tu travailles
                  vers un objectif précis … ?
[10:25] Simon   : Je veux recommencer l'onboarding.
[10:25] Coach   : Tu reviens sur la course — est-ce ton sport principal … ?
```

Deux défauts, une seule cause.

### Il n'écoute pas

Deux messages de l'athlète sont des **actes de langage** : une question directe, puis une demande explicite. Le coach n'y répond ni l'un ni l'autre et repose sa question, à peine reformulée, trois fois.

### Il affirme du faux

« Tu m'as indiqué 8 heures » — l'athlète ne l'a jamais dit. `hours_per_week` vient de `scripts/bootstrap_v4.py`. La vue le présente au modèle comme un fait sur l'athlète, et le modèle en fait une chose que l'athlète aurait dite.

### La cause

`_onboarding_instruction()` envoie, à **chaque** tour :

```
"Il manque encore : X. Demande à l'athlète uniquement ce qui manque."
```

La phase B a remplacé un script figé par une **instruction figée**. Même échec, un étage plus haut. Le modèle obéit à un ordre au lieu de conduire une conversation ; il ne peut pas répondre à une question, parce qu'on ne lui demande pas de répondre.

C'est la troisième fois que la même erreur revient sous une forme différente :

| Phase | Ce qui pilotait | Symptôme |
|---|---|---|
| Avant A | `_BLOCK_INSTRUCTIONS`, 6 blocs | redemande la même chose 3× |
| Après B | une instruction « demande les manques » | ignore les questions, boucle |
| Cible | rien — le modèle décide, avec des outils | conversation |

---

## 2. La décision d'architecture

**Arrêter de dire au modèle quoi dire.** Le graphe cesse de décider du contenu du tour ; il fournit des faits et des capacités.

Trois changements liés :

1. **Les manques deviennent une information, pas un ordre.** Le contexte dit « le profil ne contient pas encore X » ; il ne dit plus « demande X ». Le modèle choisit s'il répond à une question, accuse réception d'une demande, ou pose une question.

2. **Chaque fait porte sa provenance.** `declared` (l'athlète l'a dit), `measured` (venu d'un connecteur), `assumed` (valeur par défaut). Le coach ne peut plus attribuer à l'athlète ce qu'il n'a pas dit. `vdot_source` existe déjà ; c'est le même principe généralisé.

3. **Le coach reçoit des outils** et décide quand les appeler :

   | Outil | Ce qu'il fait |
   |---|---|
   | `update_profile` | écrit ce que l'athlète vient de dire |
   | `generate_plan` | construit et présente la semaine |
   | `restart_onboarding` | efface le profil et repart |
   | `get_training_data` | va chercher le détail Strava/Hevy à la demande |

   L'extraction cesse d'être une passe automatique par tour : le modèle écrit ce qu'il a compris, quand il l'a compris.

**Ce qui ne change pas.** Le moteur déterministe — allures, zones, ACWR, périodisation, VDOT depuis la table de Daniels — reste du Python testé. Les outils l'appellent ; ils ne le remplacent pas. C'est ce qui empêche le coach d'inventer une prescription, et ça n'a jamais été le problème.

---

## 3. Phases

### D1 — Le modèle décide du tour *(corrige la boucle)*

- L'instruction impérative disparaît. Le contexte devient descriptif.
- Provenance sur chaque champ du profil ; interdiction explicite d'attribuer un `assumed` à l'athlète.
- Test : rejouer les trois échanges du 21 août et vérifier que la question « quand t'ai-je dit 8h ? » reçoit une réponse, et que « je veux recommencer » est reconnu.

### D2 — Les outils

- Définir les quatre outils avec leur schéma d'entrée.
- Boucle tool-use : appeler le modèle, exécuter les `tool_use`, réinjecter les résultats, recommencer jusqu'à une réponse texte.
- Garde-fous : nombre maximal d'itérations, et un outil qui échoue rend une erreur au modèle plutôt que de faire tomber le tour.

### D3 — L'onboarding devient une conversation ordinaire

- Supprimer `_onboarding_instruction`, le compteur de blocs, `extract_profile` en passe automatique.
- Une seule boucle sert l'onboarding et le chat : la différence n'est plus le code, c'est ce que le profil contient.

### D4 — Vérification

- Rejouer les deux conversations réelles (20 et 21 août) de bout en bout.
- Critère : aucune question sans réponse, aucune répétition, aucune affirmation non fondée.

---

## 4. Ce que je ne propose pas

- **Réécrire le moteur.** Il est juste et testé.
- **Donner au modèle le droit d'écrire une allure.** Les outils calculent ; le modèle formule.
- **Supprimer l'approbation humaine.** Un plan continue de demander un bouton avant d'aller dans l'agenda.
