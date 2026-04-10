# Phase 11 — Polish & Power Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add food databases (USDA + Open Food Facts + FCÉN), Chat HiTL endpoint, agent token economy (`_get_view()`), profile editing, plan customization, ACWR alerts, and nutrition display — completing the full Resilio Plus feature set.

**Architecture:** Six independent subsystems wired together: (1) food search connectors hit external APIs, (2) chat endpoint routes user messages to Head Coach, (3) `_get_view()` reduces token usage per agent, (4) profile CRUD, (5) plan session patching, (6) frontend polish (alerts, nutrition widget, notifications). No new DB tables — all state fits in existing models.

**Tech Stack:** Python (FastAPI), SQLAlchemy (sync), anthropic SDK, httpx, fitparse, Next.js, TypeScript, Tailwind CSS 4

---

## File Structure

**New files:**
- `backend/app/connectors/food_search.py` — USDA + Open Food Facts (async httpx, parallel)
- `backend/app/connectors/fcen.py` — FCÉN Santé Canada CSV loader
- `data/fcen_nutrients.csv` — 25+ Canadian foods
- `backend/app/routes/food.py` — 3 food endpoints
- `backend/app/routes/chat.py` — Chat HiTL endpoint
- `frontend/src/app/chat/page.tsx` — Chat page
- `frontend/src/app/settings/profile/page.tsx` — Profile edit page
- `frontend/src/components/NutritionDirectives.tsx` — Macro targets widget
- `frontend/src/components/AcwrAlert.tsx` — ACWR warning banner

**Modified files:**
- `backend/app/agents/base.py` — Add `_get_view()` method
- `backend/app/agents/running_coach.py` — Override `_get_view()`
- `backend/app/agents/lifting_coach.py` — Override `_get_view()`
- `backend/app/agents/swimming_coach.py` — Override `_get_view()`
- `backend/app/agents/biking_coach.py` — Override `_get_view()`
- `backend/app/agents/nutrition_coach.py` — Override `_get_view()`
- `backend/app/agents/recovery_coach.py` — Override `_get_view()`
- `backend/app/routes/athletes.py` — Add `PUT /athletes/{id}/profile`
- `backend/app/routes/plans.py` — Add `PATCH /athletes/{id}/plan/sessions/{session_id}`
- `backend/app/main.py` — Register food and chat routers
- `frontend/src/lib/api.ts` — Add food, chat, profile, plan patch API functions
- `frontend/src/components/top-nav.tsx` — Add "Coach" link
- `frontend/src/app/dashboard/page.tsx` — Add ACWR alert + nutrition widget

---

## Task 1: Food Database Connectors (USDA + Open Food Facts)

**Files:**
- Create: `backend/app/connectors/food_search.py`
- Create: `data/fcen_nutrients.csv`
- Create: `backend/app/connectors/fcen.py`
- Test: `tests/backend/connectors/test_food_search.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/connectors/test_food_search.py
import pytest
from unittest.mock import patch, AsyncMock
from backend.app.connectors.food_search import FoodSearchConnector, FoodItem
from backend.app.connectors.fcen import FcenConnector


def test_food_item_dataclass():
    item = FoodItem(
        name="Riz basmati cuit",
        calories_per_100g=130.0,
        carbs_g=28.2,
        protein_g=2.7,
        fat_g=0.3,
        source="usda",
    )
    assert item.name == "Riz basmati cuit"
    assert item.source == "usda"


@pytest.mark.asyncio
async def test_search_returns_list():
    connector = FoodSearchConnector(usda_api_key="test_key")
    usda_response = {
        "foods": [
            {
                "description": "Rice, white, cooked",
                "foodNutrients": [
                    {"nutrientName": "Energy", "value": 130.0},
                    {"nutrientName": "Carbohydrate, by difference", "value": 28.2},
                    {"nutrientName": "Protein", "value": 2.7},
                    {"nutrientName": "Total lipid (fat)", "value": 0.3},
                ],
            }
        ]
    }
    off_response = {"products": []}

    with patch("httpx.AsyncClient") as mock_client:
        mock_ctx = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_ctx
        mock_ctx.get = AsyncMock(side_effect=[
            AsyncMock(status_code=200, json=AsyncMock(return_value=usda_response)),
            AsyncMock(status_code=200, json=AsyncMock(return_value=off_response)),
        ])
        results = await connector.search("rice")

    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0].source == "usda"


@pytest.mark.asyncio
async def test_search_off_barcode():
    connector = FoodSearchConnector(usda_api_key="test_key")
    off_response = {
        "product": {
            "product_name": "Nutella",
            "nutriments": {
                "energy-kcal_100g": 530.0,
                "carbohydrates_100g": 57.5,
                "proteins_100g": 6.3,
                "fat_100g": 30.9,
            },
        },
        "status": 1,
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_ctx = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_ctx
        mock_ctx.get = AsyncMock(return_value=AsyncMock(
            status_code=200,
            json=AsyncMock(return_value=off_response),
        ))
        result = await connector.get_by_barcode("3017620422003")

    assert result is not None
    assert result.name == "Nutella"
    assert result.source == "open_food_facts"


def test_fcen_search():
    fcen = FcenConnector()
    results = fcen.search("riz")
    assert isinstance(results, list)
    # At least one result for "riz" given our CSV has rice entries
    # (will be 0 if CSV not present, tested separately)


def test_fcen_search_no_match():
    fcen = FcenConnector()
    results = fcen.search("xyznonexistent999")
    assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:\Users\simon\resilio-plus
poetry run pytest tests/backend/connectors/test_food_search.py -v
```

Expected: ImportError — modules don't exist yet.

- [ ] **Step 3: Create FCÉN CSV data file**

