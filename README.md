# Resilio Plus — Hybrid Athlete Coaching Platform

An AI-powered multi-agent coaching platform for hybrid athletes combining running, strength training, swimming, and cycling.

## What is Resilio Plus?

A **Head Coach AI** orchestrates 7 specialist agents to create personalized, periodized training and nutrition plans. Plans adapt weekly based on actual performance data from connected apps.

### Coaching Agents

| Agent | Specialty |
|---|---|
| Head Coach | Orchestration, conflict resolution, load management |
| Running Coach | Economy, biomechanics, injury prevention (Daniels/Pfitzinger/80-20/FIRST) |
| Lifting Coach | Hypertrophy, strength, MEV/MAV/MRV, SFR |
| Swimming Coach | SWOLF, CSS-based zones, propulsive efficiency |
| Biking Coach | FTP, Coggan zones, TSS/CTL/ATL/TSB |
| Nutrition Coach | Carb periodization, evidence-based supplementation |
| Recovery Coach | HRV-guided training, sleep banking, Readiness Score |

### Connected Apps

| App | Data | Status |
|---|---|---|
| Strava | Running, cycling, swimming (GPS, HR, power) | Active |
| Hevy | Strength training (sets, reps, load, volume) | Phase 3 |
| FatSecret | Nutrition (macros, micros, food journal) | Phase 3 |
| Apple Health | HRV, sleep, steps (via Terra API) | Phase 3 |

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLite, Poetry
- **Frontend**: Next.js, React, Tailwind CSS, shadcn/ui
- **AI**: Claude (Anthropic) via multi-agent architecture
- **Legacy CLI**: Typer (preserved for development and debug)

## Project Status

| Phase | Scope | Status |
|---|---|---|
| Phase 0 | Repo setup, scaffold, CLAUDE.md | ✅ Complete |
| Phase 1 | Data schemas, agent definitions | Upcoming |
| Phase 2 | Agent implementations (backend) | Upcoming |
| Phase 3 | API connectors, FastAPI routes | Upcoming |
| Phase 4 | Next.js frontend | Upcoming |
| Phase 5 | Weekly review loop, E2E | Upcoming |

## Getting Started (Development)

```bash
# Install dependencies
poetry install

# Verify environment
poetry run resilio --help

# Run tests
poetry run pytest
```

## Origin

Based on [resilio-app](https://github.com/du-phan/resilio-app) by du-phan — a running coach CLI with Strava integration. The running methodology and VDOT calculator from resilio-app power the Running Coach agent.
