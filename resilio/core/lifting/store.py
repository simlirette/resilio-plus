"""
File-backed storage for lifting data under ``data/lifting/``.

    workouts/YYYY-MM/<hevy_id>.yaml   one Hevy workout per file
    sync_state.yaml                   last successful sync timestamps
    exercise_templates.yaml           cached Hevy exercise templates
    hevy_routines.yaml                Resilio routine slots pushed to Hevy (SP5)
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

from resilio.schemas.lifting import ExerciseTemplate, HevyWorkout, LiftingSyncState


def default_lifting_dir() -> Path:
    from resilio.core.config import get_repo_root

    return get_repo_root() / "data" / "lifting"


def _dump(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    tmp.replace(path)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class LiftingStore:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base = Path(base_dir) if base_dir is not None else default_lifting_dir()

    # ------------------------------------------------------------ workouts

    @property
    def workouts_dir(self) -> Path:
        return self.base / "workouts"

    def _find(self, workout_id: str) -> list[Path]:
        if not self.workouts_dir.exists():
            return []
        return list(self.workouts_dir.glob(f"*/{workout_id}.yaml"))

    def has_workout(self, workout_id: str) -> bool:
        return bool(self._find(workout_id))

    def save_workout(self, workout: HevyWorkout) -> Path:
        target = self.workouts_dir / workout.start_time.strftime("%Y-%m") / f"{workout.id}.yaml"
        for old in self._find(workout.id):
            if old != target:
                old.unlink()
        _dump(target, workout.model_dump(mode="json"))
        return target

    def delete_workout(self, workout_id: str) -> bool:
        found = self._find(workout_id)
        for p in found:
            p.unlink()
        return bool(found)

    def workout_ids(self) -> set[str]:
        if not self.workouts_dir.exists():
            return set()
        return {p.stem for p in self.workouts_dir.glob("*/*.yaml")}

    def load_workouts(
        self, since: Optional[date] = None, until: Optional[date] = None
    ) -> list[HevyWorkout]:
        if not self.workouts_dir.exists():
            return []
        out = []
        for p in self.workouts_dir.glob("*/*.yaml"):
            w = HevyWorkout.model_validate(_load(p))
            d = w.local_date
            if since and d < since:
                continue
            if until and d > until:
                continue
            out.append(w)
        return sorted(out, key=lambda w: w.start_time)

    # --------------------------------------------------------------- state

    def load_state(self) -> LiftingSyncState:
        data = _load(self.base / "sync_state.yaml")
        return LiftingSyncState.model_validate(data) if data else LiftingSyncState()

    def save_state(self, state: LiftingSyncState) -> None:
        _dump(self.base / "sync_state.yaml", state.model_dump(mode="json"))

    # ----------------------------------------------------------- templates

    def save_templates(self, templates: list[ExerciseTemplate]) -> None:
        _dump(self.base / "exercise_templates.yaml", [t.model_dump(mode="json") for t in templates])

    def load_templates(self) -> dict[str, ExerciseTemplate]:
        data = _load(self.base / "exercise_templates.yaml") or []
        return {t["id"]: ExerciseTemplate.model_validate(t) for t in data}

    # ------------------------------------------------------ routine slots

    def load_routine_map(self) -> dict:
        return dict(_load(self.base / "hevy_routines.yaml") or {})

    def save_routine_map(self, data: dict) -> None:
        _dump(self.base / "hevy_routines.yaml", data)
