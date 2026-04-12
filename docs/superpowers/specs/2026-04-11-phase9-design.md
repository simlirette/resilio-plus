# Phase 9 — Connecteurs complets : Design Spec

**Date:** 2026-04-11  
**Statut:** Approuvé  
**Dépend de:** Phase 8 (SessionLogModel), Phase 7 (Recovery Coach)

---

## Contexte

Phase 9 automatise le logging manuel de Phase 8. Les connecteurs Strava, Hevy et Terra remplacent la saisie manuelle par un sync automatique toutes les 6 heures. Un scheduler APScheduler (déjà bootstrappé dans `main.py`) orchestre les syncs en background.

### État existant — ce qui est déjà là

| Composant | État |
|---|---|
| `backend/app/connectors/strava.py` | ✅ Implémenté |
| `backend/app/connectors/hevy.py` | ✅ Implémenté |
| `backend/app/connectors/terra.py` | ✅ Implémenté |
| `backend/app/core/sync_scheduler.py` | ✅ Existe — Strava + Hevy toutes les 6h — **mais ne persiste pas les données** |
| `POST /connectors/hevy/sync` | ✅ Existe — mappe Hevy → SessionLogModel |
| `POST /connectors/terra/sync` | ✅ Existe — stocke HRV/sleep dans `extra_json` |
| `POST /connectors/strava/sync` | ✅ Existe — mappe Strava → SessionLogModel |
| `frontend/.../settings/connectors/page.tsx` | ✅ Existe — Sync now buttons pour les 3 connecteurs |
| `frontend/.../settings/page.tsx` | ✅ Existe — redirige vers /settings/connectors |

### Gaps identifiés

| Gap | Impact |
|---|---|
| Scheduler fetch mais ne persiste pas → SessionLogModel | Auto-sync silencieux et inutile |
| Terra absent du scheduler | Pas d'auto-sync HRV/sleep |
| `fetch_connector_data` ne retourne pas `terra_health` | Recovery Coach lit toujours `[]` |
| `delete_connector` = `Literal["strava", "hevy"]` seulement | Terra ne peut pas être déconnecté |
| `ConnectorListResponse` n'expose pas `last_sync` | UI ne sait pas quand le dernier sync a eu lieu |
| Pas de formulaire Connect pour Hevy (API key) | Impossible de connecter Hevy depuis l'UI |
| Pas de formulaire Connect pour Terra (user ID) | Impossible de connecter Terra depuis l'UI |

---

## Architecture

### Approche retenue : `SyncService` centralisé

Extraire toute la logique de mapping dans `backend/app/services/sync_service.py`. Les endpoints manuels ET le scheduler délèguent à ce service. Une seule source de vérité, cohérent avec `connector_service.py` et `coaching_service.py` existants.

```
backend/app/services/sync_service.py         NEW
backend/app/core/sync_scheduler.py           MODIFY
backend/app/routes/connectors.py             MODIFY
backend/app/services/connector_service.py    MODIFY
frontend/src/app/settings/connectors/page.tsx  MODIFY
frontend/src/lib/api.ts                         MODIFY
```

---

## Design détaillé

### 1. `SyncService` — `backend/app/services/sync_service.py`

Trois méthodes statiques, toutes avec la signature `(athlete_id: str, db: Session) -> dict`.

#### `sync_strava(athlete_id, db)`
1. Lit `ConnectorCredentialModel` pour provider `strava`
2. Instancie `StravaConnector`, fetch les 7 derniers jours d'activités
3. Si le token est rafraîchi pendant le fetch, persiste le nouveau token dans `ConnectorCredentialModel`
4. Mappe les activités → `SessionLogModel` via `_upsert_session_log` (identique au endpoint manuel actuel)
5. Met à jour `extra_json["last_sync"]` avec `datetime.now(UTC).isoformat()`
6. Retourne `{"synced": int, "skipped": int}`

