# Phase 10 — Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an analytics dashboard with ACWR trend, CTL/ATL/TSB training load, sport breakdown, and performance progression charts.

**Architecture:** Three new backend endpoints aggregate historical `SessionLogModel` data into time-series analytics. Frontend `app/analytics/page.tsx` renders these with Recharts. Data is derived entirely from existing tables — no new DB models needed.

**Tech Stack:** Python (FastAPI), SQLAlchemy (sync), Recharts, Next.js, TypeScript, Tailwind CSS 4

---

## File Structure

**New files:**
- `backend/app/routes/analytics.py` — 3 GET endpoints: `/load`, `/sport-breakdown`, `/performance`
- `backend/app/core/analytics_logic.py` — Pure functions: ACWR from session logs, CTL/ATL/TSB, sport breakdown, VDOT/e1RM progression
- `frontend/src/app/analytics/page.tsx` — Analytics dashboard page
- `frontend/src/components/analytics/AcwrTrendChart.tsx` — ACWR on 8 weeks with danger zones
- `frontend/src/components/analytics/TrainingLoadChart.tsx` — CTL/ATL/TSB line chart
- `frontend/src/components/analytics/SportBreakdownChart.tsx` — Pie/bar chart hours per sport
- `frontend/src/components/analytics/PerformanceTrendChart.tsx` — VDOT and e1RM over time

**Modified files:**
- `backend/app/main.py` — Register analytics router
- `frontend/src/lib/api.ts` — Add `getLoadAnalytics`, `getSportBreakdown`, `getPerformanceAnalytics`
- `frontend/src/components/top-nav.tsx` — Add "Analytics" link

---

## Task 1: Analytics Core Logic

**Files:**
- Create: `backend/app/core/analytics_logic.py`
- Test: `tests/backend/core/test_analytics_logic.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/core/test_analytics_logic.py
from datetime import date, timedelta
from backend.app.core.analytics_logic import (
    compute_acwr_series,
    compute_ctl_atl_tsb,
    compute_sport_breakdown,
    compute_performance_trends,
)


def make_day(offset: int, load: float, sport: str = "running") -> dict:
    return {
        "session_date": (date.today() - timedelta(days=offset)).isoformat(),
        "total_load": load,
        "sport": sport,
    }


def test_acwr_series_empty():
    result = compute_acwr_series([])
    assert result == []


def test_acwr_series_single_day():
    sessions = [make_day(0, 100.0)]
    result = compute_acwr_series(sessions)
    assert len(result) == 1
    entry = result[0]
    assert "date" in entry
    assert "acwr" in entry
    assert "acute" in entry
    assert "chronic" in entry
    # With a single day, chronic == acute
    assert entry["acwr"] == 1.0


def test_acwr_series_multiple_weeks():
    # 28 days of data at 100 load/day
    sessions = [make_day(i, 100.0) for i in range(27, -1, -1)]
    result = compute_acwr_series(sessions)
    assert len(result) == 28
    # Steady state: ACWR ≈ 1.0
    last = result[-1]
    assert 0.9 < last["acwr"] < 1.1


def test_acwr_series_spike():
    # 21 days at 100, then 7 days at 200
    sessions = [make_day(i, 100.0) for i in range(27, 6, -1)]
    sessions += [make_day(i, 200.0) for i in range(6, -1, -1)]
    result = compute_acwr_series(sessions)
    last = result[-1]
    # Acute load spiked, chronic still lower — ACWR > 1.0
    assert last["acwr"] > 1.0


def test_ctl_atl_tsb_empty():
    result = compute_ctl_atl_tsb([])
    assert result == []


def test_ctl_atl_tsb_values():
    sessions = [make_day(i, 100.0) for i in range(41, -1, -1)]
    result = compute_ctl_atl_tsb(sessions)
    assert len(result) == 42
    last = result[-1]
    assert "date" in last
    assert "ctl" in last
    assert "atl" in last
    assert "tsb" in last
    # TSB = CTL - ATL
    assert abs(last["tsb"] - (last["ctl"] - last["atl"])) < 0.01


def test_sport_breakdown_empty():
    result = compute_sport_breakdown([])
    assert result == {}


def test_sport_breakdown():
    sessions = [
        {"sport": "running", "duration_minutes": 60, "session_date": date.today().isoformat()},
        {"sport": "running", "duration_minutes": 30, "session_date": date.today().isoformat()},
        {"sport": "lifting", "duration_minutes": 45, "session_date": date.today().isoformat()},
    ]
    result = compute_sport_breakdown(sessions)
    assert result["running"] == 90
    assert result["lifting"] == 45


def test_performance_trends_empty():
    result = compute_performance_trends([])
    assert result["vdot"] == []
    assert result["e1rm"] == []


def test_performance_trends_vdot():
    sessions = [
        {"sport": "running", "session_date": "2026-01-01", "actual_data_json": '{"vdot": 45.0}'},
        {"sport": "running", "session_date": "2026-02-01", "actual_data_json": '{"vdot": 47.0}'},
    ]
    result = compute_performance_trends(sessions)
    assert len(result["vdot"]) == 2
    assert result["vdot"][0]["value"] == 45.0
    assert result["vdot"][1]["value"] == 47.0


def test_performance_trends_e1rm():
    sessions = [
        {"sport": "lifting", "session_date": "2026-01-01", "actual_data_json": '{"e1rm_kg": 100.0}'},
        {"sport": "lifting", "session_date": "2026-02-01", "actual_data_json": '{"e1rm_kg": 105.0}'},
    ]
    result = compute_performance_trends(sessions)
    assert len(result["e1rm"]) == 2
    assert result["e1rm"][0]["value"] == 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:\Users\simon\resilio-plus
poetry run pytest tests/backend/core/test_analytics_logic.py -v
```

