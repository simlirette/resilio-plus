# Resume prompt — Resilio V4, starting at T2

> Paste the block below into Codex after `/goal`. Written 2026-08-18 after T1 shipped.

---

```
Resume building Resilio V4 — the text-native coach.

SPEC: read docs/prompts/CODEX-V4-TEXT-COACH.md (execution brief) and
docs/GOAL-V4-TEXT-COACH.md (the why + locked decisions) before touching
anything. Where the brief disagrees with the code, the code wins — correct the
brief and say so.

WHERE THINGS STAND:
- T0 done: Phase D merged to main.
- T1 done and VERIFIED on branch feat/v4-t1-messaging-core (6 commits):
  backend/app/messaging/{base,chunking,gateway,notification_service}.py,
  tests/backend/messaging/ (77 tests, all passing in 0.87s),
  alembic 0013_messaging_core.
  Verified 2026-08-18: 77/77 scoped, ruff 0, mypy 0 errors / 164 files.
- main is at b45b620. T1 is NOT yet merged.

STEP 0: merge feat/v4-t1-messaging-core into main (it is verified — do not
re-litigate it), then create feat/v4-t2-telegram and work there.

START AT T2 — Telegram channel. Then T3 approvals, T4 onboarding over text,
T5 Google Calendar, T6 weekly automation, T7 freeze clients, T8 deploy+smoke.

*** WHY THE LAST TWO SESSIONS DIED — DO NOT REPEAT THIS ***
Both were killed by holding a live code-mode cell open while waiting on a long
command: launch the test suite as a cell, then wait(cell_id=N,
yield_time_ms=50000) over and over for 15+ minutes. The Node code-mode host
dies mid-wait with "code-mode host closed its stdout", which removes all tool
execution and ends the session. Codex logs nothing — the failure is in the
child process.

NEVER wait on a long-running cell. Detach and poll the file instead:
  nohup "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1 &
  echo launched
then, in SEPARATE short calls minutes apart:
  tail -5 /tmp/pytest.txt
Each poll returns in under a second. Do useful work between polls. Never cat a
whole result file.

STOP AT THE END OF T2. Commit, report, and hand back — do not roll into T3.
Long sessions accumulate code-mode cells and host memory; the session that died
was on cell 139 with 55M cumulative input tokens. A fresh session per package
is the fix.

GATE for T2 — exactly this, no better and no worse:
  pytest : 3 failed, >=2693 passed   <- those 3 are PRE-EXISTING (Apple Health
                                        date drift x2, get_repo_root env). Do
                                        NOT fix or chase them. A 4th failure
                                        means you broke something.
  mypy   : 0 errors
  ruff   : 0 violations
Use the Poetry venv interpreter, not system Python:
  C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/

HARD CONSTRAINTS:
- Never modify backend/app/agents/, any existing test, or mypy/ruff config.
- resilio/ is read-only.
- TDD: tests first, red -> green -> refactor.
- Before any Alembic revision run `alembic heads` and chain from the real head.
  T1 used 0013, so T2's is 0014 unless the tree says otherwise.
- Atomic conventional commits, one per logical task.
- No new stack: LangGraph + FastAPI + SQLAlchemy 2 sync + APScheduler + Pydantic v2.
- Secrets only via env vars; Fernet-encrypt third-party tokens following
  backend/app/integrations/strava/oauth_service.py.
- Telegram specifics that matter: parse_mode=HTML not MarkdownV2; 4096-char
  limit; webhook returns 200 immediately and processes in a BackgroundTask;
  validate X-Telegram-Bot-Api-Secret-Token; dedupe on update_id; mock the Bot
  API with respx scoped to https://api.telegram.org — never patch httpx.Client
  globally (TestClient subclasses it).

REPORT at the end: files added, files modified, test count delta, the three
gate results, and confirmation that T2 is complete. If something is blocked,
finish everything else first, then say plainly what is blocked and why.
```
