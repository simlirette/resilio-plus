# The `/goal` prompt for Codex — Resilio V4

> Paste the block below into Codex after typing `/goal`.
> Full detail lives in `docs/prompts/CODEX-V4-TEXT-COACH.md`; this is just the driver.

---

```
Build Resilio V4 — the text-native coach.

SPEC: read docs/prompts/CODEX-V4-TEXT-COACH.md (execution brief, 9 work packages)
and docs/GOAL-V4-TEXT-COACH.md (the why + locked decisions). Read both before
touching anything. Where the brief disagrees with the code, the code wins —
correct the brief and say so.

OUTCOME: an athlete with only a phone can be onboarded by the coach over
Telegram, receives next week's training plan as an unprompted weekly message
with the reasoning behind it, can reply "too much volume Wednesday" in plain
language to get a revised week, and on tapping Approve sees every session
appear in a dedicated "Resilio Training" Google Calendar. Re-running a week
updates those events instead of duplicating them.

START AT T1. T0 is DONE — Phase D is already merged to main (3ad665d), the
worktree is removed, mobile WIP is saved (9b04fc7). Do not re-merge anything.

ORDER, one at a time, no skipping ahead:
  T1 messaging core (channel-agnostic)   T5 Google Calendar
  T2 Telegram channel                    T6 weekly automation cron
  T3 approvals over text                 T7 freeze web/mobile/desktop
  T4 onboarding over text                T8 deploy + smoke test

COMMAND DISCIPLINE — this is what wedged the previous session. Never run a
long or high-output command in the foreground. Always redirect and tail:
  pytest ... -q --tb=line -p no:cacheprovider > /tmp/pt.txt 2>&1; tail -30 /tmp/pt.txt
Run the SCOPED suite while iterating; the FULL suite only at the end of each
package. Never cat a whole result file. If any run passes ~10 minutes, kill it
and re-run scoped.

GATE after each package — exactly this, no better and no worse:
  pytest : 3 failed, >=2616 passed   <- the 3 are PRE-EXISTING, listed in the
                                        brief. Do NOT fix or chase them.
                                        A 4th failure means you broke something.
  mypy   : 0 errors (159 files)
  ruff   : 0 violations
Use the Poetry venv interpreter, not system Python:
  C:/Users/simon/AppData/Local/pypoetry/Cache/virtualenvs/resilio-8kDCl3fk-py3.13/Scripts/

HARD CONSTRAINTS:
- Never modify backend/app/agents/, any existing test, or mypy/ruff config.
- resilio/ is read-only.
- TDD: tests first, red -> green -> refactor.
- Before any Alembic revision run `alembic heads` and chain from the real head.
  Numbers in the brief are indicative and may be stale.
- Atomic conventional commits, one per logical task.
- No new stack: LangGraph + FastAPI + SQLAlchemy 2 sync + APScheduler + Pydantic v2.
- Secrets only via env vars; third-party refresh tokens Fernet-encrypted following
  backend/app/integrations/strava/oauth_service.py.

REPORT after each package: files added, files modified, test count delta, and
the three gate results. If something is blocked, finish everything else in the
package first, then say plainly what is blocked and why. Do not silently narrow
scope, and do not report done until the gate is green.
```