Expected: ImportError — `analytics_logic` does not exist yet.

- [ ] **Step 3: Implement analytics_logic.py**

```python
# backend/app/core/analytics_logic.py
"""
Pure functions for computing analytics time-series.
Inputs: list of dicts (from SessionLogModel rows).
Outputs: list of dicts ready for JSON serialization.
"""
import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Any


def _load_by_date(sessions: list[dict]) -> dict[str, float]:
    """Aggregate total_load per ISO date string."""
    by_date: dict[str, float] = defaultdict(float)
    for s in sessions:
        d = s.get("session_date")
        if d:
            by_date[str(d)] += float(s.get("total_load") or 0.0)
    return dict(by_date)


def _date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def compute_acwr_series(sessions: list[dict]) -> list[dict[str, Any]]:
    """
    Compute ACWR (Acute:Chronic Workload Ratio) series using EWMA.
    Acute window: 7 days (λ = 2/8 = 0.25)
    Chronic window: 28 days (λ = 2/29 ≈ 0.069)
    Returns: list of {"date", "acwr", "acute", "chronic"} sorted ascending.
    """
    if not sessions:
        return []

    by_date = _load_by_date(sessions)
    dates = sorted(by_date.keys())
    start = date.fromisoformat(dates[0])
    end = date.fromisoformat(dates[-1])
    all_dates = _date_range(start, end)

    lambda_acute = 2 / (7 + 1)   # 0.25
    lambda_chronic = 2 / (28 + 1)  # ≈ 0.069

    ewma_acute = 0.0
    ewma_chronic = 0.0
    result = []

    for d in all_dates:
        load = by_date.get(d.isoformat(), 0.0)
        ewma_acute = lambda_acute * load + (1 - lambda_acute) * ewma_acute
        ewma_chronic = lambda_chronic * load + (1 - lambda_chronic) * ewma_chronic
        acwr = (ewma_acute / ewma_chronic) if ewma_chronic > 0 else 1.0
        result.append({
            "date": d.isoformat(),
            "acwr": round(acwr, 3),
            "acute": round(ewma_acute, 1),
            "chronic": round(ewma_chronic, 1),
        })

    return result


def compute_ctl_atl_tsb(sessions: list[dict]) -> list[dict[str, Any]]:
    """
    Compute CTL (Chronic Training Load), ATL (Acute Training Load), TSB (Training Stress Balance).
    CTL: 42-day EWMA (λ = 2/43)
    ATL: 7-day EWMA (λ = 2/8)
    TSB = CTL - ATL
    Returns: list of {"date", "ctl", "atl", "tsb"} sorted ascending.
    """
    if not sessions:
        return []

    by_date = _load_by_date(sessions)
    dates = sorted(by_date.keys())
    start = date.fromisoformat(dates[0])
    end = date.fromisoformat(dates[-1])
    all_dates = _date_range(start, end)

    lambda_ctl = 2 / (42 + 1)
    lambda_atl = 2 / (7 + 1)

    ctl = 0.0
    atl = 0.0
    result = []

    for d in all_dates:
        load = by_date.get(d.isoformat(), 0.0)
        ctl = lambda_ctl * load + (1 - lambda_ctl) * ctl
        atl = lambda_atl * load + (1 - lambda_atl) * atl
        tsb = ctl - atl
        result.append({
            "date": d.isoformat(),
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(tsb, 1),
        })

    return result


def compute_sport_breakdown(sessions: list[dict]) -> dict[str, int]:
    """
    Sum duration_minutes per sport.
    Returns: {"running": 180, "lifting": 90, ...}
    """
    totals: dict[str, int] = defaultdict(int)
    for s in sessions:
        sport = s.get("sport")
        mins = int(s.get("duration_minutes") or 0)
        if sport and mins:
            totals[sport] += mins
    return dict(totals)


def compute_performance_trends(sessions: list[dict]) -> dict[str, list[dict[str, Any]]]:
    """
    Extract VDOT (running) and e1RM (lifting) progression over time.
    Returns: {"vdot": [{"date", "value"}, ...], "e1rm": [{"date", "value"}, ...]}
    """
    vdot_series = []
    e1rm_series = []

    for s in sessions:
        sport = s.get("sport", "")
        d = s.get("session_date")
        raw_json = s.get("actual_data_json")
        if not (d and raw_json):
            continue
        try:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except (json.JSONDecodeError, TypeError):
            continue

        if sport == "running" and "vdot" in data:
            vdot_series.append({"date": str(d), "value": float(data["vdot"])})
        elif sport == "lifting" and "e1rm_kg" in data:
            e1rm_series.append({"date": str(d), "value": float(data["e1rm_kg"])})

    vdot_series.sort(key=lambda x: x["date"])
    e1rm_series.sort(key=lambda x: x["date"])

    return {"vdot": vdot_series, "e1rm": e1rm_series}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/core/test_analytics_logic.py -v
```

