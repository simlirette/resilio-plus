# Phase 6 — Intégration & Polish : Design Spec

**Date:** 2026-04-09  
**Statut:** Approuvé (mode auto)

---

## Objectif

Terminer le projet Resilio Plus en rendant l'application déployable localement via Docker, en ajoutant des tests E2E du workflow complet, en rédigeant un README de qualité production, et en taguant v1.0.0.

---

## 1. Docker Compose

### Architecture

Deux services Docker, pas de base de données séparée (SQLite = fichier).

```
docker-compose.yml
├── backend    — FastAPI via uvicorn, port 8000
└── frontend   — Next.js via npm run dev, port 3000
```

SQLite persisté dans `./data/` (volume bind-mount) — même chemin qu'en dev local.

### Fichiers créés

| Fichier | Rôle |
|---------|------|
| `Dockerfile.backend` | Image Python 3.13-slim, installe Poetry, lance uvicorn |
| `Dockerfile.frontend` | Image Node 20-slim, installe npm deps, lance next dev |
| `docker-compose.yml` | Orchestre les deux services + bind-mounts |
| `.dockerignore` (×2) | Exclut `.git`, `__pycache__`, `node_modules`, `.worktrees` |

### Variables d'environnement

Le frontend a besoin de `NEXT_PUBLIC_API_URL` pour pointer vers le backend. En docker-compose, le backend est accessible via `http://backend:8000` depuis le container frontend, mais le **browser** (client) appelle toujours `http://localhost:8000`. Solution : `api.ts` continue à utiliser `http://localhost:8000` (correct pour dev local), pas de changement nécessaire car les deux ports sont exposés sur l'hôte.

### Décision technique : images dev vs prod

On utilise des images **dev** (next dev / uvicorn --reload) — suffisant pour un projet local. Pas de multi-stage build prod (hors scope).

---

## 2. Tests E2E API

### Approche

Tests pytest dans `tests/e2e/` qui testent le workflow complet end-to-end contre le backend réel (SQLite in-memory via `TestClient` de FastAPI, pas de serveur externe). Pas de Playwright — les 26 tests frontend + 286 tests backend couvrent déjà l'essentiel.

### Workflow couvert

```
POST /athletes/onboarding           → crée user + athlete + plan initial
GET  /athletes/{id}/week-status     → vérifie semaine 1
POST /athletes/{id}/review          → soumet review hebdo
GET  /athletes/{id}/plan            → vérifie plan toujours présent
POST /auth/login                    → login avec les credentials créés
```

### Fichiers

| Fichier | Contenu |
|---------|---------|
| `tests/e2e/__init__.py` | vide |
| `tests/e2e/test_full_workflow.py` | 5 tests séquentiels via TestClient |
| `tests/e2e/conftest.py` | Fixture `client` avec DB SQLite in-memory |

### Contraintes

- DB isolée par test (fixture `client` avec `create_all` + `drop_all`)
- Pas de dépendances réseau externes (Strava, Hevy moqués au niveau service)
- Les tests E2E doivent passer dans la même commande `pytest` que les tests unitaires

---

## 3. README complet

Réécriture de `README.md` avec les sections suivantes :

1. **Header** — nom, description courte, badges (Python, Next.js, tests)
2. **Quick Start (Docker)** — 3 commandes pour avoir l'app qui tourne
3. **Quick Start (Local)** — pour le dev sans Docker
4. **Architecture** — tableau des agents, diagramme ASCII du flux de données
5. **API Reference** — tableau des endpoints principaux
6. **Tech Stack** — backend + frontend + test tooling
7. **Project Structure** — arbre de fichiers annoté
8. **Development** — commandes pytest, npm test, migrations

---

## 4. Tag v1.0.0

Après que tous les tests passent (pytest + npm test) :

```bash
git tag -a v1.0.0 -m "Resilio Plus v1.0.0 — full-stack hybrid coaching platform"
```

---

## Séquence d'implémentation

1. `Dockerfile.backend` + `.dockerignore`
2. `Dockerfile.frontend` + `.dockerignore`  
3. `docker-compose.yml`
4. Tests E2E (`tests/e2e/`)
5. README complet
6. Vérification finale (pytest + npm test)
7. Tag v1.0.0

---

## Ce qui n'est PAS dans le scope

- CI/CD (GitHub Actions)
- Docker multi-stage prod
- HTTPS / reverse proxy
- Tests E2E Playwright
- Monitoring / observabilité