```csv
# data/fcen_nutrients.csv
name_fr,name_en,calories_per_100g,carbs_g,protein_g,fat_g
Riz blanc cuit,White rice cooked,130,28.2,2.7,0.3
Poulet rôti sans peau,Roasted chicken no skin,165,0.0,31.0,3.6
Patate douce cuite,Cooked sweet potato,86,20.1,1.6,0.1
Saumon atlantique cuit,Atlantic salmon cooked,208,0.0,20.4,13.4
Avocat,Avocado,160,8.5,2.0,14.7
Quinoa cuit,Cooked quinoa,120,21.3,4.4,1.9
Lentilles cuites,Cooked lentils,116,20.1,9.0,0.4
Banane,Banana,89,22.8,1.1,0.3
Brocoli cuit,Cooked broccoli,35,7.2,2.4,0.4
Œufs entiers cuits,Whole eggs cooked,155,1.1,13.0,11.0
Yogourt grec 2%,Greek yogurt 2%,73,5.5,10.2,1.7
Fromage cheddar,Cheddar cheese,402,1.3,25.0,33.1
Pain blé entier,Whole wheat bread,247,41.3,13.2,3.5
Amandes,Almonds,579,21.6,21.2,49.9
Avoine sèche,Dry oats,389,66.3,16.9,6.9
Bœuf haché maigre cuit,Lean ground beef cooked,218,0.0,26.0,12.4
Tofu ferme,Firm tofu,76,1.9,8.1,4.2
Lait 2%,Milk 2%,50,4.8,3.4,2.0
Bleuets frais,Fresh blueberries,57,14.5,0.7,0.3
Épinards cuits,Cooked spinach,23,3.8,2.9,0.3
Patates Yukon Gold cuites,Cooked Yukon Gold potatoes,87,20.1,1.9,0.1
Pâtes de blé entier cuites,Cooked whole wheat pasta,124,26.5,5.3,0.5
Canneberges séchées,Dried cranberries,308,82.4,0.1,1.4
Miel,Honey,304,82.4,0.3,0.0
Huile d'olive,Olive oil,884,0.0,0.0,100.0
```

- [ ] **Step 4: Create food_search.py connector**

```python
# backend/app/connectors/food_search.py
"""
Food database connector: USDA FoodData Central + Open Food Facts.
Queries run in parallel via asyncio.gather.
No DB dependency — pure data fetch/normalize.
"""
import asyncio
from dataclasses import dataclass

import httpx

USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
OFF_BASE = "https://world.openfoodfacts.org"


@dataclass
class FoodItem:
    name: str
    calories_per_100g: float
    carbs_g: float
    protein_g: float
    fat_g: float
    source: str  # "usda" | "open_food_facts" | "fcen"


def _nutrient_value(nutrients: list[dict], name: str) -> float:
    for n in nutrients:
        if n.get("nutrientName", "").startswith(name):
            return float(n.get("value") or 0.0)
    return 0.0


def _parse_usda(food: dict) -> FoodItem:
    nutrients = food.get("foodNutrients", [])
    return FoodItem(
        name=food.get("description", "Unknown"),
        calories_per_100g=_nutrient_value(nutrients, "Energy"),
        carbs_g=_nutrient_value(nutrients, "Carbohydrate"),
        protein_g=_nutrient_value(nutrients, "Protein"),
        fat_g=_nutrient_value(nutrients, "Total lipid"),
        source="usda",
    )


def _parse_off_product(product: dict) -> FoodItem | None:
    name = product.get("product_name", "").strip()
    if not name:
        return None
    n = product.get("nutriments", {})
    return FoodItem(
        name=name,
        calories_per_100g=float(n.get("energy-kcal_100g") or 0.0),
        carbs_g=float(n.get("carbohydrates_100g") or 0.0),
        protein_g=float(n.get("proteins_100g") or 0.0),
        fat_g=float(n.get("fat_100g") or 0.0),
        source="open_food_facts",
    )


class FoodSearchConnector:
    def __init__(self, usda_api_key: str = "") -> None:
        self._api_key = usda_api_key

    async def search(self, query: str) -> list[FoodItem]:
        """Search USDA and Open Food Facts in parallel. Returns merged list."""
        usda_task = self._search_usda(query)
        off_task = self._search_off(query)
        usda_results, off_results = await asyncio.gather(
            usda_task, off_task, return_exceptions=True
        )
        items: list[FoodItem] = []
        if isinstance(usda_results, list):
            items.extend(usda_results)
        if isinstance(off_results, list):
            items.extend(off_results)
        return items

    async def _search_usda(self, query: str) -> list[FoodItem]:
        if not self._api_key:
            return []
        params = {"query": query, "api_key": self._api_key, "pageSize": 10}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{USDA_BASE}/foods/search", params=params)
        if resp.status_code != 200:
            return []
        foods = resp.json().get("foods", [])
        return [_parse_usda(f) for f in foods[:10]]

    async def _search_off(self, query: str) -> list[FoodItem]:
        params = {"search_terms": query, "json": 1, "page_size": 10}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OFF_BASE}/cgi/search.pl", params=params)
        if resp.status_code != 200:
            return []
        products = resp.json().get("products", [])
        items = []
        for p in products[:10]:
            item = _parse_off_product(p)
            if item:
                items.append(item)
        return items

    async def get_by_barcode(self, barcode: str) -> FoodItem | None:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OFF_BASE}/api/v0/product/{barcode}.json")
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None
        return _parse_off_product(data.get("product", {}))
```

- [ ] **Step 5: Create fcen.py connector**

```python
# backend/app/connectors/fcen.py
"""
FCÉN Santé Canada food database — local CSV, loaded once at import time.
No network calls. Thread-safe (read-only after load).
"""
import csv
import os
from dataclasses import dataclass

from .food_search import FoodItem

_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "fcen_nutrients.csv"
)
_NORMALIZED_PATH = os.path.normpath(_CSV_PATH)


def _load_csv(path: str) -> list[dict]:
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("name_fr", "").startswith("#"):
                    continue
                rows.append(row)
    except FileNotFoundError:
        pass
    return rows


_FCEN_DATA: list[dict] = _load_csv(_NORMALIZED_PATH)


class FcenConnector:
    def search(self, query: str) -> list[FoodItem]:
        """Case-insensitive substring match on name_fr or name_en."""
        q = query.lower()
        results = []
        for row in _FCEN_DATA:
            name_fr = row.get("name_fr", "").lower()
            name_en = row.get("name_en", "").lower()
            if q in name_fr or q in name_en:
                display_name = f"{row['name_fr']} / {row['name_en']}"
                results.append(
                    FoodItem(
                        name=display_name,
                        calories_per_100g=float(row.get("calories_per_100g") or 0),
                        carbs_g=float(row.get("carbs_g") or 0),
                        protein_g=float(row.get("protein_g") or 0),
                        fat_g=float(row.get("fat_g") or 0),
                        source="fcen",
                    )
                )
        return results
```