#### `sync_hevy(athlete_id, db)`
1. Lit `ConnectorCredentialModel` pour provider `hevy`, extrait `api_key` de `extra_json`
2. Instancie `HevyConnector`, fetch les 7 derniers jours de workouts
3. Mappe les workouts → `SessionLogModel` (exercices, sets, reps, poids dans `actual_data_json`)
4. Met à jour `extra_json["last_sync"]`
5. Retourne `{"synced": int, "skipped": int}`

#### `sync_terra(athlete_id, db)`
1. Lit `ConnectorCredentialModel` pour provider `terra`
2. Instancie `TerraConnector`, fetch les données du jour
3. Stocke dans `extra_json` : `last_hrv_rmssd`, `last_sleep_hours`, `last_sleep_score`, `last_steps`, `last_sync`
4. Retourne `{"synced": 1, "hrv_rmssd": float|None, "sleep_hours": float|None}`

**Gestion d'erreurs :** Chaque méthode lève `ConnectorNotFoundError` (404-friendly) si le credential n'existe pas. Les erreurs de l'API externe (`httpx`, réseau) sont propagées pour que l'appelant décide.

---

### 2. `sync_scheduler.py` — ajout Terra + délégation à SyncService

`sync_all_strava` et `sync_all_hevy` sont réécrits pour déléguer à `SyncService`. `sync_all_terra` est ajouté.

Pattern commun pour chaque `sync_all_X` :
```python
def sync_all_terra() -> None:
    with SessionLocal() as db:
        creds = db.query(ConnectorCredentialModel).filter_by(provider="terra").all()
        for cred_model in creds:
            try:
                SyncService.sync_terra(cred_model.athlete_id, db)
                logger.info("Terra sync OK: athlete=%s", cred_model.athlete_id)
            except Exception:
                logger.warning("Terra sync failed: athlete=%s", cred_model.athlete_id, exc_info=True)
```

`setup_scheduler` ajoute un 3e job :
```python
scheduler.add_job(sync_all_terra, trigger="interval", hours=6, id="terra_sync", ...)
```

---

### 3. `connectors.py` — refactor des endpoints manuels + fixes

**Endpoints manuels :** `hevy_sync`, `terra_sync`, `strava_sync` délèguent à `SyncService` :
```python
@router.post("/{athlete_id}/connectors/strava/sync")
def strava_sync(athlete_id, db, _):
    return SyncService.sync_strava(athlete_id, db)
```

**Fix `delete_connector` :** `Literal["strava", "hevy"]` → `Literal["strava", "hevy", "terra"]`

**Fix `list_connectors` :** lit `extra_json["last_sync"]` de chaque credential et le passe dans `ConnectorStatus` :
```python
ConnectorStatus(
    provider=c.provider,
    connected=True,
    expires_at=c.expires_at,
    last_sync=json.loads(c.extra_json or "{}").get("last_sync"),
)
```

---

### 4. `connector_service.py` — fix Terra pipeline

`fetch_connector_data` est étendu pour lire les données Terra cachées depuis `extra_json` :

```python
# Après la section Hevy
terra_model = db.query(ConnectorCredentialModel).filter_by(
    athlete_id=athlete_id, provider="terra"
).first()
terra_health: list[TerraHealthData] = []
if terra_model:
    extra = json.loads(terra_model.extra_json or "{}")
    if extra.get("last_hrv_rmssd") is not None or extra.get("last_sleep_hours") is not None:
        terra_health = [TerraHealthData(
            date=date.today(),
            hrv_rmssd=extra.get("last_hrv_rmssd"),
            sleep_duration_hours=extra.get("last_sleep_hours"),
            sleep_score=extra.get("last_sleep_score"),
            steps=extra.get("last_steps"),
            active_energy_kcal=None,
        )]

return {
    "strava_activities": strava_activities,
    "hevy_workouts": hevy_workouts,
    "terra_health": terra_health,
}
```

`recovery.py` fonctionne immédiatement après ce fix sans aucune modification.

---

### 5. `ConnectorStatus` schema — ajout `last_sync`

