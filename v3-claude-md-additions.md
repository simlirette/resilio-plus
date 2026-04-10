# V3 — Additions au CLAUDE.md
# À appliquer via /revise-claude-md au démarrage de la V3

> Ce fichier contient les sections à ajouter ou modifier dans CLAUDE.md
> quand la V2 est complète et que la branche v3 est créée.
> Après intégration dans CLAUDE.md, supprimer ce fichier.

---

## SECTION À AJOUTER : Décisions architecturales V3

Ajouter après la liste des décisions V2 dans CLAUDE.md :

```markdown
## Décisions V3 (non-négociables)

12. **Energy Coach** : 7e agent. Rôle exclusif : produire EnergySnapshot.
    Ne prescrit jamais de workouts. Fichier : `agents/energy_coach/`

13. **Charge allostatique** : Variable d'entraînement de premier ordre.
    Fatigue cognitive + professionnelle = même statut que fatigue physique.
    Calcul dans `core/allostatic.py`. Seuils dans `data/allostatic_weights.json`.

14. **Energy Availability (EA)** : Métrique de santé prioritaire.
    Calcul quotidien par Nutrition Coach. Seuil critique déclenche veto
    Recovery Coach indépendamment du HRV et de l'ACWR.
    Seuils dans `data/ea_thresholds.json`.

15. **Cycle hormonal féminin** : Intégration transversale dans tous les agents.
    Profil hormonal optionnel dans AthleteState. Ajustements par phase
    dans Lifting Coach, Running Coach, Recovery Coach, Nutrition Coach.
    Règles dans `data/hormonal_adjustments.json`.

16. **Recovery Coach veto V3** : Veto basé sur 5 composantes :
    HRV + ACWR + EA + Allostatic Score + Phase cycle.
    La pire composante détermine le cap final.

17. **Branche de travail V3** : Toujours travailler sur `v3`.
    Ne jamais merger dans `main` sans tests E2E V3 complets.
```

---

## SECTION À MODIFIER : Structure du repo

Ajouter les nouvelles entrées dans la section structure de CLAUDE.md :

```markdown
## Nouveaux fichiers V3

agents/energy_coach/
  agent.py                    — Energy Coach agent
  prescriber.py               — EnergySnapshot builder
  energy_coach_system_prompt.md

core/
  allostatic.py               — Calcul Allostatic Score
  energy_availability.py      — Calcul EA + RED-S detection
  hormonal.py                 — Cycle phases + ajustements

data/
  allostatic_weights.json     — Poids et seuils allostatic score
  hormonal_adjustments.json   — Ajustements par phase cycle
  ea_thresholds.json          — Seuils EA par sexe
  energy_coach_check_in_schema.json — Schéma check-in quotidien

docs/
  resilio-v3-master.md        — Document maître V3
  v3-knowledge-files-specs.md — Specs fichiers JSON V3

tests/v3/
  test_energy_coach.py
  test_allostatic.py
  test_energy_availability.py
  test_hormonal.py
  test_recovery_coach_v3.py
  test_e2e_v3.py
```

---

## SECTION À MODIFIER : AthleteState

Ajouter dans la description de l'AthleteState :

```markdown
## AthleteState V3 — Champs additionnels

- `energy_snapshot` : EnergySnapshot (Energy Coach output quotidien)
- `hormonal_profile` : HormonalProfile (optionnel, cycle menstruel)
- `allostatic_history` : List[AllostaticEntry] (28 derniers jours)
- `recovery_coach_veto` étendu : inclut ea_component, allostatic_component, cycle_component
```

---

## RÈGLE ABSOLUE V3 À AJOUTER

```markdown
## Règle absolue #12 (V3)
L'Energy Coach ne communique JAMAIS directement avec l'utilisateur 
sur le contenu des séances. Son seul output est un EnergySnapshot 
structuré. Tout le reste passe par le Head Coach.

## Règle absolue #13 (V3)
Si EA < seuil critique pendant 3 jours consécutifs (RED-S signal),
le Head Coach présente la situation à l'utilisateur avec une 
recommandation de réduction de charge. Il ne pose PAS de diagnostic 
médical et ne force PAS une consultation. Il informe et recommande.
```