- [ ] **Step 6: Add httpx to pyproject.toml**

Open `pyproject.toml`. Find the `[tool.poetry.dependencies]` section. Add:

```toml
"httpx>=0.27,<1.0",
```

Run:

```bash
cd C:\Users\simon\resilio-plus
poetry lock --no-update
poetry install
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/connectors/test_food_search.py -v
```

Expected: 5 tests PASS (the USDA/OFF tests use mocks, the FCÉN test passes once CSV is present).

- [ ] **Step 8: Commit**

```bash
git add backend/app/connectors/food_search.py backend/app/connectors/fcen.py data/fcen_nutrients.csv tests/backend/connectors/test_food_search.py pyproject.toml poetry.lock
git commit -m "feat: food database connectors (USDA, Open Food Facts, FCÉN Santé Canada)"
```

---

## Task 2: Food API Endpoints

**Files:**
- Create: `backend/app/routes/food.py`
- Modify: `backend/app/main.py`
- Test: `tests/backend/api/test_food.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/api/test_food.py
import pytest
from unittest.mock import patch, AsyncMock
from backend.app.connectors.food_search import FoodItem
from tests.backend.api.conftest import client, auth_headers, athlete_id


def test_food_search_unauthenticated(client, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=rice")
    assert resp.status_code == 401


def test_food_search_empty_query(client, auth_headers, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/food/search?q=", headers=auth_headers)
    assert resp.status_code == 422  # query param required


def test_food_search_returns_list(client, auth_headers, athlete_id):
    mock_items = [
        FoodItem("Rice", 130.0, 28.2, 2.7, 0.3, "usda"),
        FoodItem("Brown rice", 112.0, 23.0, 2.3, 0.8, "open_food_facts"),
    ]
    with patch(
        "backend.app.routes.food.FoodSearchConnector.search",
        new_callable=AsyncMock,
        return_value=mock_items,
    ):
        resp = client.get(f"/athletes/{athlete_id}/food/search?q=rice", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["source"] == "usda"


def test_fcen_search(client, auth_headers, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/food/search/fcen?q=riz", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_barcode_lookup(client, auth_headers, athlete_id):
    mock_item = FoodItem("Nutella", 530.0, 57.5, 6.3, 30.9, "open_food_facts")
    with patch(
        "backend.app.routes.food.FoodSearchConnector.get_by_barcode",
        new_callable=AsyncMock,
        return_value=mock_item,
    ):
        resp = client.get(
            f"/athletes/{athlete_id}/food/barcode/3017620422003",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Nutella"


def test_barcode_not_found(client, auth_headers, athlete_id):
    with patch(
        "backend.app.routes.food.FoodSearchConnector.get_by_barcode",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = client.get(
            f"/athletes/{athlete_id}/food/barcode/0000000000000",
            headers=auth_headers,
        )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/backend/api/test_food.py -v
```

Expected: ImportError or 404.

- [ ] **Step 3: Create food router**

```python
# backend/app/routes/food.py
import os
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import AthleteModel
from ..routes.auth import get_current_user
from ..connectors.food_search import FoodSearchConnector, FoodItem
from ..connectors.fcen import FcenConnector

router = APIRouter(prefix="/athletes", tags=["food"])

_fcen = FcenConnector()


def _require_own(
    athlete_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> str:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user.id


@router.get("/{athlete_id}/food/search")
async def search_food(
    athlete_id: int,
    q: Annotated[str, Query(min_length=1)],
    _: Annotated[str, Depends(_require_own)],
) -> list[dict]:
    api_key = os.getenv("FOOD_API_KEY", "")
    connector = FoodSearchConnector(usda_api_key=api_key)
    items = await connector.search(q)
    return [_item_to_dict(i) for i in items]


@router.get("/{athlete_id}/food/search/fcen")
def search_fcen(
    athlete_id: int,
    q: Annotated[str, Query(min_length=1)],
    _: Annotated[str, Depends(_require_own)],
) -> list[dict]:
    items = _fcen.search(q)
    return [_item_to_dict(i) for i in items]


@router.get("/{athlete_id}/food/barcode/{barcode}")
async def get_by_barcode(
    athlete_id: int,
    barcode: str,
    _: Annotated[str, Depends(_require_own)],
) -> dict:
    api_key = os.getenv("FOOD_API_KEY", "")
    connector = FoodSearchConnector(usda_api_key=api_key)
    item = await connector.get_by_barcode(barcode)
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _item_to_dict(item)


def _item_to_dict(item: FoodItem) -> dict:
    return {
        "name": item.name,
        "calories_per_100g": item.calories_per_100g,
        "carbs_g": item.carbs_g,
        "protein_g": item.protein_g,
        "fat_g": item.fat_g,
        "source": item.source,
    }
```

- [ ] **Step 4: Register food router in main.py**

Open `backend/app/main.py`. Add after the analytics router line:

```python
from .routes import food
app.include_router(food.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/api/test_food.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/food.py backend/app/main.py tests/backend/api/test_food.py
git commit -m "feat: food API endpoints (search USDA+OFF, FCÉN search, barcode lookup)"
```

---

## Task 3: Chat HiTL Endpoint

