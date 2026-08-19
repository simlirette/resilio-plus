# Resume prompt — Resilio V4, T3 retry in an isolated worktree

> Paste the block below into Codex after `/goal` — or without it this time, see the note at the
> bottom. Written 2026-08-19 after the first T3 attempt ran 3h21m, wrote and staged real code
> three separate times, never once committed, and then froze — the same silent-reasoning-cutoff
> signature as the two prior incidents, this time with `guardian_subagent` already disabled, which
> rules that setting out as the sole cause.

---

```
Build T3 for Resilio V4 — approvals over text. This is a clean start: an earlier attempt at T3
produced zero surviving code (see WHERE THINGS STAND) so there is nothing to resume or continue —
implement it from scratch.

WORK IN THE WORKTREE, NOT THE MAIN CHECKOUT — READ THIS FIRST:
Your working directory for this entire session must be:
  C:\Users\simon\resilio-plus\.worktrees\t3-approvals
It already exists, is already on branch feat/v4-t3-approvals, and is already up to date with main
(HEAD ff8633e — nothing to merge, nothing to branch). Do NOT cd into or edit anything under
C:\Users\simon\resilio-plus directly (the primary checkout, now on main) — during the last T3
attempt, three unrelated Codex sessions were found running concurrently in that exact primary
directory, touching unrelated old V3 files. Whether that caused the vanished work or not was never
fully pinned down, but running in an isolated worktree removes the possibility entirely. The Poetry
venv is shared and already confirmed working from inside the worktree (no `poetry install` needed) —
tools:
  PYTEST="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe"
  PY="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/python.exe"
  RUFF="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/ruff.exe"
Run every command with that worktree path as cwd.

SPEC: read docs/prompts/CODEX-V4-TEXT-COACH.md (execution brief, T3 section) and
docs/GOAL-V4-TEXT-COACH.md (the why + locked decisions) before touching anything — both exist in
the worktree, same content as main. Where the brief disagrees with the code, the code wins —
correct the brief and say so. One known gap: the brief's T3 section says "on approve -> trigger T5
calendar push," but T5 (Google Calendar) doesn't exist yet — packages are built in strict T1..T8
order. Implement approve/revise/reject fully; where the calendar push would go, leave an explicit,
clearly named seam (a function stub with a docstring pointing at T5) rather than a bare pass or a
fabricated calendar service.

WHERE THINGS STAND:
- T0, T1, T2 all done, merged, on main (HEAD ff8633e). T2 shipped 12 commits: Telegram client,
  webhook, polling, runtime, main.py wiring, Sentry/PII redaction, a deterministic polling-shutdown
  fix, docs. All verified.
- T3 attempt #1 (2026-08-19, 13:24-16:45, 3h21m): wrote backend/app/messaging/approvals.py and
  0014-migration material, staged it with `git add` eight times across the session, but never once
  ran `git commit`. Ended on a bare reasoning step with nothing after — no error, no exit code. The
  working tree is now clean; there is no draft to recover. Root cause not fully pinned (see the
  worktree note above) but two things are now confirmed: `guardian_subagent` was already off for
  this attempt (ruled out as sufficient alone), and the session never got a single unit of work to
  a committable state in over three hours — whatever the trigger, going that long without a commit
  is itself the thing to fix this time (see COMMIT DISCIPLINE below).
- Full gate, last confirmed 2026-08-19 on this exact HEAD: mypy 0 errors (170 files), ruff 0
  violations, pytest 4 failed / 2767 passed / 16 skipped. Re-confirm in STEP 1 rather than trusting
  this number blindly — it should be identical since no code changed, but confirm before you build
  on it.

COMMIT DISCIPLINE — the actual lesson from this incident:
Commit after the FIRST passing test for each piece, not after the whole approvals module feels
"done." A rough split: (1) the pending_approvals migration alone, (2) create_approval() + its test,
(3) resolve() happy path + its test, (4) resolve() expired/reused/cross-athlete rejections + tests,
(5) the approve/revise/reject wiring into the existing graph-resume path, (6) the T5 seam. Six small
commits, not one large one at the end. If you notice yourself past 45 minutes without a commit,
stop, get whatever is currently green committed, then continue.

STEP 0: none — you're already in the right place on the right branch. Go straight to STEP 1.

STEP 1: run the full gate once before writing anything, confirm it matches the numbers above:
  "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1; tail -30 /tmp/pytest.txt
  "$PY" -m mypy backend/app/ --config-file pyproject.toml > /tmp/mypy.txt 2>&1; tail -20 /tmp/mypy.txt
  "$RUFF" check backend/ > /tmp/ruff.txt 2>&1; tail -20 /tmp/ruff.txt
Expect 4 failures, not 3: the usual Apple Health pair + get_repo_root, plus
tests/unit/test_vdot_continuity.py::TestBreakDetection::test_high_continuity_no_breaks, a
pre-existing calendar-dependent flake (docs/V1.1-BACKLOG.md item #8, fires on some weekdays and not
others). A possible 5th, item #7 (`test_history_shows_logged_count`, a DB-ordering flake) may or may
not fire. Both are V1-FROZEN territory (BACKEND_FROZEN.md) — do not fix them. Only a genuinely new
failure outside this named pool means you broke something.

*** WHY THE LAST TWO T3 SESSIONS DIED — DO NOT REPEAT EITHER ***
1. NEVER hold a live code-mode cell open waiting on a long command (launch, then
   wait(cell_id, yield_time_ms=50000) repeatedly for minutes). The Node code-mode host dies mid-wait
   with no error. Detach and poll a file instead — nohup the command, redirect to a file, then short
   separate `tail` calls minutes apart. Never cat a whole result file.
2. Once you print the final REPORT, stop completely — don't idle, don't keep polling, don't wait for
   acknowledgement. A prior session froze in exactly that idle tail after the work was already done.
3. NEW: don't let three hours pass without a commit. If you're still mid-implementation at the
   45-minute mark with nothing committed, that itself is the signal to stop, commit whatever passes
   right now even if incomplete-but-inert (e.g., the migration alone, or approvals.py with only
   create_approval implemented and tested), and continue from there.

GATE for T3 — exactly the floor from STEP 1, no better and no worse:
  pytest : 3-5 failed (see STEP 1's known pool), >=2767 passed
  mypy   : 0 errors
  ruff   : 0 violations

HARD CONSTRAINTS:
- Never modify backend/app/agents/, any existing test, or mypy/ruff config.
- resilio/ is read-only.
- TDD: tests first, red -> green -> refactor.
- Before any Alembic revision run `alembic heads` from the worktree root (alembic.ini lives at repo
  root, not under backend/) and chain from the real head. Confirmed 2026-08-19: head is 0013. T3's
  migration is 0014 unless the tree says otherwise by the time you check.
- Atomic conventional commits, one per logical task, committed as you finish each — see COMMIT
  DISCIPLINE above, this is not optional this time.
- No new stack: LangGraph + FastAPI + SQLAlchemy 2 sync + APScheduler + Pydantic v2.
- Secrets only via env vars; Fernet-encrypt third-party tokens following
  backend/app/integrations/strava/oauth_service.py.
- Telegram `callback_data` is capped at 64 bytes — the approval token (never a thread_id, never
  JSON) is the only thing that belongs in it; look everything else up server-side from the token.
- Approval tokens: default TTL 7 days. `resolve()` must reject expired, already-resolved, and
  cross-athlete tokens (403 on cross-athlete — verify ownership before touching anything).

STOP AT THE END OF T3. Commit, report, and hand back — do not roll into T4.

REPORT at the end: files added, files modified, commits made (list them — there should be several,
not one), test count delta, the three gate results, and confirmation T3 is complete. If something
is blocked, finish everything else first, then say plainly what is blocked and why.
```

**On `/goal`:** every prior V4 session used it, and every one eventually froze — `guardian_subagent`
is now ruled out as a sufficient cause on its own, leaving `model_reasoning_effort = "xhigh"` and the
Goals feature itself as the two remaining known correlates from the original diagnosis. If this
worktree attempt freezes too, the next experiment is dropping `/goal` (or reasoning effort) to
isolate which one actually matters — not repeating the same combination a fourth time.
