# Resume prompt — Resilio V4, continuing T2 (interrupted mid-session)

> Paste the block below into Codex after `/goal`. Written 2026-08-19 after the T2 session was cut
> off mid-work by a Claude Code app update — a different failure mode than the code-mode-cell crash
> documented below, same lesson: commit constantly.

---

```
Continue building Resilio V4 — the text-native coach. This resumes T2, which is already
feature-complete but was never committed before the session died.

SPEC: read docs/prompts/CODEX-V4-TEXT-COACH.md (execution brief) and
docs/GOAL-V4-TEXT-COACH.md (the why + locked decisions) before touching anything. Where the brief
disagrees with the code, the code wins — correct the brief and say so.

WHERE THINGS STAND:
- T0, T1 done, merged, verified on main @ 593d953 (77 messaging tests). Do not re-merge.
- You are already on feat/v4-t2-telegram (main + 1 commit, 2b4e01f). Do not create a new branch.
- T2 code exists and is feature-complete but 100% UNCOMMITTED — the prior session was killed by a
  Claude Code app update mid-T2, before anything landed. Working tree right now has:
    NEW  backend/app/integrations/telegram/{__init__,client,channel,webhook,polling,runtime}.py
    NEW  tests/backend/integrations/telegram/{__init__,test_channel,test_client,test_webhook,
         test_polling,test_runtime,test_dev_launcher,test_sentry_redaction}.py
    MOD  backend/app/main.py                       (+9: wires telegram_router, lifespan polling start/stop)
    MOD  .env.example                              (+10: TELEGRAM_BOT_TOKEN/MODE/WEBHOOK_SECRET/BOOTSTRAP_CHAT_ID)
    MOD  backend/app/observability/pii_filter.py    (scrubs bot token out of api.telegram.org URLs)
    MOD  backend/app/observability/sentry.py        (include_local_variables=False, scrubs transactions too)
    MOD  scripts/start_dev.ps1                      (uvicorn --env-file .env, so TELEGRAM_* loads in dev)
    MOD  docs/backend-v2/v4-telegram-channel.md     (doc already updated to match the code below)
- Verified already, scoped, 2026-08-19:
    pytest tests/backend/integrations/telegram tests/backend/messaging -> 132 passed, 9.21s
    mypy backend/app/integrations/telegram/ backend/app/messaging/ -> 0 errors, 11 files
    ruff check (same two dirs) -> 0 violations
  NOT yet run: the full-repo gate. Do that first (STEP 1), before writing more code.
- Read the code before assuming anything is missing — already confirmed present: webhook.py
  validates X-Telegram-Bot-Api-Secret-Token with secrets.compare_digest, dedupes on update_id via
  an in-memory LRU, returns 200 + processes in a BackgroundTask. runtime.py's
  TelegramUpdateProcessor handles both `message` (bootstrap-chat linking / link-code capture /
  gateway.handle_inbound + a typing action) and `callback_query` (acknowledges it, then calls an
  optional callback_handler seam — intentionally None for now; T3 plugs in there). client.py
  retries only explicit 429s, capped at 60s backoff, and never leaks the token in errors. This
  matches the T2 section of CODEX-V4-TEXT-COACH.md essentially in full — T2 is a wrap-up, not a
  build-more.

*** DATA LOSS IN PROGRESS — FIX THIS FIRST, BEFORE ANYTHING ELSE ***
session-log.md's working copy has been overwritten with a stale, unrelated 29-line snippet (two
2026-04-26 Phase D entries) that doesn't match HEAD (~198 lines of older FE/audit entries) — and
neither version has any T1/T2 history. This is the known "Resilio Sync reverts uncommitted files"
issue: some other synced copy of this repo is stomping local edits before they get committed.
  1. `git checkout -- session-log.md`  — restore HEAD's version before anything might commit the
     working copy as-is. Committing it now would permanently destroy the older entries that exist
     only in HEAD.
  2. Append ONE new dated entry (2026-08-19) summarizing T1 + T2: what shipped, key decisions
     (parse_mode HTML not MarkdownV2, in-memory LRU dedupe process-local by design, callback_handler
     seam left None for T3, retry_after capped at 60s), and note both interruptions this branch has
     now survived (Codex code-mode-cell wedge; Claude Code app update mid-T2) plus this sync-revert
     finding itself, since it will keep happening otherwise.
  3. Commit this file EARLY and ALONE, separate from the code commits. Don't leave it modified-but-
     uncommitted for more than a few minutes — that's the exact window Sync reverts in. If any
     tracked file's working copy looks wrong (content that doesn't match what you just wrote, or
     looks unexpectedly old), assume Sync clobbered it, diff against HEAD to confirm, and reapply —
     don't trust disk state blindly.
- Leave `docs/superpowers/plans/2026-04-26-phase-d.md` alone — untracked debris from an old
  session, never committed on any branch, unrelated to T2. Don't add it, don't delete it, and don't
  let a broad `git add` sweep it into a T2 commit.

STEP 0: none needed — you're already on the right branch. Go straight to STEP 1.

STEP 1 — full gate (hasn't run since before the interruption):
  PYTEST="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/pytest.exe"
  PY="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/python.exe"
  RUFF="C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/ruff.exe"
  "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1; tail -30 /tmp/pytest.txt
  "$PY" -m mypy backend/app/ --config-file pyproject.toml > /tmp/mypy.txt 2>&1; tail -20 /tmp/mypy.txt
  "$RUFF" check backend/ > /tmp/ruff.txt 2>&1; tail -20 /tmp/ruff.txt
If a 4th pytest failure or any mypy/ruff violation shows up beyond the 3 known pre-existing ones,
it's in the uncommitted telegram code (nothing else changed) — fix it there. Do not touch the
pre-existing 3, and never touch backend/app/agents/.

STEP 2 — split the uncommitted work into atomic conventional commits (none exist yet). Suggested
boundaries — adjust if the actual diff disagrees:
  feat(telegram): add bot client + HTML channel formatting
  feat(telegram): add webhook endpoint with secret validation + update dedupe
  feat(telegram): add update processor runtime + bootstrap identity linking
  feat(telegram): add local polling loop for dev
  feat(observability): scrub telegram bot token from Sentry + PII logs
  chore(dev): load .env in the Windows dev launcher
  feat(telegram): wire router and lifespan polling into the app
  docs(telegram): reconcile transport doc with the shipped implementation
  docs: restore session log, record T1+T2 entry
Commit as you go, not all at the end — see the data-loss warning above for why.

STEP 3 — re-run the full gate once more after committing, to prove the committed tree (not just
the working tree) is green.

GATE for T2 — exactly this, no better and no worse:
  pytest : 3 failed, >=2693 passed   <- pre-existing (Apple Health date drift x2, get_repo_root
                                        env). Do NOT fix or chase them. A 4th is yours to fix.
  mypy   : 0 errors
  ruff   : 0 violations

*** WHY SESSIONS KEEP DYING ON THIS BRANCH — DO NOT REPEAT EITHER ***
Two distinct failure modes have now killed work here:
1. (Codex-specific) Holding a live code-mode cell open while waiting on a long command: launch the
   test suite as a cell, then wait(cell_id=N, yield_time_ms=50000) repeatedly for 15+ minutes. The
   Node code-mode host dies mid-wait ("code-mode host closed its stdout"), which kills all tool
   execution and ends the session. Codex logs nothing — the failure is in the child process. NEVER
   wait on a long-running cell. Detach and poll the file instead:
     nohup "$PYTEST" tests/ -q --tb=line -p no:cacheprovider > /tmp/pytest.txt 2>&1 &
     echo launched
   then, in SEPARATE short calls minutes apart: tail -5 /tmp/pytest.txt. Never cat a whole file.
2. (This session) A Claude Code app auto-update killed the session outright mid-T2, with nothing
   committed. There's no tool-level workaround for this one — the only defense is committing small
   and often (STEP 2), so an interruption costs minutes of work, not a whole package.

STOP AT THE END OF T2. Commit, report, and hand back — do not roll into T3.

HARD CONSTRAINTS:
- Never modify backend/app/agents/, any existing test, or mypy/ruff config.
- resilio/ is read-only.
- TDD: tests first, red -> green -> refactor, for anything you still write.
- Before any Alembic revision run `alembic heads` from the repo root (alembic.ini lives there, not
  under backend/) and chain from the real head. Confirmed 2026-08-19: head is 0013. T2 needs no
  migration. T3's will be 0014 unless the tree says otherwise by then.
- Atomic conventional commits, one per logical task.
- No new stack: LangGraph + FastAPI + SQLAlchemy 2 sync + APScheduler + Pydantic v2.
- Secrets only via env vars; Fernet-encrypt third-party tokens following
  backend/app/integrations/strava/oauth_service.py.
- Telegram specifics already respected in the code — verify, don't redo: parse_mode=HTML not
  MarkdownV2; 4096-char limit; webhook returns 200 immediately and processes in a BackgroundTask;
  validates X-Telegram-Bot-Api-Secret-Token; dedupes on update_id; mocks the Bot API with respx
  scoped to https://api.telegram.org — never patch httpx.Client globally (TestClient subclasses it).

REPORT at the end: files added, files modified, commits made (list them), the three gate results
before and after committing, confirmation T2 is complete, and confirmation session-log.md is fixed
and committed. If something is blocked, finish everything else first, then say plainly what's
blocked and why.
```