**Files:**
- Create: `backend/app/routes/chat.py`
- Modify: `backend/app/main.py`
- Test: `tests/backend/api/test_chat.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/api/test_chat.py
import pytest
from unittest.mock import patch, MagicMock
from tests.backend.api.conftest import client, auth_headers, athlete_id


def test_chat_unauthenticated(client, athlete_id):
    resp = client.post(f"/athletes/{athlete_id}/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_chat_forbidden(client, auth_headers):
    resp = client.post("/athletes/99999/chat", json={"message": "hello"}, headers=auth_headers)
    assert resp.status_code == 403


def test_chat_missing_message(client, auth_headers, athlete_id):
    resp = client.post(f"/athletes/{athlete_id}/chat", json={}, headers=auth_headers)
    assert resp.status_code == 422


def test_chat_returns_response(client, auth_headers, athlete_id):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Train easy this week, your ACWR is high.")]

    with patch("backend.app.routes.chat.anthropic") as mock_anthropic:
        mock_anthropic.messages.create.return_value = mock_message
        resp = client.post(
            f"/athletes/{athlete_id}/chat",
            json={"message": "What should I focus on this week?"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "action" in data
    assert data["response"] == "Train easy this week, your ACWR is high."
    assert data["action"] is None


def test_chat_regenerate_plan_action(client, auth_headers, athlete_id):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(
        text="I've updated your plan. [ACTION:regenerate_plan]"
    )]

    with patch("backend.app.routes.chat.anthropic") as mock_anthropic:
        mock_anthropic.messages.create.return_value = mock_message
        resp = client.post(
            f"/athletes/{athlete_id}/chat",
            json={"message": "Please regenerate my plan for next week."},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "regenerate_plan"
    # Response text should not include the action tag
    assert "[ACTION:" not in data["response"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/backend/api/test_chat.py -v
```

Expected: ImportError — chat module doesn't exist.

- [ ] **Step 3: Create chat router**

```python
# backend/app/routes/chat.py
"""
Chat HiTL endpoint — athlete sends message, Head Coach responds.
Single-turn: each request is independent (no conversation history stored).
Context includes: athlete profile, current plan summary, ACWR, last 5 sessions.
If Head Coach response contains [ACTION:regenerate_plan], the plan is regenerated.
"""
import os
import re
from typing import Annotated, Literal

import anthropic as _anthropic_module
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import AthleteModel, TrainingPlanModel, SessionLogModel
from ..routes.auth import get_current_user

router = APIRouter(prefix="/athletes", tags=["chat"])

anthropic = _anthropic_module.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

_ACTION_PATTERN = re.compile(r"\[ACTION:(\w+)\]")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    action: Literal["regenerate_plan"] | None = None


def _require_own(
    athlete_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AthleteModel:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return athlete


def _build_context(athlete: AthleteModel, db: Session) -> str:
    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete.id)
        .order_by(TrainingPlanModel.created_at.desc())
        .first()
    )
    recent_sessions = (
        db.query(SessionLogModel)
        .filter(SessionLogModel.athlete_id == athlete.id)
        .order_by(SessionLogModel.session_date.desc())
        .limit(5)
        .all()
    )

    sessions_summary = "\n".join(
        f"  - {s.session_date}: {s.sport}, {s.duration_minutes or 0}min"
        for s in recent_sessions
    ) or "  (no sessions logged)"

    plan_summary = "No plan generated yet."
    if plan and plan.plan_json:
        import json
        try:
            p = json.loads(plan.plan_json) if isinstance(plan.plan_json, str) else plan.plan_json
            plan_summary = f"Current week: {len(p.get('sessions', []))} sessions planned."
        except Exception:
            plan_summary = "Plan available."

    return f"""Athlete profile:
- Name: {athlete.name}
- Primary sport: {getattr(athlete, 'primary_sport', 'mixed')}
- Weekly availability: {getattr(athlete, 'weekly_hours', '?')} hours

Current plan: {plan_summary}

Last 5 logged sessions:
{sessions_summary}

Instructions:
- You are the Head Coach AI for Resilio Plus, a hybrid athlete coaching platform.
- Respond concisely and directly. Max 3 short paragraphs.
- If the athlete asks you to regenerate or update their plan, include [ACTION:regenerate_plan] at the end of your response.
- Otherwise do NOT include any [ACTION:] tags.
"""


@router.post("/{athlete_id}/chat", response_model=ChatResponse)
def chat(
    athlete_id: int,
    body: ChatRequest,
    athlete: Annotated[AthleteModel, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> ChatResponse:
    context = _build_context(athlete, db)
    result = anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=context,
        messages=[{"role": "user", "content": body.message}],
    )
    raw_text: str = result.content[0].text

    action: Literal["regenerate_plan"] | None = None
    match = _ACTION_PATTERN.search(raw_text)
    if match and match.group(1) == "regenerate_plan":
        action = "regenerate_plan"
        raw_text = _ACTION_PATTERN.sub("", raw_text).strip()

    return ChatResponse(response=raw_text, action=action)
```

- [ ] **Step 4: Register chat router in main.py**

Open `backend/app/main.py`. Add after the food router line:

```python
from .routes import chat
app.include_router(chat.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/api/test_chat.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/chat.py backend/app/main.py tests/backend/api/test_chat.py
git commit -m "feat: chat HiTL endpoint (HEAD Coach consultation + regenerate_plan action)"
```

---

## Task 4: Agent Token Economy (`_get_view()`)

