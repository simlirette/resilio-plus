# Typing Conventions — Resilio+ Backend

This document codifies the typing decisions made during the mypy --strict migration (2026-04-16).
The backend runs mypy --strict with 0 errors. All new code must maintain this.

---

## mypy Configuration

```toml
[tool.mypy]
python_version = "3.13"
strict = true
exclude = ["backend/scripts/"]
```

Run: `python -m mypy backend/app/ --config-file pyproject.toml`

---

## Conventions

### 1. SQLAlchemy models — use `Mapped[T]`

All ORM columns use the declarative `Mapped[T]` + `mapped_column()` style (SQLAlchemy 2.x):

```python
from sqlalchemy.orm import Mapped, mapped_column

class MyModel(Base):
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    optional_field: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
```

Never use the old `Column(String)` style — it produces `Any` types and breaks strict mode.

### 2. `Any` for LangGraph / external graph types

LangGraph's `StateGraph`, compiled graphs, and `RunnableConfig` have complex generics.
Use `Any` for graph return types and checkpointers rather than fighting the type system:

```python
from typing import Any

def build_coaching_graph(*, checkpointer: Any, interrupt: bool = True) -> Any: ...
def get_graph_state(self, thread_id: str) -> Any: ...
```

### 3. Node functions — `Callable[..., dict[str, Any]]`

LangGraph node functions share a common signature. Use the type alias from `graphs/logging.py`:

```python
from collections.abc import Callable
from typing import Any

_NodeFunc = Callable[..., dict[str, Any]]

def log_node(func: _NodeFunc) -> _NodeFunc: ...
```

All node functions return `dict[str, Any]`:

```python
def my_node(state: AthleteCoachingState, config: RunnableConfig) -> dict[str, Any]:
    ...
```

### 4. `Self` for connector `__enter__`

Connector subclasses use `Self` so `with StravaConnector(...) as c:` types `c` as `StravaConnector`:

```python
from typing import Self

class BaseConnector:
    def __enter__(self) -> Self:
        return self
```

### 5. Literal types for DB → Pydantic conversions

When reading string columns that map to `Literal` types in schemas, use `cast()`:

```python
from typing import cast, Literal

sex = cast(Literal["M", "F", "other"], row.sex)
coaching_mode = cast(Literal["full", "tracking_only"], row.coaching_mode)
```

When assigning to a variable (not passing directly), use an annotation:

```python
phase: Literal["onboarding", "no_plan", "active", "weekly_review_due"] = (
    "no_plan" if athlete.target_race_date else "onboarding"
)
```

### 6. `AsyncGenerator[None, None]` for lifespan

```python
from collections.abc import AsyncGenerator

async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
```

### 7. Connectors — `_request` returns `Any`

The base `_request` method returns `Any` because endpoints may return either `dict` or `list`:

```python
def _request(self, method: str, url: str, **kwargs: Any) -> Any: ...
```

Callers narrow the type themselves as needed.

### 8. Lazy-imported model classes — lowercase variable names

When model classes are imported dynamically (to avoid SQLAlchemy double-registration), use
lowercase `_cls` suffix to satisfy N806:

```python
import importlib
_db_models = importlib.import_module("app.db.models")
_plan_model_cls = _db_models.TrainingPlanModel
_review_model_cls = _db_models.WeeklyReviewModel
```

### 9. Function-local dicts — lowercase variable names

Ruff N806 forbids uppercase variable names in functions. Use lowercase:

```python
# OK
_intensity = {"easy_z1": 1.0, "tempo_z2": 1.5}
_tier_note = {"general_prep": "Tier 1"}
_z = FatigueScore(...)

# NOT OK (N806)
_INTENSITY = {...}
_TIER_NOTE = {...}
_Z = FatigueScore(...)
```

Module-level constants stay UPPER_CASE.

### 10. Mocking-safe attribute access

When accessing attributes on objects that may be mocks in tests, prefer `getattr` over `isinstance`:

```python
# OK — works with real objects and MagicMock
raw_text: str = getattr(block, "text", "")

# Breaks test mocks:
if isinstance(block, TextBlock):
    raw_text = block.text
```

---

## ruff Configuration

```toml
[tool.ruff.lint.per-file-ignores]
"backend/app/agents/prompts.py" = ["E501"]   # system prompts — not wrappable
"backend/app/main.py" = ["E402"]              # lifespan import ordering
"backend/scripts/**" = ["E402", "E501", "N806"]  # utility scripts
```

Long imports after module-level code (observability singletons) use `# noqa: E402` inline.

---

## Pre-commit

`.pre-commit-config.yaml` at repo root runs ruff + mypy on every commit.

Install: `pre-commit install`
Manual run: `pre-commit run --all-files`
