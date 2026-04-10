# RESILIO+ — Design des Endpoints FastAPI

> Ce document définit toutes les routes API avant l'implémentation (Session 11).
> Base URL : `/api/v1`
> Auth : JWT Bearer token sur tous les endpoints sauf `/auth`

---

## 1. AUTHENTIFICATION — `/auth`

```
POST   /auth/register          Créer un compte athlète
POST   /auth/login             Obtenir un JWT token
POST   /auth/refresh           Rafraîchir le token
POST   /auth/logout            Invalider le token
```

---

## 2. ATHLÈTES — `/athletes`

```
GET    /athletes/me            Profil de l'athlète authentifié
PUT    /athletes/me            Mettre à jour le profil
GET    /athletes/me/state      AthleteState actuel (vue complète)
```

---

## 3. ONBOARDING — `/onboarding`

```
POST   /onboarding/start       Démarrer une session de profiling (7 blocs)
POST   /onboarding/message     Envoyer un message au Head Coach (streaming)
GET    /onboarding/status      Statut du profiling (blocs complétés)
POST   /onboarding/confirm     Valider le profil et déclencher les calculs
```

---

## 4. PLANS — `/plans`

```
POST   /plans/generate         Déclencher la génération du plan hebdomadaire
GET    /plans/current          Plan de la semaine en cours
GET    /plans/{plan_id}        Plan spécifique par ID
POST   /plans/{plan_id}/confirm Confirmer le plan (ou demander une révision)
GET    /plans/history          Historique des plans (pagination)
```

---

## 5. SÉANCES — `/sessions`

```
GET    /sessions/today         Séances du jour
GET    /sessions/week          Séances de la semaine
GET    /sessions/{session_id}  Détail d'une séance
POST   /sessions/{session_id}/complete  Marquer comme complétée
POST   /sessions/{session_id}/skip      Marquer comme sautée + raison
```

---

## 6. SUIVI HEBDOMADAIRE — `/weekly-review`

```
POST   /weekly-review/start    Démarrer le bilan hebdomadaire
POST   /weekly-review/message  Message au Head Coach (streaming)
GET    /weekly-review/report   Rapport de la semaine (prévu vs réalisé)
POST   /weekly-review/confirm  Confirmer les ajustements proposés
```

---

## 7. DÉCISIONS EDGE CASES — `/decisions`

```
GET    /decisions/pending      Décisions en attente (edge cases)
POST   /decisions/{id}/respond Répondre à une décision
                               Body: { choice: "confirm" | "alternatives" | "custom", custom_text?: string }
GET    /decisions/history      Historique des décisions
```

---

## 8. FATIGUE & READINESS — `/readiness`

```
GET    /readiness/today        Score de readiness du jour + verdict (vert/jaune/rouge)
POST   /readiness/checkin      Saisie manuelle des données biométriques
                               Body: { hrv_rmssd?, sleep_hours?, sleep_quality?, fatigue_subjective? }
GET    /readiness/history      Historique 28 jours (pour calcul ACWR)
```

---

## 9. CONNECTEURS — `/connectors`

### Strava
```
GET    /connectors/strava/status          Statut de connexion
GET    /connectors/strava/auth            URL d'autorisation OAuth
GET    /connectors/strava/callback        Callback OAuth (redirect)
POST   /connectors/strava/sync            Synchroniser les activités récentes
DELETE /connectors/strava/disconnect      Déconnecter
```

### Hevy
```
GET    /connectors/hevy/status            Statut de connexion
POST   /connectors/hevy/upload-csv        Upload d'un export CSV Hevy
POST   /connectors/hevy/sync             Synchroniser via API (si disponible)
DELETE /connectors/hevy/disconnect        Déconnecter
```

### Apple Health
```
GET    /connectors/apple-health/status    Statut de connexion
POST   /connectors/apple-health/sync      Synchroniser HRV, sommeil, FC repos
```

---

## 10. NUTRITION — `/nutrition`

```
POST   /nutrition/log                     Logger un repas (texte libre NLP)
GET    /nutrition/today                   Bilan nutritionnel du jour
GET    /nutrition/plan/today              Plan nutritionnel prescrit du jour
GET    /nutrition/history                 Historique 7 jours
GET    /nutrition/search?q={query}        Recherche d'aliment (USDA/OFF/FCÉN)
```

---

## 11. EXPORTS — `/exports`

```
GET    /exports/hevy/{workout_id}         Export JSON compatible Hevy
GET    /exports/garmin/{workout_id}       Export JSON compatible Garmin Connect
GET    /exports/runna/{run_id}            Export JSON compatible Runna
```

---

## 12. CHAT — `/chat`

```
POST   /chat/message                      Message au Head Coach (streaming SSE)
GET    /chat/history                      Historique du chat
DELETE /chat/history                      Réinitialiser le chat
```

---

## FORMATS DE RÉPONSE

### Standard success
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2026-04-06T10:00:00Z"
}
```

### Standard error
```json
{
  "success": false,
  "error": {
    "code": "ACWR_LIMIT_EXCEEDED",
    "message": "ACWR > 1.5 — réduction de charge requise",
    "details": { "acwr": 1.62, "limit": 1.5 }
  },
  "timestamp": "2026-04-06T10:00:00Z"
}
```

### Streaming (SSE) pour les réponses agents
```
event: message
data: {"content": "Analyse de ton profil...", "done": false}

event: message
data: {"content": " Tu as un historique de shin splints.", "done": false}

event: message
data: {"content": "", "done": true, "decision_required": false}
```

---

## NOTES D'IMPLÉMENTATION

- Tous les endpoints agents (onboarding, weekly-review, chat) utilisent le **Server-Sent Events (SSE)** pour le streaming des réponses
- Les décisions edge cases interrompent le streaming et retournent un objet `pending_decision`
- Rate limiting : 60 req/min sur les endpoints chat, 300 req/min sur les autres
- CORS configuré pour `localhost:3000` en dev, domaine production en prod