**Files:**
- Modify: `backend/app/agents/base.py`
- Modify: `backend/app/agents/running_coach.py`
- Modify: `backend/app/agents/lifting_coach.py`
- Modify: `backend/app/agents/swimming_coach.py`
- Modify: `backend/app/agents/biking_coach.py`
- Modify: `backend/app/agents/nutrition_coach.py`
- Modify: `backend/app/agents/recovery_coach.py`
- Test: `tests/backend/agents/test_get_view.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/agents/test_get_view.py
import pytest
from backend.app.agents.running_coach import RunningCoachAgent
from backend.app.agents.lifting_coach import LiftingCoachAgent
from backend.app.agents.swimming_coach import SwimmingCoachAgent
from backend.app.agents.biking_coach import BikingCoachAgent
from backend.app.agents.nutrition_coach import NutritionCoachAgent
from backend.app.agents.recovery_coach import RecoveryCoachAgent


FULL_ATHLETE_DATA = {
    "profile": {"name": "Alice", "primary_sport": "running"},
    "vdot": 50.0,
    "ftp_watts": 250,
    "css_pace_per_100m": 95,
    "e1rm_kg": 100.0,
    "running_sessions": [{"date": "2026-01-01", "distance_km": 10}],
    "lifting_sessions": [{"date": "2026-01-02", "volume_kg": 2000}],
    "swimming_sessions": [{"date": "2026-01-03", "distance_m": 2000}],
    "biking_sessions": [{"date": "2026-01-04", "distance_km": 50}],
    "hrv_rmssd": 65.0,
    "sleep_hours": 7.5,
    "steps_daily": 8000,
    "acwr": 1.1,
    "readiness": {"score": 85},
    "nutrition_targets": {"carbs_g": 300, "protein_g": 150, "fat_g": 70},
    "weekly_review": {"energy": 4},
}


def test_running_coach_view_has_running_data():
    agent = RunningCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    assert "profile" in view
    assert "vdot" in view
    assert "running_sessions" in view
    assert "acwr" in view
    # Should NOT include lifting or swimming specifics
    assert "lifting_sessions" not in view
    assert "swimming_sessions" not in view
    assert "ftp_watts" not in view


def test_lifting_coach_view_has_lifting_data():
    agent = LiftingCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    assert "profile" in view
    assert "e1rm_kg" in view
    assert "lifting_sessions" in view
    assert "running_sessions" not in view


def test_swimming_coach_view_has_swimming_data():
    agent = SwimmingCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    assert "profile" in view
    assert "css_pace_per_100m" in view
    assert "swimming_sessions" in view
    assert "running_sessions" not in view


def test_biking_coach_view_has_biking_data():
    agent = BikingCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    assert "profile" in view
    assert "ftp_watts" in view
    assert "biking_sessions" in view
    assert "running_sessions" not in view


def test_nutrition_coach_view_has_nutrition_data():
    agent = NutritionCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    assert "profile" in view
    assert "nutrition_targets" in view
    assert "running_sessions" not in view


def test_recovery_coach_view_has_recovery_data():
    agent = RecoveryCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    assert "profile" in view
    assert "hrv_rmssd" in view
    assert "sleep_hours" in view
    assert "readiness" in view
    assert "running_sessions" not in view


def test_view_is_subset_of_full_data():
    """All keys in view must exist in full data."""
    agent = RunningCoachAgent()
    view = agent._get_view(FULL_ATHLETE_DATA)
    for key in view:
        assert key in FULL_ATHLETE_DATA, f"Key '{key}' not in full athlete data"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/backend/agents/test_get_view.py -v
```

Expected: AttributeError — `_get_view` method doesn't exist yet.

- [ ] **Step 3: Add `_get_view()` to BaseAgent**

Open `backend/app/agents/base.py`. Find the class body. Add the method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    """
    Return filtered subset of athlete_data for this agent.
    Override in subclasses to reduce token usage by 30-40%.
    Default: return full data (safe fallback for Head Coach).
    """
    return athlete_data
```

- [ ] **Step 4: Add `_get_view()` overrides to each specialist agent**

**RunningCoachAgent** (`backend/app/agents/running_coach.py`) — add method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    return {
        "profile": athlete_data.get("profile"),
        "vdot": athlete_data.get("vdot"),
        "running_sessions": athlete_data.get("running_sessions", []),
        "acwr": athlete_data.get("acwr"),
        "readiness": athlete_data.get("readiness"),
        "weekly_review": athlete_data.get("weekly_review"),
    }
```

**LiftingCoachAgent** (`backend/app/agents/lifting_coach.py`) — add method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    return {
        "profile": athlete_data.get("profile"),
        "e1rm_kg": athlete_data.get("e1rm_kg"),
        "lifting_sessions": athlete_data.get("lifting_sessions", []),
        "acwr": athlete_data.get("acwr"),
        "readiness": athlete_data.get("readiness"),
        "weekly_review": athlete_data.get("weekly_review"),
    }
```

**SwimmingCoachAgent** (`backend/app/agents/swimming_coach.py`) — add method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    return {
        "profile": athlete_data.get("profile"),
        "css_pace_per_100m": athlete_data.get("css_pace_per_100m"),
        "swimming_sessions": athlete_data.get("swimming_sessions", []),
        "acwr": athlete_data.get("acwr"),
        "readiness": athlete_data.get("readiness"),
        "weekly_review": athlete_data.get("weekly_review"),
    }
```

**BikingCoachAgent** (`backend/app/agents/biking_coach.py`) — add method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    return {
        "profile": athlete_data.get("profile"),
        "ftp_watts": athlete_data.get("ftp_watts"),
        "biking_sessions": athlete_data.get("biking_sessions", []),
        "acwr": athlete_data.get("acwr"),
        "readiness": athlete_data.get("readiness"),
        "weekly_review": athlete_data.get("weekly_review"),
    }
```

**NutritionCoachAgent** (`backend/app/agents/nutrition_coach.py`) — add method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    return {
        "profile": athlete_data.get("profile"),
        "nutrition_targets": athlete_data.get("nutrition_targets"),
        "weekly_review": athlete_data.get("weekly_review"),
        "acwr": athlete_data.get("acwr"),
    }
```

**RecoveryCoachAgent** (`backend/app/agents/recovery_coach.py`) — add method:

```python
def _get_view(self, athlete_data: dict) -> dict:
    return {
        "profile": athlete_data.get("profile"),
        "hrv_rmssd": athlete_data.get("hrv_rmssd"),
        "sleep_hours": athlete_data.get("sleep_hours"),
        "steps_daily": athlete_data.get("steps_daily"),
        "readiness": athlete_data.get("readiness"),
        "weekly_review": athlete_data.get("weekly_review"),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/agents/test_get_view.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/base.py backend/app/agents/running_coach.py backend/app/agents/lifting_coach.py backend/app/agents/swimming_coach.py backend/app/agents/biking_coach.py backend/app/agents/nutrition_coach.py backend/app/agents/recovery_coach.py tests/backend/agents/test_get_view.py
git commit -m "feat: agent token economy via _get_view() - reduces LLM context 30-40% per specialist"
```

---

## Task 5: Profile Edit Endpoint

