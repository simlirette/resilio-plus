# Tech Debt Cleanup — Design Spec
**Date:** 2026-04-16  
**Status:** Approved  
**Branch:** main

---

## Objective

Eliminate all mypy --strict errors and ruff violations in `backend/app/` before frontend code freeze. Deliver a production-ready typing baseline with pre-commit enforcement.

**Targets:**
- mypy --strict: 0 errors (from 447 in 63 files)
- ruff check: 0 errors (from 197)
- ruff format: clean
- Pre-commit hook: active on main branch

---

## Scope

**In scope:**
- `backend/app/` — all Python source files
- `pyproject.toml` — mypy + ruff config
- `.pre-commit-config.yaml` — new file
- `docs/backend/TYPING-CONVENTIONS.md` — new file

**Non-goals:**
- `frontend/` — separate session
- `tests/` — only touched if type errors surface from test imports
- `resilio/` — read-only legacy CLI
- `docs/` — parallel session owns this
- SQLAlchemy query behavior changes (migration preserves semantics)

---

## Diagnostic Baseline (2026-04-16)

### mypy --strict: 447 errors in 63 files

| Error Code | Count | Root Cause |
|---|---|---|
| `[arg-type]` | 174 | `Column[str]` passed as `str` (json.loads, str ops) |
| `[type-arg]` | 97 | Bare `dict` / `list` without generic params |
| `[assignment]` | 72 | `Column[str]` assigned to typed variable |
| `[union-attr]` | 17 | Attribute access on `Optional[T]` without guard |
| `[no-untyped-def]` | 15 | Functions missing return type annotations |
| `[no-any-return]` | 14 | `return Any` in typed function |
| `[no-untyped-call]` | 12 | Calling `log_node` (untyped decorator) from typed context |
| `[misc]` | 6 | SQLAlchemy `Base` subclass |
| `[import-untyped]` | 6 | fitparse, jose, passlib, apscheduler (no stubs) |
| `[import-not-found]` | 6 | Circular: `schemas.py ↔ db/models.py`; sentry_sdk optional |

**Top files by error count:**
- `routes/workflow.py`: 35
- `routes/sessions.py`: 33
- `integrations/nutrition/unified_service.py`: 27
- `routes/athletes.py`: 25
- `graphs/nodes.py`: 23, `routes/connectors.py`: 23
- `routes/auth.py`: 21
- `integrations/strava/oauth_service.py`: 20

### ruff check: 197 errors (58 auto-fixable)

| Code | Count | Fix type |
|---|---|---|
| E501 | 89 | Manual (wrap lines) |
| I001 | 43 | Auto-fixable (import sort) |
| E402 | 33 | Manual/noqa (main.py structural) |
| N806 | 15 | Manual (variable rename) |
| F401 | 15 | Auto-fixable (unused imports) |

### Other
- **Pydantic V2:** Clean — no `class Config:` found
- **TODO/FIXME:** 1 item (`routes/athletes.py:62`, legitimate auth comment)
- **Circular imports:** `app.models.schemas` ↔ `app.db.models`

---

## Architecture

### Lot 1 — Ruff Auto-Fix (safe)
Run `ruff check --fix` + `ruff format`. Resolves I001 (43) + F401 partial (15). No manual review needed for auto-fixes.

### Lot 2 — Third-Party Stubs + mypy Overrides
Install typed stubs where available (`types-passlib`). For libs without stubs (jose, fitparse, apscheduler), add targeted `# type: ignore[import-untyped]` with comment. For optional dep `sentry_sdk`, add `[[tool.mypy.overrides]]` with `ignore_missing_imports = true`.

```toml
[[tool.mypy.overrides]]
module = ["sentry_sdk", "sentry_sdk.*", "apscheduler.*"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["fitparse.*"]
ignore_missing_imports = true
```

### Lot 3 — SQLAlchemy Mapped[T] Migration (core)

Migrate `backend/app/db/models.py` from SQLAlchemy 1.x Column style to 2.0 `Mapped[T]` + `mapped_column()`. This resolves ~246 errors (`[arg-type]` + `[assignment]`).

**Pattern:**
```python
# Before
from sqlalchemy import Column, String
class Athlete(Base):
    id: str = Column(String, primary_key=True)
    name: str = Column(String)
    bio: Optional[str] = Column(String, nullable=True)

# After  
from sqlalchemy.orm import Mapped, mapped_column
class Athlete(Base):
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    bio: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

**Relationship pattern:**
```python
# Before
activities: List["StravaActivity"] = relationship("StravaActivity", back_populates="athlete")

