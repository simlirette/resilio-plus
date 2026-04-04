# ══════════════════════════════════════════════
# Stage 1 — builder : installe les dépendances
# ══════════════════════════════════════════════
FROM python:3.12-slim AS builder

WORKDIR /app

# Installer Poetry
RUN pip install --no-cache-dir poetry==1.8.4

# Copier uniquement les fichiers de dépendances
COPY pyproject.toml poetry.lock* ./

# Créer le venv dans /app/.venv et installer les dépendances prod uniquement
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root --no-interaction

# ══════════════════════════════════════════════
# Stage 2 — runtime : image légère sans Poetry
# ══════════════════════════════════════════════
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copier le venv compilé depuis le builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copier le code source
COPY . .

EXPOSE 8000

# En prod : uvicorn sans --reload
# En dev : docker-compose override avec --reload
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
