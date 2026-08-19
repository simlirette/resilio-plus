# Resume prompt — Resilio V4, starting T3

> Paste the block below into Codex after `/goal`. Written 2026-08-19 after T2 shipped (12 commits,
> merged-ready) and the session that finished it froze during its idle tail — process stayed alive
> for hours at near-zero CPU after the last commit landed. Killed manually; no work was lost.

---

```
Continue building Resilio V4 — the text-native coach. T2 (Telegram channel) is complete, verified,
and committed. Start T3 — approvals over text.

SPEC: read docs/prompts/CODEX-V4-TEXT-COACH.md (execution brief, T3 section) and
docs/GOAL-V4-TEXT-COACH.md (the why + locked decisions) before touching anything. Where the brief
disagrees with the code, the code wins — correct the brief and say so. One known gap: the brief's
T3 section says "on approve -> trigger T5 calendar push," but T5 (Google Calendar) doesn't exist
yet — packages are being built in strict T1..T8 order. Implement approve/revise/reject fully;
where the calendar push would go, leave an explicit, clearly named seam (a function stub with a
docstring pointing at T5) rather than a bare pass or a fabricated calendar service.

WHERE THINGS STAND:
- T0, T1, T2 all done. T2 shipped 12 commits on feat/v4-t2-telegram: bot client + HTML channel,
  webhook (secret validation + update_id dedupe), update-processor runtime (bootstrap identity
  linking, callback_query acknowledgement with a callback_handler seam left None for you to fill),
  local polling loop, main.py wiring + env vars, Sentry/PII redaction for the bot token AND webhook
  event payloads, a deterministic-shutdown fix for the polling thread (stop() now raises
  TimeoutError instead of silently returning if the thread won't join), and doc updates. Also
  restored a corrupted session-log.md and recorded a T1+T2 entry.
- Verified 2026-08-19: mypy 0 errors (170 files), ruff 0 violations. Full pytest run completed
  after hand-off: **4 failed, 2767 passed, 16 skipped, 906s**. The 4th failure is NOT a T1/T2
  regression — see the gate note below, it's a known pre-existing flake that just happened to fire
  on today's date.
- main is still at 593d953 — T2 is NOT yet merged.

STEP 0: merge feat/v4-t2-telegram into main (it is verified — do not re-litigate it), then create
feat/v4-t3-approvals and work there.

STEP 1: run the full gate once before writing anything, and confirm it against the numbers already
measured at hand-off (below) — don't assume they still hold, this repo has a live sync-revert
hazard (see the data-loss note in the prior resume prompt), confirm fresh:
  PYTEST="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe"
  PY="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/python.exe"
  RUFF="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/ruff.exe"
  "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1; tail -30 /tmp/pytest.txt
  "$PY" -m mypy backend/app/ --config-file pyproject.toml > /tmp/mypy.txt 2>&1; tail -20 /tmp/mypy.txt
  "$RUFF" check backend/ > /tmp/ruff.txt 2>&1; tail -20 /tmp/ruff.txt
Measured 2026-08-19: 4 failed, 2767 passed, 16 skipped, 906s (15m06s — this run is slow, budget for
it, don't panic and kill it early). The 4 failures:
  tests/backend/api/test_apple_health_endpoint.py::TestValidImport::test_minimal_valid_imports_one_day
  tests/backend/api/test_apple_health_endpoint.py::TestValidImport::test_multi_day_imports_seven_days
  tests/unit/test_config.py::TestGetRepoRoot::test_get_repo_root_raises_when_not_in_repo
  tests/unit/test_vdot_continuity.py::TestBreakDetection::test_high_continuity_no_breaks
The first three are the long-standing baseline. The 4th is item #8 in docs/V1.1-BACKLOG.md — a
pre-existing, already-catalogued flake ("fails when run on certain calendar dates") that fires or
doesn't depending on today's actual weekday when the suite runs; it just happened to fire today.
There is also a 5th possible one, item #7 in the same doc (`test_history_shows_logged_count`,
a DB-ordering timing flake) — it did NOT fire this run but might on yours. Before treating ANY
failure beyond a totally novel one as your bug: check `docs/V1.1-BACKLOG.md` items 7–8 first. Both
are in code under V1-FROZEN governance (BACKEND_FROZEN.md) — do not fix them yourself even if you
spot the exact bug; they're deferred to V1.1 on purpose. Only a genuinely NEW, 6th failure —
something outside this known pool — means you broke something; stop and fix that one.

*** WHY THE LAST SESSION ENDED WITHOUT A HANDBACK — DO NOT REPEAT ***
Not a crash this time — a freeze. The process stayed alive at near-zero CPU for hours after the
last commit landed; every bit of real work was already safely committed, but nothing after that
point got reported back, and the operator had to kill it manually. This matches a known pattern on
this machine (see the reference-codex-freeze-maintenance memory): `approvals_reviewer =
"guardian_subagent"` in ~/.codex/config.toml, plus high reasoning effort, plus the Goals feature
running concurrently, correlate with freezes on long sessions — and all three were active here.
  - Before starting, confirm no stale codex/node process is still running from a prior session
    (`Get-Process codex,node` in PowerShell) — kill it first if so.
  - The standing rule still applies: NEVER hold a live code-mode cell open waiting on a long
    command (launch, then wait(cell_id, yield_time_ms=50000) repeatedly for minutes). Detach and
    poll a file instead — nohup the command, redirect to a file, then short separate `tail` calls
    minutes apart. Never cat a whole result file.
  - NEW lesson from this incident: once you print the final REPORT for this package, stop
    completely. Don't idle, don't keep polling anything, don't wait around for acknowledgement.
    This freeze happened after the work was done, sitting in that idle tail. A session that ends
    the moment it's done beats one that hangs after finishing.

GATE for T3 — exactly the floor from STEP 1, no better and no worse:
  pytest : 3-5 failed (see STEP 1's known pool), >=2767 passed
  mypy   : 0 errors
  ruff   : 0 violations

HARD CONSTRAINTS:
- Never modify backend/app/agents/, any existing test, or mypy/ruff config.
- resilio/ is read-only.
- TDD: tests first, red -> green -> refactor.
- Before any Alembic revision run `alembic heads` from the repo root (alembic.ini lives there, not
  under backend/) and chain from the real head. Confirmed 2026-08-19: head is 0013. T3's migration
  is 0014 unless the tree says otherwise by the time you check.
- Atomic conventional commits, one per logical task — commit each as you finish it, not in a batch
  at the end. This is the only real defense against every interruption this branch has hit so far
  (a Codex code-mode-cell wedge, a Claude Code app update, and now this freeze).
- No new stack: LangGraph + FastAPI + SQLAlchemy 2 sync + APScheduler + Pydantic v2.
- Secrets only via env vars; Fernet-encrypt third-party tokens following
  backend/app/integrations/strava/oauth_service.py.
- Telegram `callback_data` is capped at 64 bytes — the approval token (never a thread_id, never
  JSON) is the only thing that belongs in it; look everything else up server-side from the token.
- Approval tokens: default TTL 7 days. `resolve()` must reject expired, already-resolved, and
  cross-athlete tokens (403 on cross-athlete — verify ownership before touching anything).

STOP AT THE END OF T3. Commit, report, and hand back — do not roll into T4.

REPORT at the end: files added, files modified, test count delta (and the new floor you measured
in STEP 1), the three gate results, and confirmation that T3 is complete. If something is blocked,
finish everything else first, then say plainly what is blocked and why.
```
