# Resilio

AI-powered adaptive coach for multi-sport athletes, designed to run with
Claude Code and Codex in both app and CLI environments, with local YAML/JSON persistence.

**How to use Resilio:**

> Open this folder in **Claude Code** or **Codex**, then chat with the assistant.
>
> The assistant acts as your AI coach. Resilio provides the tools, training methodology, and local data the coach uses to guide your training.

Resilio works in both app and CLI versions of Claude Code and Codex. For most users, we recommend the app versions because they are more user-friendly.

**Methodology focus (current):** Resilio is currently strongest on running methodology, grounded in frameworks from Daniels' _Running Formula_, Pfitzinger's _Advanced Marathoning_, Fitzgerald's _80/20 Running_, and FIRST's _Run Less, Run Faster_.

**Strava data usage:** During setup, Resilio connects to Strava to download and leverage the athlete's training data for analysis, planning, and adaptations. The AI coach will guide you through authentication, sync, and any rate-limit pauses.

## Start Here (Recommended: App)

1. Get the project files:
   - **New to GitHub**: Download [v0.1.0 ZIP](https://github.com/du-phan/resilio-app/archive/refs/tags/v0.1.0.zip), unzip it, then use the extracted `resilio-app-0.1.0` folder.
   - **If you use Git**:
     ```bash
     git clone https://github.com/du-phan/resilio-app.git
     cd resilio-app
     ```
2. Open this project in your app of choice:
   - **Claude app**: Open Claude app -> **Code** -> **Add folder** (select this repository).
   - **Codex app**: Open Codex app -> **Add new project** (select this repository folder).
3. Start chatting with the assistant (for example: "Let's get started"). The assistant guides setup, authentication, sync, and profile onboarding.

## Alternative: CLI

If you prefer terminal workflows, you can also use Claude Code CLI or Codex CLI by launching them from this repository folder.

## Quick Links

- `AGENTS.md` - Codex usage, skills, coaching protocols
- `CLAUDE.md` - Claude Code usage, coaching protocols
- `docs/coaching/cli/index.md` - CLI command index
- `docs/coaching/methodology.md` - Training methodology
- `docs/coaching/scenarios.md` - Practical coaching scenarios

## Coach Quickstart (CLI Commands)

```bash
# Install dependencies (Poetry recommended)
poetry install

# Create config
mkdir -p config
cp templates/settings.yaml config/settings.yaml
cp templates/secrets.local.yaml config/secrets.local.yaml

# Add Strava credentials (edit with your preferred editor)
${EDITOR:-vim} config/secrets.local.yaml

# Core session flow
poetry run resilio auth status
poetry run resilio sync
poetry run resilio profile analyze
poetry run resilio status
```

You can run those commands manually, or simply start chatting and let the assistant guide the same flow.
For full coaching workflows and behavior rules, see `AGENTS.md` and `CLAUDE.md`.

## Developer Quickstart

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Type check
poetry run mypy resilio

# Format
poetry run black resilio

# Lint
poetry run ruff resilio
```

## Architecture Snapshot

- `resilio/cli/` - Typer CLI entrypoints (`resilio`)
- `resilio/core/` - Domain logic (metrics, planning, adaptation)
- `resilio/api/` - Public API layer for agents
- `resilio/schemas/` - Pydantic models
- `data/` - Local persistence (gitignored)

## Skills

Skills live in `.agents/skills` (Codex) and `.claude/skills` (Claude Code). For selection rules and workflows, see `AGENTS.md` and `CLAUDE.md`.

## License

MIT