Expected: 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/analytics_logic.py tests/backend/core/test_analytics_logic.py
git commit -m "feat: analytics core logic (ACWR, CTL/ATL/TSB, sport breakdown, performance trends)"
```

---

## Task 2: Analytics API Endpoints

**Files:**
- Create: `backend/app/routes/analytics.py`
- Modify: `backend/app/main.py`
- Test: `tests/backend/api/test_analytics.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/backend/api/test_analytics.py
import pytest
from fastapi.testclient import TestClient
from tests.backend.api.conftest import client, auth_headers, athlete_id


def test_load_analytics_empty(client, auth_headers, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/analytics/load", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "acwr" in data
    assert "training_load" in data
    assert data["acwr"] == []
    assert data["training_load"] == []


def test_sport_breakdown_empty(client, auth_headers, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/analytics/sport-breakdown", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data == {}


def test_performance_analytics_empty(client, auth_headers, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/analytics/performance", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "vdot" in data
    assert "e1rm" in data
    assert data["vdot"] == []
    assert data["e1rm"] == []


def test_load_analytics_forbidden(client, auth_headers):
    resp = client.get("/athletes/99999/analytics/load", headers=auth_headers)
    assert resp.status_code == 403


def test_analytics_unauthenticated(client, athlete_id):
    resp = client.get(f"/athletes/{athlete_id}/analytics/load")
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/backend/api/test_analytics.py -v
```

Expected: ImportError or 404 — router not registered yet.

- [ ] **Step 3: Create analytics router**

```python
# backend/app/routes/analytics.py
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db.models import AthleteModel, SessionLogModel
from ..routes.auth import get_current_user
from ..core.analytics_logic import (
    compute_acwr_series,
    compute_ctl_atl_tsb,
    compute_sport_breakdown,
    compute_performance_trends,
)

router = APIRouter(prefix="/athletes", tags=["analytics"])


def _require_own(
    athlete_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> str:
    athlete = db.get(AthleteModel, athlete_id)
    if not athlete or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user.id


def _session_rows(athlete_id: int, db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(SessionLogModel)
        .filter(SessionLogModel.athlete_id == athlete_id)
        .all()
    )
    result = []
    for r in rows:
        result.append({
            "session_date": r.session_date,
            "sport": r.sport,
            "total_load": r.total_load,
            "duration_minutes": r.duration_minutes,
            "actual_data_json": r.actual_data_json,
        })
    return result


@router.get("/{athlete_id}/analytics/load")
def get_load_analytics(
    athlete_id: int,
    _: Annotated[str, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = _session_rows(athlete_id, db)
    return {
        "acwr": compute_acwr_series(rows),
        "training_load": compute_ctl_atl_tsb(rows),
    }


@router.get("/{athlete_id}/analytics/sport-breakdown")
def get_sport_breakdown(
    athlete_id: int,
    _: Annotated[str, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> dict[str, int]:
    rows = _session_rows(athlete_id, db)
    return compute_sport_breakdown(rows)


@router.get("/{athlete_id}/analytics/performance")
def get_performance_analytics(
    athlete_id: int,
    _: Annotated[str, Depends(_require_own)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = _session_rows(athlete_id, db)
    return compute_performance_trends(rows)
```

- [ ] **Step 4: Register router in main.py**

Open `backend/app/main.py`. Find the line that registers the last router (e.g., `app.include_router(connectors.router)`). Add after it:

```python
from .routes import analytics
app.include_router(analytics.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/backend/api/test_analytics.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 6: Run full test suite to verify no regressions**

```bash
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/analytics.py backend/app/main.py tests/backend/api/test_analytics.py
git commit -m "feat: analytics API endpoints (load, sport-breakdown, performance)"
```

---

## Task 3: Frontend API Client

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add analytics API functions**

Open `frontend/src/lib/api.ts`. Add at the end (before the final closing or after existing exports):

```typescript
// ── Analytics ──────────────────────────────────────────────────────────
export interface AcwrPoint {
  date: string;
  acwr: number;
  acute: number;
  chronic: number;
}

export interface TrainingLoadPoint {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
}

export interface LoadAnalytics {
  acwr: AcwrPoint[];
  training_load: TrainingLoadPoint[];
}

export interface SportBreakdown {
  [sport: string]: number;
}

export interface PerformancePoint {
  date: string;
  value: number;
}

export interface PerformanceAnalytics {
  vdot: PerformancePoint[];
  e1rm: PerformancePoint[];
}

export async function getLoadAnalytics(athleteId: number): Promise<LoadAnalytics> {
  return _req(`/athletes/${athleteId}/analytics/load`);
}

export async function getSportBreakdown(athleteId: number): Promise<SportBreakdown> {
  return _req(`/athletes/${athleteId}/analytics/sport-breakdown`);
}

export async function getPerformanceAnalytics(athleteId: number): Promise<PerformanceAnalytics> {
  return _req(`/athletes/${athleteId}/analytics/performance`);
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat: analytics API client types and functions"
```

---

## Task 4: ACWR Trend Chart Component

**Files:**
- Create: `frontend/src/components/analytics/AcwrTrendChart.tsx`

- [ ] **Step 1: Install Recharts if not present**

```bash
cd frontend && npm list recharts 2>/dev/null || npm install recharts
```

- [ ] **Step 2: Create AcwrTrendChart component**

```tsx
// frontend/src/components/analytics/AcwrTrendChart.tsx
"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { AcwrPoint } from "@/lib/api";

interface Props {
  data: AcwrPoint[];
}

export function AcwrTrendChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No data yet — log sessions to see ACWR trend
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: d.date.slice(5), // "MM-DD"
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={formatted} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
        />
        <YAxis domain={[0, 2]} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(val: number) => val.toFixed(2)}
          labelFormatter={(label) => `Date: ${label}`}
        />
        {/* Safe zone */}
        <ReferenceLine y={0.8} stroke="#22c55e" strokeDasharray="4 4" label={{ value: "0.8", position: "right", fontSize: 10 }} />
        <ReferenceLine y={1.3} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "1.3", position: "right", fontSize: 10 }} />
        <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "1.5", position: "right", fontSize: 10 }} />
        <Line
          type="monotone"
          dataKey="acwr"
          stroke="var(--primary)"
          strokeWidth={2}
          dot={false}
          name="ACWR"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/analytics/AcwrTrendChart.tsx
git commit -m "feat: AcwrTrendChart component with danger zone reference lines"
```

---

## Task 5: Training Load Chart Component

**Files:**
- Create: `frontend/src/components/analytics/TrainingLoadChart.tsx`

- [ ] **Step 1: Create TrainingLoadChart component**

```tsx
// frontend/src/components/analytics/TrainingLoadChart.tsx
"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TrainingLoadPoint } from "@/lib/api";

interface Props {
  data: TrainingLoadPoint[];
}

export function TrainingLoadChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No data yet — log sessions to see training load
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: d.date.slice(5),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={formatted} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(val: number) => val.toFixed(1)} />
        <Legend />
        <Line type="monotone" dataKey="ctl" stroke="#6366f1" strokeWidth={2} dot={false} name="CTL" />
        <Line type="monotone" dataKey="atl" stroke="#f59e0b" strokeWidth={2} dot={false} name="ATL" />
        <Line type="monotone" dataKey="tsb" stroke="#22c55e" strokeWidth={1.5} dot={false} strokeDasharray="4 4" name="TSB" />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/analytics/TrainingLoadChart.tsx
git commit -m "feat: TrainingLoadChart component (CTL/ATL/TSB)"
```

---

## Task 6: Sport Breakdown and Performance Charts

**Files:**
- Create: `frontend/src/components/analytics/SportBreakdownChart.tsx`
- Create: `frontend/src/components/analytics/PerformanceTrendChart.tsx`

- [ ] **Step 1: Create SportBreakdownChart component**

```tsx
// frontend/src/components/analytics/SportBreakdownChart.tsx
"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { SportBreakdown } from "@/lib/api";

const COLORS: Record<string, string> = {
  running: "#6366f1",
  lifting: "#f59e0b",
  biking: "#22c55e",
  swimming: "#06b6d4",
  other: "#94a3b8",
};

interface Props {
  data: SportBreakdown;
}

export function SportBreakdownChart({ data }: Props) {
  const entries = Object.entries(data).map(([name, minutes]) => ({
    name,
    value: Math.round(minutes / 60 * 10) / 10, // hours, 1 decimal
  }));

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No sessions logged yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={entries}
          cx="50%"
          cy="50%"
          outerRadius={80}
          dataKey="value"
          label={({ name, value }) => `${name} ${value}h`}
          labelLine={false}
        >
          {entries.map((entry) => (
            <Cell
              key={entry.name}
              fill={COLORS[entry.name] ?? COLORS.other}
            />
          ))}
        </Pie>
        <Tooltip formatter={(val: number) => [`${val}h`, "Hours"]} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Create PerformanceTrendChart component**

```tsx
// frontend/src/components/analytics/PerformanceTrendChart.tsx
"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceAnalytics } from "@/lib/api";

interface Props {
  data: PerformanceAnalytics;
}

export function PerformanceTrendChart({ data }: Props) {
  const hasVdot = data.vdot.length > 0;
  const hasE1rm = data.e1rm.length > 0;

  if (!hasVdot && !hasE1rm) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No performance data yet — log sessions with VDOT or e1RM
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {hasVdot && (
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">VDOT (Running)</p>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={data.vdot} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip formatter={(val: number) => val.toFixed(1)} />
              <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} name="VDOT" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {hasE1rm && (
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">e1RM (Lifting, kg)</p>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={data.e1rm} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip formatter={(val: number) => `${val.toFixed(1)} kg`} />
              <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} name="e1RM" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/analytics/SportBreakdownChart.tsx frontend/src/components/analytics/PerformanceTrendChart.tsx
git commit -m "feat: SportBreakdownChart and PerformanceTrendChart components"
```

---

## Task 7: Analytics Dashboard Page + Navigation

**Files:**
- Create: `frontend/src/app/analytics/page.tsx`
- Modify: `frontend/src/components/top-nav.tsx`

- [ ] **Step 1: Create analytics page**

```tsx
// frontend/src/app/analytics/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import {
  getLoadAnalytics,
  getSportBreakdown,
  getPerformanceAnalytics,
  type LoadAnalytics,
  type SportBreakdown,
  type PerformanceAnalytics,
} from "@/lib/api";
import { AcwrTrendChart } from "@/components/analytics/AcwrTrendChart";
import { TrainingLoadChart } from "@/components/analytics/TrainingLoadChart";
import { SportBreakdownChart } from "@/components/analytics/SportBreakdownChart";
import { PerformanceTrendChart } from "@/components/analytics/PerformanceTrendChart";

export default function AnalyticsPage() {
  const { athlete, token } = useAuth();
  const router = useRouter();

  const [load, setLoad] = useState<LoadAnalytics | null>(null);
  const [breakdown, setBreakdown] = useState<SportBreakdown | null>(null);
  const [performance, setPerformance] = useState<PerformanceAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    if (!athlete) return;

    Promise.all([
      getLoadAnalytics(athlete.id),
      getSportBreakdown(athlete.id),
      getPerformanceAnalytics(athlete.id),
    ])
      .then(([l, b, p]) => {
        setLoad(l);
        setBreakdown(b);
        setPerformance(p);
      })
      .catch((e) => setError(e.message ?? "Failed to load analytics"));
  }, [athlete, token, router]);

  if (!token || !athlete) return null;

  if (error) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-destructive">{error}</p>
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* ACWR */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">ACWR Trend</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Acute:Chronic Workload Ratio — safe zone 0.8–1.3
        </p>
        {load ? (
          <AcwrTrendChart data={load.acwr} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>

      {/* Training Load */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">Training Load</h2>
        <p className="text-sm text-muted-foreground mb-4">
          CTL (fitness), ATL (fatigue), TSB (form)
        </p>
        {load ? (
          <TrainingLoadChart data={load.training_load} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>

      {/* Sport Breakdown */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">Sport Breakdown</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Total training hours per sport (all time)
        </p>
        {breakdown ? (
          <SportBreakdownChart data={breakdown} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>

      {/* Performance Trends */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">Performance Trends</h2>
        <p className="text-sm text-muted-foreground mb-4">
          VDOT progression (running) and e1RM progression (lifting)
        </p>
        {performance ? (
          <PerformanceTrendChart data={performance} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>
    </main>
  );
}
```

- [ ] **Step 2: Add Analytics to top navigation**

Open `frontend/src/components/top-nav.tsx`. Find the `NAV_LINKS` array. Add the Analytics entry:

```typescript
// Find the existing NAV_LINKS array, e.g.:
// const NAV_LINKS = [
//   { href: "/dashboard", label: "Dashboard" },
//   { href: "/plan", label: "Plan" },
//   ...
// ]
// Add:
  { href: "/analytics", label: "Analytics" },
```

Add it after "History" and before "Settings" (or at end if Settings not yet present).

- [ ] **Step 3: TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 4: Run full test suite**

```bash
cd C:\Users\simon\resilio-plus
poetry run pytest tests/ -q
```

Expected: ≥1243 tests pass, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/analytics/page.tsx frontend/src/components/top-nav.tsx
git commit -m "feat: analytics dashboard page and navigation link"
```

---

## Self-Review

**Spec coverage:**
- `GET /athletes/{id}/analytics/load` — ACWR + CTL/ATL/TSB → Task 2 ✅
- `GET /athletes/{id}/analytics/sport-breakdown` → Task 2 ✅
- `GET /athletes/{id}/analytics/performance` — VDOT + e1RM → Task 2 ✅
- AcwrTrendChart with danger zones → Task 4 ✅
- TrainingLoadChart CTL/ATL/TSB → Task 5 ✅
- SportBreakdownChart → Task 6 ✅
- PerformanceTrendChart → Task 6 ✅
- `frontend/src/app/analytics/page.tsx` → Task 7 ✅
- Navigation "Analytics" link → Task 7 ✅

**Placeholder scan:** No TBD, no TODOs, all code complete.

**Type consistency:**
- `AcwrPoint`, `TrainingLoadPoint`, `LoadAnalytics`, `SportBreakdown`, `PerformancePoint`, `PerformanceAnalytics` defined in Task 3, used in Tasks 4–7 ✅
- `compute_acwr_series`, `compute_ctl_atl_tsb`, `compute_sport_breakdown`, `compute_performance_trends` defined in Task 1, imported in Task 2 ✅
- `getLoadAnalytics`, `getSportBreakdown`, `getPerformanceAnalytics` defined in Task 3, used in Task 7 ✅

All good.