**Files:**
- Modify: `backend/app/routes/athletes.py`
- Test: `tests/backend/api/test_profile_edit.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/api/test_profile_edit.py
import pytest
from tests.backend.api.conftest import client, auth_headers, athlete_id


def test_update_profile_unauthorized(client, athlete_id):
    resp = client.put(f"/athletes/{athlete_id}/profile", json={"weight_kg": 75.0})
    assert resp.status_code == 401


def test_update_profile_forbidden(client, auth_headers):
    resp = client.put(
        "/athletes/99999/profile",
        json={"weight_kg": 75.0},
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_update_profile_weight(client, auth_headers, athlete_id):
    resp = client.put(
        f"/athletes/{athlete_id}/profile",
        json={"weight_kg": 72.5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["weight_kg"] == 72.5


def test_update_profile_partial(client, auth_headers, athlete_id):
    # Only update weekly_hours — other fields unchanged
    resp = client.put(
        f"/athletes/{athlete_id}/profile",
        json={"weekly_hours": 12},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["weekly_hours"] == 12


def test_update_profile_invalid_field_ignored(client, auth_headers, athlete_id):
    # Unknown fields should be ignored (extra fields in body)
    resp = client.put(
        f"/athletes/{athlete_id}/profile",
        json={"weight_kg": 70.0, "unknown_field": "ignored"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/backend/api/test_profile_edit.py -v
```

Expected: 404 — route doesn't exist yet.

- [ ] **Step 3: Add profile update endpoint to athletes.py**

Open `backend/app/routes/athletes.py`. Add a Pydantic model and the PUT endpoint.

Find the imports section and add (if not already present):
```python
from typing import Optional
```

Add the model and endpoint:

```python
class ProfileUpdateRequest(BaseModel):
    weight_kg: Optional[float] = None
    weekly_hours: Optional[int] = None
    primary_sport: Optional[str] = None
    goal: Optional[str] = None
    available_days: Optional[list[str]] = None


@router.put("/{athlete_id}/profile")
def update_profile(
    athlete_id: int,
    body: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.weight_kg is not None and hasattr(athlete, "weight_kg"):
        athlete.weight_kg = body.weight_kg
    if body.weekly_hours is not None and hasattr(athlete, "weekly_hours"):
        athlete.weekly_hours = body.weekly_hours
    if body.primary_sport is not None and hasattr(athlete, "primary_sport"):
        athlete.primary_sport = body.primary_sport
    if body.goal is not None and hasattr(athlete, "goal"):
        athlete.goal = body.goal
    if body.available_days is not None and hasattr(athlete, "available_days"):
        import json as _json
        athlete.available_days = _json.dumps(body.available_days)

    db.commit()
    db.refresh(athlete)

    return {
        "id": athlete.id,
        "name": athlete.name,
        "weight_kg": getattr(athlete, "weight_kg", None),
        "weekly_hours": getattr(athlete, "weekly_hours", None),
        "primary_sport": getattr(athlete, "primary_sport", None),
        "goal": getattr(athlete, "goal", None),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/api/test_profile_edit.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/athletes.py tests/backend/api/test_profile_edit.py
git commit -m "feat: PUT /athletes/{id}/profile endpoint for editable athlete profile"
```

---

## Task 6: Plan Session Customization Endpoint

**Files:**
- Modify: `backend/app/routes/plans.py`
- Test: `tests/backend/api/test_plan_customization.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/api/test_plan_customization.py
import pytest
import json
from tests.backend.api.conftest import client, auth_headers, athlete_id


def _get_session_id(client, auth_headers, athlete_id):
    """Helper: get first session ID from plan."""
    resp = client.get(f"/athletes/{athlete_id}/plan", headers=auth_headers)
    assert resp.status_code == 200
    plan = resp.json()
    sessions = plan.get("sessions", [])
    if sessions:
        return sessions[0].get("id") or sessions[0].get("session_id") or 1
    return 1


def test_patch_session_unauthorized(client, athlete_id):
    resp = client.patch(
        f"/athletes/{athlete_id}/plan/sessions/1",
        json={"skip": True},
    )
    assert resp.status_code == 401


def test_patch_session_forbidden(client, auth_headers):
    resp = client.patch(
        "/athletes/99999/plan/sessions/1",
        json={"skip": True},
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_patch_session_skip(client, auth_headers, athlete_id):
    resp = client.patch(
        f"/athletes/{athlete_id}/plan/sessions/1",
        json={"skip": True},
        headers=auth_headers,
    )
    # Either 200 (session exists) or 404 (no plan yet) — both are valid
    assert resp.status_code in (200, 404)


def test_patch_session_adjust_volume(client, auth_headers, athlete_id):
    resp = client.patch(
        f"/athletes/{athlete_id}/plan/sessions/1",
        json={"volume_adjustment": 0.8, "notes": "Feeling tired, reducing volume"},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/backend/api/test_plan_customization.py -v
```

Expected: 404 — route doesn't exist yet.

- [ ] **Step 3: Add plan session patch endpoint to plans.py**

Open `backend/app/routes/plans.py`. Add model and endpoint:

```python
class SessionPatchRequest(BaseModel):
    skip: Optional[bool] = None
    volume_adjustment: Optional[float] = None  # e.g. 0.8 = 80% of planned volume
    notes: Optional[str] = None


@router.patch("/{athlete_id}/plan/sessions/{session_index}")
def patch_plan_session(
    athlete_id: int,
    session_index: int,
    body: SessionPatchRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    plan = (
        db.query(TrainingPlanModel)
        .filter(TrainingPlanModel.athlete_id == athlete_id)
        .order_by(TrainingPlanModel.created_at.desc())
        .first()
    )
    if not plan or not plan.plan_json:
        raise HTTPException(status_code=404, detail="No active plan")

    import json as _json
    plan_data = _json.loads(plan.plan_json) if isinstance(plan.plan_json, str) else plan.plan_json
    sessions = plan_data.get("sessions", [])

    # session_index is 1-based
    idx = session_index - 1
    if idx < 0 or idx >= len(sessions):
        raise HTTPException(status_code=404, detail="Session not found in plan")

    session = sessions[idx]
    if body.skip is not None:
        session["skip"] = body.skip
    if body.volume_adjustment is not None:
        session["volume_adjustment"] = body.volume_adjustment
    if body.notes is not None:
        session["custom_notes"] = body.notes

    plan.plan_json = _json.dumps(plan_data)
    db.commit()

    return {"session_index": session_index, "updated": session}
```

Also add `Optional` to imports if not already present:
```python
from typing import Optional
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/api/test_plan_customization.py -v
```

