#!/usr/bin/env python3
"""Offline eval for classify_intent service — Phase D (D15).

Runs classify_intent against the eval dataset at data/classify_intent_eval.jsonl
and reports per-case and aggregate accuracy.

Usage:
    python scripts/eval_classify_intent.py [--verbose] [--limit N]

Environment:
    ANTHROPIC_API_KEY — required (uses claude-haiku-4-5-20251001)

Output:
    Per-case: PASS / FAIL with reason
    Summary: accuracy per dimension (decision, specialist_chain, language)
    Exit code 0 if accuracy ≥ 75%, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Allow running from repo root without installing backend package
sys.path.insert(0, str(Path(__file__).parents[1]))

from backend.app.schemas.intent import (
    IntentClassificationRequest,
    ConversationContextMinimal,
    UserProfileMinimal,
)
from backend.app.services.classify_intent_service import classify_intent


# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parents[1]
EVAL_PATH = REPO_ROOT / "data" / "classify_intent_eval.jsonl"

# ── Accuracy threshold ─────────────────────────────────────────────────────────

PASS_THRESHOLD = 0.75  # 75% overall accuracy required


# ── Eval structures ────────────────────────────────────────────────────────────

@dataclass
class EvalCase:
    id: str
    user_message: str
    expected_decision: str
    expected_specialist_chain: list[str]
    language: str
    notes: str


@dataclass
class EvalResult:
    case_id: str
    decision_correct: bool
    specialist_correct: bool
    language_correct: bool
    actual_decision: str
    actual_specialists: list[str]
    actual_language: str
    error: str | None = None
    elapsed_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.decision_correct and self.error is None


# ── Loader ─────────────────────────────────────────────────────────────────────

def load_eval_cases(path: Path, limit: int | None = None) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            cases.append(EvalCase(
                id=d["id"],
                user_message=d["user_message"],
                expected_decision=d["expected_decision"],
                expected_specialist_chain=d.get("expected_specialist_chain", []),
                language=d.get("language", "fr"),
                notes=d.get("notes", ""),
            ))
    if limit:
        cases = cases[:limit]
    return cases


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_case(case: EvalCase) -> EvalResult:
    req = IntentClassificationRequest(
        user_message=case.user_message,
        conversation_context_minimal=ConversationContextMinimal(last_3_intents=[]),
        user_profile_minimal=UserProfileMinimal(
            athlete_id="eval-dummy",
            journey_phase="steady_state",
            sports=["running", "lifting", "swimming", "biking"],
        ),
    )

    t0 = time.monotonic()
    try:
        result = classify_intent(req)
        elapsed_ms = (time.monotonic() - t0) * 1000

        actual_specialists = (
            [s.specialist for s in result.specialist_chain]
            if result.specialist_chain
            else []
        )

        # Decision match: exact
        decision_correct = result.decision == case.expected_decision

        # Specialist match: expected specialists must all be present (order-insensitive)
        # For chains where we only check a subset, we check inclusion
        if case.expected_specialist_chain:
            specialist_correct = set(case.expected_specialist_chain).issubset(
                set(actual_specialists)
            )
        else:
            specialist_correct = True  # no expected chain → don't penalise

        language_correct = result.language_detected == case.language

        return EvalResult(
            case_id=case.id,
            decision_correct=decision_correct,
            specialist_correct=specialist_correct,
            language_correct=language_correct,
            actual_decision=result.decision,
            actual_specialists=actual_specialists,
            actual_language=result.language_detected,
            elapsed_ms=elapsed_ms,
        )

    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.monotonic() - t0) * 1000
        return EvalResult(
            case_id=case.id,
            decision_correct=False,
            specialist_correct=False,
            language_correct=False,
            actual_decision="ERROR",
            actual_specialists=[],
            actual_language="unknown",
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )


# ── Report ─────────────────────────────────────────────────────────────────────

def print_report(cases: list[EvalCase], results: list[EvalResult], verbose: bool) -> float:
    print("\n" + "=" * 60)
    print("classify_intent eval — Phase D (D15)")
    print("=" * 60)

    case_map = {c.id: c for c in cases}
    n = len(results)
    n_pass = sum(1 for r in results if r.passed)
    n_decision_correct = sum(1 for r in results if r.decision_correct)
    n_specialist_correct = sum(1 for r in results if r.specialist_correct)
    n_language_correct = sum(1 for r in results if r.language_correct)
    total_ms = sum(r.elapsed_ms for r in results)

    for r in results:
        case = case_map[r.case_id]
        status = "PASS" if r.passed else "FAIL"
        if verbose or not r.passed:
            print(f"\n[{status}] {r.case_id}")
            print(f"  Input   : {case.user_message[:80]}")
            print(f"  Expected: decision={case.expected_decision!r}, specialists={case.expected_specialist_chain}")
            print(f"  Actual  : decision={r.actual_decision!r}, specialists={r.actual_specialists}, lang={r.actual_language!r}")
            print(f"  Elapsed : {r.elapsed_ms:.0f}ms")
            if r.error:
                print(f"  Error   : {r.error}")
            if not r.decision_correct:
                print(f"  ❌ Decision mismatch")
            if not r.specialist_correct and case.expected_specialist_chain:
                print(f"  ❌ Specialist chain mismatch")

    print("\n" + "-" * 60)
    print(f"Total cases     : {n}")
    print(f"Decision acc.   : {n_decision_correct}/{n} = {n_decision_correct/n*100:.1f}%")
    print(f"Specialist acc. : {n_specialist_correct}/{n} = {n_specialist_correct/n*100:.1f}%")
    print(f"Language acc.   : {n_language_correct}/{n} = {n_language_correct/n*100:.1f}%")
    print(f"Overall PASS    : {n_pass}/{n} = {n_pass/n*100:.1f}%")
    print(f"Avg latency     : {total_ms/n:.0f}ms per case")
    print("-" * 60)

    accuracy = n_pass / n if n > 0 else 0.0
    threshold_pct = PASS_THRESHOLD * 100
    if accuracy >= PASS_THRESHOLD:
        print(f"✅ PASS — accuracy {accuracy*100:.1f}% ≥ {threshold_pct:.0f}% threshold")
    else:
        print(f"❌ FAIL — accuracy {accuracy*100:.1f}% < {threshold_pct:.0f}% threshold")
    print("=" * 60)
    return accuracy


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Eval classify_intent accuracy")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print all cases")
    parser.add_argument("--limit", type=int, default=None, help="Run only first N cases")
    args = parser.parse_args()

    if not EVAL_PATH.exists():
        print(f"Eval dataset not found: {EVAL_PATH}", file=sys.stderr)
        return 1

    cases = load_eval_cases(EVAL_PATH, limit=args.limit)
    print(f"Running {len(cases)} eval cases against classify_intent (claude-haiku-4-5-20251001)…")
    print("This may take a few minutes.\n")

    results: list[EvalResult] = []
    for i, case in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {case.id}… ", end="", flush=True)
        result = run_case(case)
        status = "✓" if result.passed else "✗"
        print(f"{status} ({result.elapsed_ms:.0f}ms)")
        results.append(result)

    accuracy = print_report(cases, results, verbose=args.verbose)
    return 0 if accuracy >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