`backend/app/schemas/connector_api.py` :
```python
class ConnectorStatus(BaseModel):
    provider: str
    connected: bool
    expires_at: int | None = None
    last_sync: str | None = None   # ISO datetime UTC string
```

---

### 6. Frontend — `settings/connectors/page.tsx`

**6a — Type ConnectorStatus étendu :**
```typescript
type ConnectorStatus = {
  provider: string
  connected: boolean
  expires_at?: number | null
  last_sync?: string | null      // nouveau
}
```

**6b — Helper `formatLastSync` :**
```typescript
function formatLastSync(iso: string | null | undefined): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}
```

Affiché sous le badge de statut dans chaque carte : `Last synced: {formatLastSync(lastSync)}`.

**6c — Hevy Connect form :**

Quand `!isConnected('hevy')`, afficher dans `CardContent` :
```
[input: API Key] [Connect button]
```
`onClick` → `api.connectHevy(athleteId, apiKey)` → refresh connectors.

**6d — Terra Connect form :**

Quand `!isConnected('terra')`, afficher :
```
[input: Terra User ID] [Connect button]
```
`onClick` → `api.connectTerra(athleteId, terraUserId)` → refresh connectors.

**6e — Disconnect buttons :**

Hevy et Terra : ajouter bouton Disconnect (appelle `DELETE /connectors/{provider}`). Strava a déjà ce pattern implicitement via le bouton Connect.

---

### 7. `api.ts` — mise à jour types

```typescript
getConnectors: (athleteId: string): Promise<{
  connectors: Array<{
    provider: string
    connected: boolean
    expires_at?: number | null
    last_sync?: string | null    // nouveau
  }>
}>
```

Ajouter `connectHevy` si absent :
```typescript
connectHevy: (athleteId: string, apiKey: string) =>
  request(`/athletes/${athleteId}/connectors/hevy`, {
    method: 'POST',
    body: JSON.stringify({ api_key: apiKey }),
  }),
```

---

## Tests

### Nouveaux fichiers de test

| Fichier | Contenu |
|---|---|
| `tests/backend/services/test_sync_service.py` | `sync_strava` crée SessionLogModel + met à jour `last_sync` ; `sync_hevy` idem ; `sync_terra` stocke HRV dans `extra_json` + met à jour `last_sync` ; erreur 404 si credential absent |
| `tests/backend/core/test_sync_scheduler.py` | `setup_scheduler` retourne un scheduler avec 3 jobs : `strava_sync`, `hevy_sync`, `terra_sync` |
| `tests/backend/api/test_connectors_phase9.py` | `list_connectors` retourne `last_sync` ; `DELETE /connectors/terra` retourne 204 ; endpoint manuel `/strava/sync` persiste token rafraîchi |
| `tests/backend/services/test_connector_service_terra.py` | `fetch_connector_data` retourne `terra_health` non-vide quand `extra_json` contient `last_hrv_rmssd` ; retourne `[]` si `extra_json` vide |

---

## Fichiers modifiés / créés — récapitulatif

| Action | Chemin |
|---|---|
| CREATE | `backend/app/services/sync_service.py` |
| MODIFY | `backend/app/core/sync_scheduler.py` |
| MODIFY | `backend/app/routes/connectors.py` |
| MODIFY | `backend/app/services/connector_service.py` |
| MODIFY | `backend/app/schemas/connector_api.py` |
| MODIFY | `frontend/src/app/settings/connectors/page.tsx` |
| MODIFY | `frontend/src/lib/api.ts` |
| CREATE | `tests/backend/services/test_sync_service.py` |
| CREATE | `tests/backend/core/test_sync_scheduler.py` |
| CREATE | `tests/backend/api/test_connectors_phase9.py` |
| CREATE | `tests/backend/services/test_connector_service_terra.py` |

---

## Invariants à vérifier après chaque tâche

- `poetry install` passe
- `pytest tests/` passe (≥ baseline actuelle)
- `npx tsc --noEmit` sans erreurs
