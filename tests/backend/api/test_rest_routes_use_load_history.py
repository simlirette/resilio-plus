"""The REST planning routes must see the athlete's training history.

`core/load_history.py` was written when the V4 weekly cycle was rewired, but
only that path was updated. `routes/plans.py` and `routes/workflow.py` kept
passing `load_history=[]`, which pins ACWR at 0.00 "undertrained" no matter how
much the athlete has actually been training -- so a plan built through the API
is computed as though they had never trained, while the same athlete planning
over Telegram gets the real ratio.

Two doors onto the same engine giving different answers is worse than either
answer, so this pins that both read the same series.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

PLANNING_ROUTES = [
    "backend/app/routes/plans.py",
    "backend/app/routes/workflow.py",
]


def _load_history_arguments(path: pathlib.Path) -> list[tuple[int, str]]:
    """Every `load_history=` keyword argument, as source text."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "load_history":
                found.append((keyword.value.lineno, ast.unparse(keyword.value)))
    return found


@pytest.mark.parametrize("module", PLANNING_ROUTES)
def test_no_planning_call_passes_an_empty_history(module: str) -> None:
    path = REPO_ROOT / module
    assert path.is_file(), f"{module} moved; update this test"

    empties = [
        f"  line {line}: load_history={text}"
        for line, text in _load_history_arguments(path)
        if text in ("[]", "list()")
    ]

    assert not empties, (
        "an empty history pins ACWR at 0.00 undertrained in {}:\n{}".format(
            module, "\n".join(empties)
        )
    )


@pytest.mark.parametrize("module", PLANNING_ROUTES)
def test_the_history_comes_from_the_shared_helper(module: str) -> None:
    """Not just non-empty -- the same series the weekly cycle uses."""
    path = REPO_ROOT / module
    arguments = _load_history_arguments(path)

    assert arguments, f"{module} no longer calls a planner; update this test"
    for line, text in arguments:
        assert "daily_training_loads" in text, (
            f"{module}:{line} builds its own history: {text}"
        )


class TestTheScannerWorks:
    def test_it_finds_an_empty_list(self, tmp_path: pathlib.Path) -> None:
        f = tmp_path / "m.py"
        f.write_text("coach.build_week(ctx, load_history=[])\n", encoding="utf-8")

        assert _load_history_arguments(f) == [(1, "[]")]

    def test_it_finds_a_call(self, tmp_path: pathlib.Path) -> None:
        f = tmp_path / "m.py"
        f.write_text(
            "coach.build_week(ctx, load_history=daily_training_loads(a, db))\n",
            encoding="utf-8",
        )

        assert _load_history_arguments(f) == [(1, "daily_training_loads(a, db)")]

    def test_it_ignores_other_keywords(self, tmp_path: pathlib.Path) -> None:
        f = tmp_path / "m.py"
        f.write_text("coach.build_week(ctx, phase=[])\n", encoding="utf-8")

        assert _load_history_arguments(f) == []