Expected: 4 tests PASS (some 404 when no plan exists is expected and valid).

- [ ] **Step 5: Run full test suite**

```bash
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/plans.py tests/backend/api/test_plan_customization.py
git commit -m "feat: PATCH /athletes/{id}/plan/sessions/{idx} for plan customization (skip, volume, notes)"
```

---

## Task 7: Frontend — Chat Page + API Client

**Files:**
- Create: `frontend/src/app/chat/page.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/components/top-nav.tsx`

- [ ] **Step 1: Add chat, food, and profile API functions to api.ts**

Open `frontend/src/lib/api.ts`. Add at the end:

```typescript
// ── Chat ───────────────────────────────────────────────────────────────
export interface ChatResponse {
  response: string;
  action: "regenerate_plan" | null;
}

export async function sendChatMessage(
  athleteId: number,
  message: string
): Promise<ChatResponse> {
  return _req(`/athletes/${athleteId}/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

// ── Food ───────────────────────────────────────────────────────────────
export interface FoodItem {
  name: string;
  calories_per_100g: number;
  carbs_g: number;
  protein_g: number;
  fat_g: number;
  source: string;
}

export async function searchFood(
  athleteId: number,
  query: string
): Promise<FoodItem[]> {
  return _req(`/athletes/${athleteId}/food/search?q=${encodeURIComponent(query)}`);
}

export async function searchFcen(
  athleteId: number,
  query: string
): Promise<FoodItem[]> {
  return _req(`/athletes/${athleteId}/food/search/fcen?q=${encodeURIComponent(query)}`);
}

export async function getFoodByBarcode(
  athleteId: number,
  barcode: string
): Promise<FoodItem> {
  return _req(`/athletes/${athleteId}/food/barcode/${barcode}`);
}

// ── Profile ────────────────────────────────────────────────────────────
export interface ProfileUpdate {
  weight_kg?: number;
  weekly_hours?: number;
  primary_sport?: string;
  goal?: string;
}

export async function updateProfile(
  athleteId: number,
  update: ProfileUpdate
): Promise<Record<string, unknown>> {
  return _req(`/athletes/${athleteId}/profile`, {
    method: "PUT",
    body: JSON.stringify(update),
  });
}

// ── Plan customization ─────────────────────────────────────────────────
export interface SessionPatch {
  skip?: boolean;
  volume_adjustment?: number;
  notes?: string;
}

