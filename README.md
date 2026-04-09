#v1

# Resilio+ : AI Hybrid Performance Orchestrator

Resilio+ est une plateforme d'orchestration multi-agents conçue pour optimiser la performance des athlètes hybrides. Contrairement aux générateurs de programmes basés sur de simples recommandations, Resilio+ agit comme un moteur de résolution de contraintes cliniques, générant des séances d'entraînement prescriptives et exactes (allures, charges, RPE).

Le système gère l'interférence métabolique (mTOR vs AMPK), la charge systémique (ACWR) et la fatigue neuromusculaire via une architecture en étoile (Hub-and-Spoke).

## Quick Start

### With Docker (recommended)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
cp .env.example .env
# Edit .env: fill in ANTHROPIC_API_KEY (required for LLM agents)
docker compose up --build
```

- **API + OpenAPI docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

### Manual dev setup

```bash
# Backend
cp .env.example .env
poetry install
poetry run uvicorn api.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Run tests

```bash
# Backend unit tests (157+)
poetry run pytest

# Frontend E2E tests (Playwright — chromium)
cd frontend
npx playwright install chromium   # one-time install
npm run test:e2e
```

---

## 🧠 Architecture Multi-Agents

Le système repose sur un agent central orchestrant plusieurs experts de domaine :

* **Head Coach (L'Orchestrateur) :** Gère la matrice de contraintes, détecte les conflits systémiques sur 3 couches (Scheduling, Overlap Musculaire, Fatigue Cumulée), et arbitre les décisions.
* **Running Coach :** Spécialiste de l'endurance. Utilise le modèle VDOT de Daniels pour prescrire des allures exactes et gère la distribution de l'intensité (TID).
* **Lifting Coach :** Spécialiste de la force et de l'hypertrophie. Gère les *Volume Landmarks* (MEV/MRV) adaptés aux athlètes hybrides et prescrit via un système de Tiers basé sur le ratio Stimulus/Fatigue.
* **Recovery Coach (Le Portier) :** Évalue la préparation (Readiness) via la biométrie (HRV, sommeil) et possède un droit de veto (Vert/Jaune/Rouge) sur chaque séance planifiée.
* **Agents en développement :** Nutrition Coach, Swimming Coach, Biking Coach.

## ⚙️ Cœur du Système : `AthleteState`

L'intégralité du contexte est maintenue dans un objet d'état dynamique, l'`AthleteState`. Cet objet circule entre les agents, accumulant la télémétrie, l'historique des blessures, les capacités biomécaniques et la fatigue résiduelle. Seul le Head Coach possède l'autorité d'écriture finale sur cet état.

## 🔌 Écosystème & Intégrations API

Resilio+ extrait et pousse les données directement vers les outils utilisés par l'athlète :

* **Strava :** Télémétrie d'endurance (GPS, Allure, FC, Cadence, Puissance).
* **Hevy :** Télémétrie de force (Exercices, Tonnage, RPE, Supersets).
* **Apple Health / Google Health Connect :** Métriques de récupération (HRV/RMSSD, FC au repos, Sommeil).
* **FatSecret / Open Food Facts / USDA :** Validation des apports macro et micronutritionnels.

## 🧬 Connaissances Scientifiques Intégrées

Les agents de Resilio+ ne s'appuient pas sur des hallucinations de LLM, mais sur des bases de données JSON strictes extraites de la littérature scientifique et de méta-analyses :
* `vdot_paces.json` : Modélisation des allures de course.
* `volume_landmarks.json` : Seuils de volume d'hypertrophie standardisés et ajustés pour l'interférence hybride.
* `muscle_overlap.json` : Matrice d'interférence neuromusculaire inter-sports.
* `exercise_database.json` : Dépôt biomécanique incluant les indications techniques (*cues*) et les SFR (*Stimulus to Fatigue Ratios*).

## 🚀 Workflow d'Exécution

1.  **Ingestion :** Collecte des données via les connecteurs API (H1).
2.  **Analyse :** Mise à jour de l'ACWR et de la fatigue par groupe musculaire (H2, H3).
3.  **Planification :** Génération des plans partiels par les agents spécialistes.
4.  **Résolution :** Le Head Coach applique la matrice de contraintes (Circuit Breaker) pour résoudre les chevauchements et l'interférence.
5.  **Déploiement :** Les séances validées sont exportées (Hevy-compatible JSON, Garmin/Runna-compatible JSON).

## 🛠 Installation & Développement

*Détails à venir suite à l'initialisation de l'environnement avec Claude Code / Superpowers.*

```bash
# Clone the repository
git clone [https://github.com/](https://github.com/)[TON_USER]/resilio-plus.git
cd resilio-plus

# Set up environment variables
cp .env.example .env

# Build and run containers
docker-compose up --build