# After
activities: Mapped[list["StravaActivity"]] = relationship("StravaActivity", back_populates="athlete")
```

**Constraint:** Migrate model-by-model, run `pytest tests/backend/` after each model. Do not batch all models in one edit.

### Lot 4 — Circular Imports + Type-Arg + Untyped Defs

**Circular import fix — `schemas.py ↔ db/models.py`:**

Create `backend/app/schemas/base.py` containing shared primitive types, enums, and TypedDicts that both modules need. Enforce one-way dependency:

```
schemas/base.py        ← shared enums, TypedDicts, Literal types
     ↓ imports
db/models.py           ← SQLAlchemy models, imports from schemas/base.py
     ↓ imports
models/schemas.py      ← Pydantic response models, imports from schemas/base.py
```

Re-export from original location for backwards-compat during transition:
```python
# models/schemas.py — temporary re-export
from app.schemas.base import SharedEnum  # noqa: F401
```

Remove re-exports once all importers are updated.

**Type-arg fixes (97 errors):** Mechanical — `dict` → `dict[str, Any]`, `list` → `list[SomeType]`. Add `from typing import Any` where missing.

**Untyped def/return (29 errors):** Add return type annotations to all flagged functions. For functions returning complex structures, use `dict[str, Any]` as interim type, or define TypedDict.

### Lot 5 — Graphs, Decorators, Union-Attr Guards

**`log_node` decorator typing:**
```python
from typing import TypeVar, Callable, Any
from collections.abc import Callable as CallableABC
import functools

F = TypeVar("F", bound=Callable[..., Any])

def log_node(name: str) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ...
        return wrapper  # type: ignore[return-value]
    return decorator
```

**Union-attr guards (17 errors):** Add `assert x is not None` or `if x is None: raise` before attribute access. No silent swallowing — fail fast.

**SQLAlchemy Base `[misc]` (6 errors):** Add `# type: ignore[misc]  # SQLAlchemy declarative Base` on subclass line.

### Lot 6 — Ruff Manual + Polish

**E501 (89 errors):** Wrap at 100 chars. For `agents/prompts.py` long strings, use implicit string concatenation or `textwrap.dedent`.

**E402 (33 errors in main.py):** Router imports after lifespan setup is a FastAPI pattern. Add `# noqa: E402  # FastAPI routers imported after lifespan setup` for structural cases. Restructure where possible (move imports to top, pass objects via dependency injection).

**N806 (15 errors):** Rename uppercase variables in function bodies (e.g., `Session = sessionmaker(...)` inside a function → `session_factory`).

**pyproject.toml — final lock:**
```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
```

**`.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        args: [--strict]
        additional_dependencies:
          - types-passlib
          - pydantic>=2.0
          - sqlalchemy>=2.0
```

---

## Error Handling

- `# type: ignore` only when: (a) third-party lib has no stubs, (b) SQLAlchemy declarative Base `[misc]`, (c) `log_node` return-value (typed wrapper). Every ignore must have a justifying comment.
- No bare `# type: ignore` — always `# type: ignore[specific-code]`.

---

## Testing Strategy

| After | Run |
|---|---|
| Each model in Lot 3 | `pytest tests/backend/` |
| Lot 4 (circular fix) | `pytest tests/backend/ tests/e2e/` |
| Lot 6 (final) | `pytest tests/` full suite |

Gate: all existing tests must pass. No new skips permitted.

---

## Failure Modes

**FM1 — SQLAlchemy Mapped[T] breaks queries (Critical → Mitigated)**
`relationship()`, `ForeignKey`, complex joins may differ. Mitigation: model-by-model migration with backend tests after each. Git atomic commits = easy rollback.

**FM2 — Circular import restructure breaks runtime imports (Critical → Mitigated)**
Moving types to `schemas/base.py` can break files importing from old locations. Mitigation: grep all importers before + after. Re-export from original locations during transition.

**FM3 — Pre-commit mypy fails on fresh clone without `poetry install` (Minor → Acceptable)**
Expected behavior for a typed production codebase. Document in CONTRIBUTING.md (out of scope this session).

---

## Deliverables

1. `mypy --strict backend/app/` → 0 errors
2. `ruff check backend/app/` → 0 errors
3. `ruff format --check backend/app/` → clean
4. `pytest tests/` → ≥2378 passing, 0 new failures
5. `.pre-commit-config.yaml` installed
6. `docs/backend/TYPING-CONVENTIONS.md`
7. `pyproject.toml` mypy + ruff locked to strict config