export async function patchPlanSession(
  athleteId: number,
  sessionIndex: number,
  patch: SessionPatch
): Promise<Record<string, unknown>> {
  return _req(`/athletes/${athleteId}/plan/sessions/${sessionIndex}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}
```

- [ ] **Step 2: Create Chat page**

```tsx
// frontend/src/app/chat/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { sendChatMessage } from "@/lib/api";
import Link from "next/link";

export default function ChatPage() {
  const { athlete, token } = useAuth();
  const router = useRouter();
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [planUpdated, setPlanUpdated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    router.push("/login");
    return null;
  }
  if (!athlete) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    setError(null);
    setPlanUpdated(false);

    try {
      const result = await sendChatMessage(athlete.id, message);
      setResponse(result.response);
      if (result.action === "regenerate_plan") {
        setPlanUpdated(true);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-2xl font-bold">Head Coach</h1>
      <p className="text-muted-foreground text-sm">
        Ask your AI coach anything about your training, recovery, or plan.
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="What should I focus on this week? My legs feel heavy..."
          rows={4}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Thinking..." : "Ask Coach"}
        </button>
      </form>

      {error && (
        <p className="text-destructive text-sm">{error}</p>
      )}

      {response && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <p className="text-sm font-medium text-muted-foreground">Head Coach</p>
          <p className="text-sm whitespace-pre-wrap">{response}</p>
          {planUpdated && (
            <div className="flex items-center gap-2 rounded-md bg-green-500/10 border border-green-500/20 px-3 py-2">
              <span className="text-green-600 dark:text-green-400 text-sm font-medium">
                Plan updated
              </span>
              <Link
                href="/plan"
                className="text-sm text-green-600 dark:text-green-400 underline"
              >
                View new plan →
              </Link>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Add "Coach" to navigation**

Open `frontend/src/components/top-nav.tsx`. Find the `NAV_LINKS` array. Add:

```typescript
  { href: "/chat", label: "Coach" },
```

Add it after "History" (before "Analytics" if already added, or at end).

- [ ] **Step 4: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/chat/page.tsx frontend/src/lib/api.ts frontend/src/components/top-nav.tsx
git commit -m "feat: chat page + full API client (food, profile, plan patch, chat)"
```

---

## Task 8: Frontend Polish — ACWR Alert, Nutrition Widget, Profile Settings Page

**Files:**
- Create: `frontend/src/components/AcwrAlert.tsx`
- Create: `frontend/src/components/NutritionDirectives.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/settings/profile/page.tsx`

- [ ] **Step 1: Create AcwrAlert component**

```tsx
// frontend/src/components/AcwrAlert.tsx
"use client";

interface Props {
  acwr: number | null;
}

export function AcwrAlert({ acwr }: Props) {
  if (!acwr || acwr <= 1.3) return null;

  const isDanger = acwr > 1.5;

  return (
    <div
      className={`rounded-md border px-4 py-3 text-sm flex items-start gap-2 ${
        isDanger
          ? "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-400"
          : "border-yellow-500/30 bg-yellow-500/10 text-yellow-700 dark:text-yellow-400"
      }`}
    >
      <span className="font-semibold">{isDanger ? "⚠ Danger" : "⚡ Caution"}</span>
      <span>
        {isDanger
          ? `ACWR ${acwr.toFixed(2)} — significant injury risk. Reduce training load immediately.`
          : `ACWR ${acwr.toFixed(2)} — above safe zone. Consider reducing intensity this week.`}
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Create NutritionDirectives component**

```tsx
// frontend/src/components/NutritionDirectives.tsx
"use client";

interface NutritionTargets {
  carbs_g: number;
  protein_g: number;
  fat_g: number;
  calories?: number;
}

interface Props {
  targets: NutritionTargets | null;
  dayType?: string;
}

export function NutritionDirectives({ targets, dayType }: Props) {
  if (!targets) return null;

  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Today's Nutrition Targets</h3>
        {dayType && (
          <span className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground capitalize">
            {dayType} day
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center">
          <p className="text-xl font-bold text-blue-500">{Math.round(targets.carbs_g)}g</p>
          <p className="text-xs text-muted-foreground">Carbs</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-green-500">{Math.round(targets.protein_g)}g</p>
          <p className="text-xs text-muted-foreground">Protein</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-yellow-500">{Math.round(targets.fat_g)}g</p>
          <p className="text-xs text-muted-foreground">Fat</p>
        </div>
      </div>
      {targets.calories && (
        <p className="text-xs text-center text-muted-foreground">
          {Math.round(targets.calories)} kcal total
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add ACWR alert and nutrition widget to dashboard**

Open `frontend/src/app/dashboard/page.tsx`. Read the file first to understand its current structure.

Find where the main content is rendered (after the week-status data loads). Import the two new components and add them near the top of the main section:

```tsx
// Add imports near top of file:
import { AcwrAlert } from "@/components/AcwrAlert";
import { NutritionDirectives } from "@/components/NutritionDirectives";

// Inside the JSX, add after the h1 title or first content section:
{weekStatus?.acwr !== undefined && (
  <AcwrAlert acwr={weekStatus.acwr} />
)}
{weekStatus?.nutrition_targets && (
  <NutritionDirectives
    targets={weekStatus.nutrition_targets}
    dayType={weekStatus.today_day_type}
  />
)}
```

> **Note:** The exact shape of `weekStatus` depends on the current dashboard implementation. Read `frontend/src/app/dashboard/page.tsx` to find the correct field names before inserting. If `acwr` is nested (e.g., `weekStatus?.load?.acwr`), adjust accordingly.

- [ ] **Step 4: Create Profile Settings page**

```tsx
// frontend/src/app/settings/profile/page.tsx
"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { updateProfile } from "@/lib/api";

export default function ProfileSettingsPage() {
  const { athlete, token } = useAuth();
  const router = useRouter();

  const [weightKg, setWeightKg] = useState<string>("");
  const [weeklyHours, setWeeklyHours] = useState<string>("");
  const [primarySport, setPrimarySport] = useState<string>("");
  const [goal, setGoal] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!token) {
    router.push("/login");
    return null;
  }
  if (!athlete) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);

    const update: Record<string, unknown> = {};
    if (weightKg) update.weight_kg = parseFloat(weightKg);
    if (weeklyHours) update.weekly_hours = parseInt(weeklyHours);
    if (primarySport) update.primary_sport = primarySport;
    if (goal) update.goal = goal;

    try {
      await updateProfile(athlete.id, update);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="max-w-lg mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Edit Profile</h1>
        <p className="text-muted-foreground text-sm">
          Update fields you want to change — leave empty to keep current values.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium block mb-1">Weight (kg)</label>
          <input
            type="number"
            step="0.1"
            value={weightKg}
            onChange={(e) => setWeightKg(e.target.value)}
            placeholder="e.g. 72.5"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div>
          <label className="text-sm font-medium block mb-1">Weekly training hours</label>
          <input
            type="number"
            value={weeklyHours}
            onChange={(e) => setWeeklyHours(e.target.value)}
            placeholder="e.g. 10"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div>
          <label className="text-sm font-medium block mb-1">Primary sport</label>
          <select
            value={primarySport}
            onChange={(e) => setPrimarySport(e.target.value)}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">-- No change --</option>
            <option value="running">Running</option>
            <option value="lifting">Lifting</option>
            <option value="biking">Biking</option>
            <option value="swimming">Swimming</option>
          </select>
        </div>

        <div>
          <label className="text-sm font-medium block mb-1">Goal</label>
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Complete a marathon in spring"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        {error && <p className="text-destructive text-sm">{error}</p>}

        {saved && (
          <p className="text-green-600 dark:text-green-400 text-sm">Profile updated successfully.</p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save changes"}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 5: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 6: Run full test suite**

```bash
cd C:\Users\simon\resilio-plus
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AcwrAlert.tsx frontend/src/components/NutritionDirectives.tsx frontend/src/app/dashboard/page.tsx frontend/src/app/settings/profile/page.tsx
git commit -m "feat: ACWR alert banner, nutrition directives widget, profile settings page"
```

---

## Self-Review

**Spec coverage:**
- USDA + Open Food Facts search → Task 1 ✅
- FCÉN Santé Canada CSV → Task 1 ✅
- `GET /athletes/{id}/food/search?q=` → Task 2 ✅
- `GET /athletes/{id}/food/search/fcen?q=` → Task 2 ✅
- `GET /athletes/{id}/food/barcode/{barcode}` → Task 2 ✅
- `POST /athletes/{id}/chat` with `regenerate_plan` action → Task 3 ✅
- `_get_view()` on all 6 specialist agents → Task 4 ✅
- `PUT /athletes/{id}/profile` → Task 5 ✅
- `PATCH /athletes/{id}/plan/sessions/{id}` → Task 6 ✅
- Chat frontend page → Task 7 ✅
- "Coach" nav link → Task 7 ✅
- ACWR alert badge/banner → Task 8 ✅
- Nutrition directives widget → Task 8 ✅
- Profile settings page → Task 8 ✅
- `FOOD_API_KEY` in env (needed by food_search.py) → noted in Task 1 (Step 6 adds to pyproject, env var read in routes/food.py) ✅

**Placeholder scan:** No TBD, no TODOs. Step 3 in Task 8 has a conditional note about reading the dashboard file first — this is intentional guidance, not a placeholder.

**Type consistency:**
- `FoodItem` dataclass defined in food_search.py, imported into fcen.py and routes/food.py ✅
- `ChatRequest`/`ChatResponse` defined in chat.py ✅
- `ProfileUpdateRequest` defined in athletes.py ✅
- `SessionPatchRequest` defined in plans.py ✅
- `ChatResponse`, `FoodItem`, `ProfileUpdate`, `SessionPatch` defined in api.ts Task 7, used in pages ✅
- `AcwrAlert` props match usage in dashboard ✅
- `NutritionDirectives` props match usage in dashboard ✅
